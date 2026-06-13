import asyncio
import json
import logging
import os
import re
from typing import Any

import httpx

from primary_api import (
    handle_primary_exhausted,
    has_fallback_config,
    is_primary_disabled,
    is_primary_exhaustion_error,
    log_primary_disabled_once,
)

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


_RETRYABLE = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.TimeoutException,
    httpx.ConnectError,
)

_JSON_TRUNCATION_MARKERS = (
    "JSON 不完整",
    "输出被截断",
    "输出不完整",
    "incomplete json",
    "truncated",
)

_JSON_ONLY_RETRY_SUFFIX = "\n\n只输出 JSON，不要解释。"

_PLANNING_PROSE_RE = re.compile(
    r"^(我们根据|先看\s*scene|需要注意|我将为|接下来|首先|根据用户|为\s*scene_|"
    r"让我先|我来为|下面为|下面我将|我将根据|好的[，,]|首先分析)",
    re.IGNORECASE,
)

_JSON_SAFE_FALLBACK_MODEL = "deepseek-chat"
_FALLBACK_DEFAULT_MODEL = "deepseek-v4-flash"


def _fallback_model() -> str:
    """Model for DeepSeek (or other fallback base). Never use primary AI_MODEL here."""
    return os.getenv("AI_MODEL_FALLBACK", "").strip() or _FALLBACK_DEFAULT_MODEL


def _env_float(name: str, default: str) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return float(default)


LLM_TIMEOUT_SEC = _env_float("LLM_TIMEOUT_SEC", "300")


def compute_timeout_sec(
    prompt_chars: int,
    *,
    base_sec: float | None = None,
    min_sec: float = 120.0,
    max_sec: float = 900.0,
) -> float:
    """Scale LLM read timeout with prompt size."""
    base = LLM_TIMEOUT_SEC if base_sec is None else base_sec
    if prompt_chars <= 2000:
        factor = 1.0
    elif prompt_chars <= 8000:
        factor = 1.0 + (prompt_chars - 2000) / 6000 * 0.35
    elif prompt_chars <= 15000:
        factor = 1.35 + (prompt_chars - 8000) / 7000 * 0.25
    else:
        factor = 1.6 + min(0.35, (prompt_chars - 15000) / 20000 * 0.35)
    return min(max_sec, max(min_sec, base * factor))


def _httpx_timeout(total_sec: float) -> httpx.Timeout:
    return httpx.Timeout(total_sec, connect=30.0)


def _timeout_error_message(step_label: str | None, total_sec: float) -> str:
    step = step_label or "AI 生成"
    sec = int(total_sec)
    return (
        f"{step}超时（已等待>{sec}秒）。请直接重试；长文本可能需要数分钟。"
    )


def _llm_error_non_retryable(exc: LLMError) -> bool:
    msg = str(exc)
    if "未配置 AI_API_KEY" in msg:
        return True
    if "HTTP 401" in msg or "HTTP 403" in msg:
        return True
    return False


def _is_truncation_llm_error(exc: BaseException) -> bool:
    if not isinstance(exc, LLMError):
        return False
    msg = str(exc).lower()
    return any(marker.lower() in msg for marker in _JSON_TRUNCATION_MARKERS)


def _http_error_message(status: int, body: str) -> str:
    if status == 401:
        return "AI 接口密钥无效（HTTP 401）。请检查 backend/.env 中的 AI_API_KEY。"
    if status == 402:
        return "AI 接口余额不足（HTTP 402）。"
    if status == 403:
        return "AI 接口拒绝访问（HTTP 403）。请检查密钥权限或账户余额。"
    if status == 429:
        return "AI 接口请求过于频繁（HTTP 429），请稍后重试。"
    return f"AI 接口请求失败（HTTP {status}）。详情：{body[:300]}"


def _delta_text(delta: dict[str, Any]) -> str:
    return (delta.get("content") or "") + (delta.get("reasoning_content") or "")


def _api_base_url() -> str:
    return (
        os.getenv("AI_API_BASE", "").strip()
        or os.getenv("AI_BASE_URL", "").strip()
        or "https://api.deepseek.com"
    ).rstrip("/")


