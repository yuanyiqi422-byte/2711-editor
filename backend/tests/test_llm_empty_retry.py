"""Empty stream / blocking LLM responses should retry cheaply before failing."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from llm import (
    LLMError,
    _blocking_completion,
    _message_text,
    _prefers_non_stream,
    _request_completion,
    _should_stream,
    _stream_completion,
    chat_json,
)


def test_message_text_returns_full_reasoning_without_json_braces() -> None:
    msg = {
        "content": "",
        "reasoning_content": 'We need to reply with exactly "ok".',
    }
    assert _message_text(msg) == 'We need to reply with exactly "ok".'


def test_message_text_prefers_json_slice_in_reasoning() -> None:
    msg = {
        "content": "",
        "reasoning_content": 'Thinking… {"ping": true} done.',
    }
    assert _message_text(msg) == '{"ping": true}'


def test_prefers_non_stream_for_v4_flash() -> None:
    assert _prefers_non_stream("deepseek-v4-flash") is True
    assert _prefers_non_stream("deepseek-chat") is False


def test_should_stream_disabled_for_reasoning_model() -> None:
    assert _should_stream("deepseek-v4-flash", 8192, 5000) is False
    assert _should_stream("deepseek-chat", 8192, 5000) is True


@pytest.mark.asyncio
async def test_stream_completion_collects_reasoning_content() -> None:
    lines = [
        'data: {"choices":[{"delta":{"reasoning_content":"{\\"ok\\":"}}]}',
        'data: {"choices":[{"delta":{"reasoning_content":"true}"}}]}',
        "data: [DONE]",
    ]

    class FakeStream:
        status_code = 200

        async def aread(self) -> bytes:
            return b""

        async def aiter_lines(self):
            for line in lines:
                yield line

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            class Ctx:
                async def __aenter__(self_inner):
                    return FakeStream()

                async def __aexit__(self_inner, *a):
                    return False

            return Ctx()

    with patch("llm.httpx.AsyncClient", return_value=FakeClient()):
        text = await _stream_completion(
            "https://api.example.com",
            "key",
            "model",
            {"messages": []},
            timeout_sec=30.0,
        )
    assert text == '{"ok":true}'


@pytest.mark.asyncio
async def test_request_completion_falls_back_when_stream_empty() -> None:
    with (
        patch("llm._stream_completion", new_callable=AsyncMock, return_value=""),
        patch(
            "llm._blocking_completion",
            new_callable=AsyncMock,
            return_value='{"nodes":{}}',
        ) as blocking,
    ):
        text = await _request_completion(
            "system",
            "x" * 2000,
            0.5,
            4096,
            model_override="deepseek-chat",
            timeout_sec=60.0,
        )
    assert text == '{"nodes":{}}'
    assert blocking.await_count >= 1


@pytest.mark.asyncio
async def test_request_completion_retries_without_json_mode() -> None:
    calls: list[bool] = []

    async def fake_blocking(base, key, payload, *, timeout_sec):
        calls.append("response_format" in payload)
        if len(calls) == 1:
            return ""
        return '{"ok": true}'

    with patch("llm._blocking_completion", side_effect=fake_blocking):
        text = await _request_completion(
            "system",
            "user",
            0.5,
            512,
            model_override="deepseek-v4-flash",
            timeout_sec=30.0,
        )
    assert text == '{"ok": true}'
    assert calls == [True, False]


@pytest.mark.asyncio
async def test_request_completion_includes_step_label_on_empty() -> None:
    with patch("llm._blocking_completion", new_callable=AsyncMock, return_value=""):
        with pytest.raises(LLMError, match="故事圣经阶段"):
            await _request_completion(
                "system",
                "user",
                0.5,
                512,
                model_override="deepseek-v4-flash",
                timeout_sec=30.0,
                step_label="故事圣经",
            )


@pytest.mark.asyncio
async def test_blocking_completion_maps_http_429() -> None:
    response = httpx.Response(
        429,
        text='{"error":"rate limit"}',
        request=httpx.Request("POST", "https://api.example.com/chat/completions"),
    )

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, *args, **kwargs):
            return response

    with patch("llm.httpx.AsyncClient", return_value=FakeClient()):
        with pytest.raises(LLMError, match="HTTP 429"):
            await _blocking_completion(
                "https://api.example.com",
                "key",
                {"messages": []},
                timeout_sec=30.0,
            )


@pytest.mark.asyncio
async def test_chat_json_retries_empty_then_succeeds() -> None:
    calls = {"n": 0}

    async def fake_request(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("模型返回内容为空，请稍后重试。")
        return '{"title":"ok"}'

    with patch("llm._request_completion", side_effect=fake_request):
        data = await chat_json("sys", "user", max_attempts=2, step_label="故事圣经")
    assert data["title"] == "ok"
    assert calls["n"] == 2
