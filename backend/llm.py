import asyncio
import json
import os
import re
from typing import Any

import httpx


class LLMError(Exception):
    pass


_RETRYABLE = (
    httpx.RemoteProtocolError,
    httpx.ReadError,
    httpx.TimeoutException,
    httpx.ConnectError,
)


def _settings() -> tuple[str, str, str]:
    base = os.getenv("AI_API_BASE", "https://api.deepseek.com").rstrip("/")
    key = os.getenv("AI_API_KEY", "").strip()
    model = os.getenv("AI_MODEL", "deepseek-chat").strip()
    if not key or key == "your-secret-key-here":
        raise LLMError("未配置 AI_API_KEY。请复制 backend/.env.example 为 backend/.env 并填入密钥后重启。")
    return base, key, model


def _supports_json_mode(base: str) -> bool:
    return "tju.edu.cn" not in base


def _message_text(message: dict[str, Any]) -> str:
    content = (message.get("content") or "").strip()
    if content:
        return content
    reasoning = (message.get("reasoning_content") or "").strip()
    if reasoning:
        start = reasoning.find("{")
        end = reasoning.rfind("}")
        if start >= 0 and end > start:
            return reasoning[start : end + 1]
    return ""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise LLMError("模型返回为空，请稍后重试。")

    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise LLMError("模型返回的 JSON 不完整，请缩短输入文本后重试。") from exc
        raise LLMError("模型返回不是合法 JSON。片段：" + text[:200])


async def _stream_completion(
    base: str,
    key: str,
    model: str,
    payload: dict[str, Any],
) -> str:
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = dict(payload)
    payload["stream"] = True
    timeout = httpx.Timeout(300.0, connect=30.0)
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
                raise LLMError(
                    f"AI 接口请求失败（HTTP {resp.status_code}）。详情：{body.decode()[:300]}"
                )
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
                parts.append(delta.get("content") or "")
    return "".join(parts)


async def _request_completion(
    system: str,
    user: str,
    temperature: float,
    max_tokens: int,
) -> str:
    base, key, model = _settings()
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if _supports_json_mode(base):
        payload["response_format"] = {"type": "json_object"}

    use_stream = max_tokens >= 2048 or len(user) > 1500
    if use_stream:
        text = await _stream_completion(base, key, model, payload)
        if not text.strip():
            raise LLMError("模型返回内容为空，请稍后重试。")
        return text

    timeout = httpx.Timeout(300.0, connect=30.0)
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
        raise LLMError(f"AI 接口请求失败（HTTP {resp.status_code}）。详情：{resp.text[:300]}")

    data = resp.json()
    choice = data.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = _message_text(message)
    finish = choice.get("finish_reason", "")

    if not content:
        raise LLMError("模型返回内容为空，请稍后重试。")

    if finish == "length":
        raise LLMError("模型输出被截断，请缩短输入文本后重试。")

    return content


async def chat_json(
    system: str,
    user: str,
    temperature: float = 0.75,
    max_tokens: int = 8192,
    max_attempts: int = 4,
) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(max_attempts):
        try:
            temp = temperature if attempt == 0 else max(0.3, temperature - 0.15 * attempt)
            content = await _request_completion(system, user, temp, max_tokens)
            return _extract_json(content)
        except LLMError as exc:
            last_err = exc
        except _RETRYABLE as exc:
            last_err = LLMError(f"AI 连接中断（{type(exc).__name__}），正在重试…")
        if attempt < max_attempts - 1:
            await asyncio.sleep(1.5 * (attempt + 1))
    if last_err is None:
        raise LLMError("生成失败，请稍后重试。")
    raise last_err