def _provider_label(base: str) -> str:
    """Hostname-only label for logs (no secrets)."""
    m = re.match(r"https?://([^/]+)", base)
    return m.group(1) if m else base


def _settings(
    model_override: str | None = None,
    *,
    use_fallback: bool = False,
) -> tuple[str, str, str]:
    if use_fallback or is_primary_disabled():
        if is_primary_disabled() and not use_fallback:
            log_primary_disabled_once()
        base = (
            os.getenv("AI_API_BASE_FALLBACK", "").strip()
            or os.getenv("AI_BASE_URL_FALLBACK", "").strip()
        ).rstrip("/")
        key = os.getenv("AI_API_KEY_FALLBACK", "").strip()
        # model_override is for primary (e.g. gpt-5.4 on chatgpt.edu.rs) — never send it to fallback API.
        model = _fallback_model()
        if not base or not key or key == "your-secret-key-here":
            raise LLMError("未配置 AI 备用接口（AI_API_BASE_FALLBACK / AI_API_KEY_FALLBACK）。")
        return base, key, model

    base = _api_base_url()
    key = os.getenv("AI_API_KEY", "").strip()
    model = (model_override or os.getenv("AI_MODEL", "deepseek-chat")).strip()
    if not key or key == "your-secret-key-here":
        raise LLMError("未配置 AI_API_KEY。请复制 backend/.env.example 为 backend/.env 并填入密钥后重启。")
    return base, key, model


def _is_fallbackable_llm_error(exc: LLMError) -> bool:
    msg = str(exc).lower()
    if any(token in msg for token in ("http 401", "http 402", "http 429")):
        return True
    quota_markers = (
        "insufficient balance",
        "quota",
        "余额不足",
        "余额",
        "rate limit",
        "too many requests",
    )
    return any(marker in msg for marker in quota_markers)


def _is_reasoning_model(model: str) -> bool:
    m = model.lower()
    return any(tag in m for tag in ("v4", "reasoner", "r1"))


def active_model_is_reasoning() -> bool:
    _, _, model = _settings()
    return _is_reasoning_model(model)


def resolved_model_is_reasoning(fast: bool = False) -> bool:
    override = _resolve_model(fast=fast)
    _, _, model = _settings(override)
    return _is_reasoning_model(model)


def _json_safe_model(model: str) -> str:
    """Prefer chat model for structured JSON when a reasoning model is configured."""
    if not _is_reasoning_model(model):
        return model
    fast = os.getenv("AI_MODEL_FAST", "").strip()
    if fast and not _is_reasoning_model(fast):
        return fast
    if not _is_reasoning_model(_JSON_SAFE_FALLBACK_MODEL):
        return _JSON_SAFE_FALLBACK_MODEL
    return model


def _resolve_model(fast: bool = False) -> str | None:
    if fast:
        fast_model = os.getenv("AI_MODEL_FAST", "").strip()
        if fast_model:
            return _json_safe_model(fast_model)
        _, _, default_model = _settings()
        return _json_safe_model(default_model)
    return None


def _supports_json_mode(base: str) -> bool:
    return "tju.edu.cn" not in base


def _stream_enabled() -> bool:
    return os.getenv("LLM_STREAM", "1").strip().lower() not in ("0", "false", "no")


def _prefers_non_stream(model: str) -> bool:
    """Reasoning models (e.g. deepseek-v4-flash) often emit empty stream deltas."""
    return _is_reasoning_model(model)


def _should_stream(model: str, max_tokens: int, user_len: int) -> bool:
    if not _stream_enabled() or _prefers_non_stream(model):
        return False
    return max_tokens >= 2048 or user_len > 1500


def _llm_error_with_step(exc: LLMError, step_label: str | None) -> LLMError:
    msg = str(exc)
    if step_label and step_label not in msg:
        return LLMError(f"{step_label}阶段：{msg}")
    return exc


def _empty_response_error(model: str, step_label: str | None = None) -> LLMError:
    hint = ""
    if _prefers_non_stream(model):
        hint = " 推理模型常把输出写入 reasoning 而非 content，建议 AI_MODEL=deepseek-chat 或增大 max_tokens。"
    msg = f"模型返回内容为空，请稍后重试。{hint}".strip()
    return _llm_error_with_step(LLMError(msg), step_label)


