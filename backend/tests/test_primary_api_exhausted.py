"""Primary API exhaustion: detect 402, fallback, persist disable flag."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import httpx
import pytest

import primary_api
from llm import LLMError, _request_completion


@pytest.fixture(autouse=True)
def _reset_primary_state(monkeypatch, tmp_path):
    monkeypatch.delenv("AI_PRIMARY_DISABLED", raising=False)
    monkeypatch.setattr(primary_api, "DISABLED_FLAG", tmp_path / ".api-primary-disabled")
    monkeypatch.setattr(primary_api, "ENV_PATH", tmp_path / ".env")
    primary_api._PROVIDER_SWITCH_NOTICE = None
    primary_api._LOGGED_PRIMARY_DISABLED = False
    yield


@pytest.mark.asyncio
async def test_primary_402_falls_back_and_disables(monkeypatch) -> None:
    primary_402 = httpx.Response(
        402,
        text='{"error":{"message":"Insufficient Balance"}}',
        request=httpx.Request("POST", "https://chatgpt.edu.rs/chat/completions"),
    )

    async def fake_blocking(base, key, payload, *, timeout_sec):
        if "deepseek" in base:
            assert payload.get("model") == "deepseek-chat"
            return '{"ok": true}'
        raise LLMError("AI 接口余额不足（HTTP 402）。")

    monkeypatch.setenv("AI_API_BASE", "https://chatgpt.edu.rs")
    monkeypatch.setenv("AI_API_KEY", "primary-key")
    monkeypatch.setenv("AI_MODEL", "gpt-5.4")
    monkeypatch.setenv("AI_API_BASE_FALLBACK", "https://api.deepseek.com")
    monkeypatch.setenv("AI_API_KEY_FALLBACK", "fallback-key")
    monkeypatch.setenv("AI_MODEL_FALLBACK", "deepseek-chat")

    with (
        patch("llm._stream_completion", new_callable=AsyncMock, return_value=""),
        patch("llm._blocking_completion", side_effect=fake_blocking),
    ):
        text = await _request_completion(
            "system",
            "user",
            0.5,
            512,
            model_override="gpt-5.4",
            timeout_sec=30.0,
        )

    assert text == '{"ok": true}'
    assert primary_api.is_primary_disabled() is True
    assert primary_api.DISABLED_FLAG.is_file()
    assert primary_api.consume_provider_switch_notice() == primary_api.provider_switch_message()
    env_text = primary_api.ENV_PATH.read_text(encoding="utf-8")
    assert "AI_PRIMARY_DISABLED=1" in env_text


@pytest.mark.asyncio
async def test_primary_disabled_skips_primary(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_blocking(base, key, payload, *, timeout_sec):
        calls.append(base)
        assert payload.get("model") != "gpt-5.4"
        return '{"via": "fallback"}'

    monkeypatch.setenv("AI_PRIMARY_DISABLED", "1")
    monkeypatch.setenv("AI_API_BASE", "https://chatgpt.edu.rs")
    monkeypatch.setenv("AI_API_KEY", "primary-key")
    monkeypatch.setenv("AI_API_BASE_FALLBACK", "https://api.deepseek.com")
    monkeypatch.setenv("AI_API_KEY_FALLBACK", "fallback-key")

    with (
        patch("llm._stream_completion", new_callable=AsyncMock, return_value=""),
        patch("llm._blocking_completion", side_effect=fake_blocking),
    ):
        text = await _request_completion("system", "user", 0.5, 512, timeout_sec=30.0)

    assert text == '{"via": "fallback"}'
    assert calls == ["https://api.deepseek.com"]


def test_primary_api_status_values(monkeypatch) -> None:
    monkeypatch.setenv("AI_API_KEY", "k")
    monkeypatch.setenv("AI_API_BASE_FALLBACK", "https://api.deepseek.com")
    monkeypatch.setenv("AI_API_KEY_FALLBACK", "fb")
    assert primary_api.primary_api_status() == "active"

    monkeypatch.delenv("AI_API_KEY", raising=False)
    assert primary_api.primary_api_status() == "fallback_only"

    monkeypatch.setenv("AI_PRIMARY_DISABLED", "1")
    assert primary_api.primary_api_status() == "disabled"


def test_is_primary_exhaustion_error() -> None:
    assert primary_api.is_primary_exhaustion_error("AI 接口余额不足（HTTP 402）。") is True
    assert primary_api.is_primary_exhaustion_error("AI 接口密钥无效（HTTP 401）。") is True
    assert primary_api.is_primary_exhaustion_error("AI 接口请求过于频繁（HTTP 429）") is False


def test_settings_fallback_never_uses_primary_model(monkeypatch) -> None:
    from llm import _settings

    monkeypatch.setenv("AI_API_BASE", "https://chatgpt.edu.rs")
    monkeypatch.setenv("AI_API_KEY", "primary-key")
    monkeypatch.setenv("AI_MODEL", "gpt-5.4")
    monkeypatch.setenv("AI_API_BASE_FALLBACK", "https://api.deepseek.com")
    monkeypatch.setenv("AI_API_KEY_FALLBACK", "fallback-key")
    monkeypatch.setenv("AI_MODEL_FALLBACK", "deepseek-v4-flash")

    _, _, model = _settings("gpt-5.4", use_fallback=True)
    assert model == "deepseek-v4-flash"

    monkeypatch.setenv("AI_PRIMARY_DISABLED", "1")
    _, _, disabled_model = _settings("gpt-5.4")
    assert disabled_model == "deepseek-v4-flash"