def _json_object_slice(text: str) -> str | None:
    """Return the outermost `{...}` dict substring if it parses as JSON."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return candidate
    except json.JSONDecodeError:
        pass
    return None


def _is_planning_prose(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if _PLANNING_PROSE_RE.search(s):
        return True
    if "{" not in s and len(s) > 30:
        markers = ("scene_", "补充对白", "节点", "骨架", "lines", "对白")
        if any(m in s for m in markers):
            return True
    return False


def _non_json_error_message(text: str) -> str:
    snippet = text.strip().replace("\n", " ")[:80]
    if len(text.strip()) > 80:
        snippet += "…"
    return f"模型返回了解释性文字而非 JSON（{snippet}）。请直接重试创建。"


def _is_prose_response_error(exc: LLMError) -> bool:
    msg = str(exc)
    return "解释性文字而非 JSON" in msg or "不是合法 JSON" in msg


def _message_text(message: dict[str, Any]) -> str:
    content = (message.get("content") or "").strip()
    reasoning = (message.get("reasoning_content") or "").strip()

    for part in (content, reasoning):
        sl = _json_object_slice(part)
        if sl:
            return sl

    if content:
        return content
    return reasoning


def _salvage_object_dict(fragment: str) -> dict[str, Any]:
    """Extract complete key-value pairs from a truncated `{ "k": v, ...` object."""
    s = fragment.strip()
    if not s.startswith("{"):
        return {}
    decoder = json.JSONDecoder()
    result: dict[str, Any] = {}
    i = 1
    n = len(s)
    while i < n:
        while i < n and s[i] in " \t\n\r,":
            i += 1
        if i >= n or s[i] == "}":
            break
        try:
            key, end = decoder.raw_decode(s, i)
            if not isinstance(key, str):
                i += 1
                continue
            while end < n and s[end] in " \t\n\r":
                end += 1
            if end >= n or s[end] != ":":
                break
            val_start = end + 1
            while val_start < n and s[val_start] in " \t\n\r":
                val_start += 1
            val, val_end = decoder.raw_decode(s, val_start)
            result[key] = val
            i = val_end
        except json.JSONDecodeError:
            break
    return result


def _salvage_truncated_json(text: str) -> dict[str, Any] | None:
    """Recover complete objects from truncated JSON (common with reasoning models)."""
    text = text.strip()
    if not text:
        return None

    start = text.find("{")
    if start < 0:
        return None
    fragment = text[start:]

    for suffix in ("", "}", "}}", "}]}", '"}', '"}]}', '"]}', '"]}}'):
        try:
            parsed = json.loads(fragment + suffix)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    nodes_match = re.search(r'"nodes"\s*:\s*\{', fragment)
    if nodes_match:
        nodes_start = nodes_match.end() - 1
        nodes_dict = _salvage_object_dict(fragment[nodes_start:])
        if nodes_dict:
            top: dict[str, Any] = {"nodes": nodes_dict}
            for key in ("title", "synopsis", "start_node_id"):
                key_match = re.search(
                    rf'"{key}"\s*:\s*("(?:\\.|[^"\\])*"|\d+|true|false|null)',
                    fragment,
                )
                if key_match:
                    try:
                        top[key] = json.loads(key_match.group(1))
                    except json.JSONDecodeError:
                        pass
            return top

    top_dict = _salvage_object_dict(fragment)
    if top_dict:
        return top_dict
    return None


def _truncation_error_message() -> str:
    return "模型输出不完整，服务端将自动重试或拆分批次，请直接重试创建。"


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise LLMError("模型返回为空，请稍后重试。")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            salvaged = _salvage_truncated_json(text[start:])
            if salvaged:
                logger.info(
                    "salvaged partial JSON keys=%s",
                    list(salvaged.keys()),
                )
                return salvaged
            raise LLMError(_truncation_error_message())

    salvaged = _salvage_truncated_json(text)
    if salvaged:
        logger.info("salvaged partial JSON keys=%s", list(salvaged.keys()))
        return salvaged

    if "{" in text:
        raise LLMError(_truncation_error_message())

    if _is_planning_prose(text):
        raise LLMError(_non_json_error_message(text))

    raise LLMError(_non_json_error_message(text))


async def _stream_completion(
    base: str,
    key: str,
    model: str,
    payload: dict[str, Any],
    *,
    timeout_sec: float,
) -> str:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = dict(payload)
    payload["stream"] = True
    timeout = _httpx_timeout(timeout_sec)
    parts: list[str] = []
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{base}/chat/completions",
            headers=headers,
            json=payload,
        ) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                raise LLMError(_http_error_message(resp.status_code, body.decode()))
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                except json.JSONDecodeError:
                    continue
                delta = data.get("choices", [{}])[0].get("delta", {})
                parts.append(_delta_text(delta))
    return "".join(parts)


async def _blocking_completion(
    base: str,
    key: str,
    payload: dict[str, Any],
    *,
    timeout_sec: float,
) -> str:
    timeout = _httpx_timeout(timeout_sec)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{base}/chat/completions",
            headers=headers,
            json=payload,
        )

    if resp.status_code >= 400:
        raise LLMError(_http_error_message(resp.status_code, resp.text))

    data = resp.json()
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = _message_text(message)
    finish = choice.get("finish_reason", "")

    if not content:
        if finish == "length":
            raise LLMError(_truncation_error_message())
        return ""

    if finish == "length":
        logger.warning(
            "LLM finish_reason=length model=%s chars=%s — attempting partial JSON salvage",
            payload.get("model"),
            len(content),
        )

    return content


def _build_payload(
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    base: str,
    *,
    json_mode: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode and _supports_json_mode(base):
        payload["response_format"] = {"type": "json_object"}
    return payload


async def _request_completion_with_provider(
    base: str,
    key: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    *,
    timeout_sec: float,
    step_label: str | None,
    json_modes: tuple[bool, ...],
) -> str:
    use_stream = _should_stream(model, max_tokens, len(user))

    async def _try_payload(payload: dict[str, Any], *, stream: bool) -> str:
        if stream:
            text = await _stream_completion(base, key, model, payload, timeout_sec=timeout_sec)
            if text.strip():
                return text
        return await _blocking_completion(base, key, payload, timeout_sec=timeout_sec)

    for json_mode in json_modes:
        payload = _build_payload(
            model, system, user, temperature, max_tokens, base, json_mode=json_mode
        )
        text = await _try_payload(payload, stream=use_stream)
        if text.strip():
            return text
        if use_stream:
            text = await _try_payload(payload, stream=False)
            if text.strip():
                return text
        logger.warning(
            "LLM empty response provider=%s model=%s json_mode=%s stream=%s step=%s",
            _provider_label(base),
            model,
            json_mode,
            use_stream,
            step_label or "",
        )

    raise _empty_response_error(model, step_label)


async def _request_completion(
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
    *,
    model_override: str | None = None,
    timeout_sec: float | None = None,
    step_label: str | None = None,
    json_mode_preference: tuple[bool, ...] | None = None,
) -> str:
    base, key, model = _settings(model_override)
    total_sec = timeout_sec if timeout_sec is not None else compute_timeout_sec(len(user))
    json_modes = json_mode_preference if json_mode_preference is not None else (True, False)

    if is_primary_disabled():
        fb_base, fb_key, fb_model = _settings(model_override, use_fallback=True)
        text = await _request_completion_with_provider(
            fb_base,
            fb_key,
            fb_model,
            system,
            user,
            temperature,
            max_tokens,
            timeout_sec=total_sec,
            step_label=step_label,
            json_modes=json_modes,
        )
        logger.info(
            "LLM ok provider=%s model=%s step=%s (fallback-only)",
            _provider_label(fb_base),
            fb_model,
            step_label or "",
        )
        return text

    try:
        text = await _request_completion_with_provider(
            base,
            key,
            model,
            system,
            user,
            temperature,
            max_tokens,
            timeout_sec=total_sec,
            step_label=step_label,
            json_modes=json_modes,
        )
        logger.info(
            "LLM ok provider=%s model=%s step=%s",
            _provider_label(base),
            model,
            step_label or "",
        )
        return text
    except LLMError as exc:
        if not (_is_fallbackable_llm_error(exc) and has_fallback_config()):
            raise
        fb_base, fb_key, fb_model = _settings(model_override, use_fallback=True)
        logger.warning(
            "LLM primary failed provider=%s err=%s — retrying fallback provider=%s model=%s",
            _provider_label(base),
            str(exc)[:120],
            _provider_label(fb_base),
            fb_model,
        )
        text = await _request_completion_with_provider(
            fb_base,
            fb_key,
            fb_model,
            system,
            user,
            temperature,
            max_tokens,
            timeout_sec=total_sec,
            step_label=step_label,
            json_modes=json_modes,
        )
        if is_primary_exhaustion_error(str(exc)):
            handle_primary_exhausted(str(exc))
        logger.info(
            "LLM ok provider=%s model=%s step=%s (fallback)",
            _provider_label(fb_base),
            fb_model,
            step_label or "",
        )
        return text


async def chat_json(
    system: str,
    user: str,
    temperature: float = 0.75,
    max_tokens: int = 8192,
    max_attempts: int = 2,
    *,
    fast_model: bool = False,
    timeout_sec: float | None = None,
    step_label: str | None = None,
    strict_json_mode: bool = False,
) -> dict[str, Any]:
    model_override = _resolve_model(fast=fast_model)
    if model_override is None:
        _, _, base_model = _settings()
        if _is_reasoning_model(base_model):
            safe = _json_safe_model(base_model)
            if safe != base_model:
                model_override = safe
                logger.info(
                    "chat_json auto json-safe model=%s step=%s",
                    safe,
                    step_label or "",
                )
    total_sec = timeout_sec if timeout_sec is not None else compute_timeout_sec(len(user))
    last_err: Exception | None = None
    current_max_tokens = max_tokens
    use_chat_fallback = False
    json_modes: tuple[bool, ...] = (True,) if strict_json_mode else (True, False)
    user_prompt = user
    prose_retry_done = False
    last_content = ""

    for attempt in range(max_attempts):
        try:
            temp = temperature if attempt == 0 else max(0.3, temperature - 0.15 * attempt)
            effective_model = model_override
            if use_chat_fallback:
                _, _, base_model = _settings(model_override)
                effective_model = _json_safe_model(base_model)
                if effective_model != base_model:
                    logger.info(
                        "chat_json fallback to json-safe model=%s step=%s attempt=%s",
                        effective_model,
                        step_label or "",
                        attempt + 1,
                    )

            content = await _request_completion(
                system,
                user_prompt,
                temp,
                current_max_tokens,
                model_override=effective_model,
                timeout_sec=total_sec,
                step_label=step_label,
                json_mode_preference=json_modes,
            )
            last_content = content
            return _extract_json(content)
        except LLMError as exc:
            last_err = _llm_error_with_step(exc, step_label)
            if _llm_error_non_retryable(exc):
                raise last_err
            if not prose_retry_done and (
                _is_planning_prose(last_content) or _is_prose_response_error(exc)
            ):
                prose_retry_done = True
                user_prompt = user + _JSON_ONLY_RETRY_SUFFIX
                logger.warning(
                    "chat_json planning prose retry step=%s attempt=%s",
                    step_label or "",
                    attempt + 1,
                )
                await asyncio.sleep(0.5)
                continue
            if _is_truncation_llm_error(exc):
                current_max_tokens = min(16384, int(current_max_tokens * 1.4) + 512)
                if attempt >= max(1, max_attempts // 2):
                    json_modes = (False,)
                    use_chat_fallback = True
                logger.warning(
                    "chat_json truncation retry attempt=%s max_tokens=%s step=%s",
                    attempt + 1,
                    current_max_tokens,
                    step_label or "",
                )
        except _RETRYABLE as exc:
            if isinstance(exc, httpx.TimeoutException):
                last_err = _llm_error_with_step(
                    LLMError(_timeout_error_message(step_label, total_sec)),
                    step_label,
                )
            else:
                last_err = LLMError(f"AI 连接中断，正在重试…（{attempt + 1}/{max_attempts}）")
        if attempt < max_attempts - 1:
            await asyncio.sleep(1.5 * (attempt + 1))
    if last_err is None:
        raise _llm_error_with_step(LLMError("生成失败，请稍后重试。"), step_label)
    raise last_err
