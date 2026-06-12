"""Partial JSON salvage and truncation retry (no live API)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from llm import (
    LLMError,
    _extract_json,
    _json_safe_model,
    _resolve_model,
    _salvage_truncated_json,
    chat_json,
)


def test_salvage_truncated_nodes_dict() -> None:
    truncated = (
        '{"nodes": {"s1": {"id": "s1", "title": "开场", "lines": []}, '
        '"s2": {"id": "s2", "title": "转折", "lines": []}, '
        '"s3": {"id": "s3", "title": "未完'
    )
    salvaged = _salvage_truncated_json(truncated)
    assert salvaged is not None
    nodes = salvaged.get("nodes") or {}
    assert "s1" in nodes
    assert "s2" in nodes
    assert "s3" not in nodes


def test_extract_json_salvages_truncated_batch() -> None:
    truncated = (
        '{"nodes": {"n1": {"id": "n1", "lines": [{"speaker": "旁白", "text": "你好"}]}, '
        '"n2": {"id": "n2", "lines": [{"speaker": "旁白", "text": "再见"}]}, '
        '"n3": {"id": "n3", "title": "截'
    )
    data = _extract_json(truncated)
    nodes = data.get("nodes") or {}
    assert "n1" in nodes
    assert "n2" in nodes
    assert "n3" not in nodes


def test_extract_json_raises_friendly_truncation_message() -> None:
    with pytest.raises(LLMError, match="自动重试或拆分"):
        _extract_json('{"nodes": {"bad": {incomplete')


def test_json_safe_model_prefers_chat_for_v4() -> None:
    assert _json_safe_model("deepseek-v4-flash") == "deepseek-chat"
    assert _json_safe_model("deepseek-chat") == "deepseek-chat"


def test_resolve_model_fast_uses_json_safe_when_no_fast_env() -> None:
    with patch.dict("os.environ", {"AI_MODEL": "deepseek-v4-flash", "AI_MODEL_FAST": ""}, clear=False):
        resolved = _resolve_model(fast=True)
        assert resolved == "deepseek-chat"


@pytest.mark.asyncio
async def test_chat_json_retries_truncation_with_higher_tokens() -> None:
    calls: list[int] = []

    async def fake_request(*args, **kwargs):
        max_tokens = kwargs.get("max_tokens") or args[3]
        calls.append(max_tokens)
        if len(calls) == 1:
            raise LLMError("模型输出不完整，服务端将自动重试或拆分批次，请直接重试创建。")
        return (
            '{"nodes": {"s1": {"id": "s1", "title": "ok", "lines": []}}}'
        )

    with patch("llm._request_completion", side_effect=fake_request):
        data = await chat_json("sys", "user", max_tokens=2048, max_attempts=3, step_label="故事圣经")
    assert "s1" in (data.get("nodes") or {})
    assert len(calls) == 2
    assert calls[1] > calls[0]


@pytest.mark.asyncio
async def test_chat_json_auto_json_safe_when_reasoner_and_not_fast() -> None:
    seen_models: list[str] = []

    async def fake_request(*args, **kwargs):
        seen_models.append(kwargs.get("model_override"))
        return '{"title": "ok", "plot_beats": ["a"]}'

    with patch.dict("os.environ", {"AI_MODEL": "deepseek-v4-flash", "AI_MODEL_FAST": ""}, clear=False):
        with patch("llm._request_completion", side_effect=fake_request) as mock_req:
            data = await chat_json("sys", "user", fast_model=False, max_attempts=1)
    assert data.get("title") == "ok"
    assert mock_req.await_count == 1
    assert seen_models == ["deepseek-chat"]


@pytest.mark.asyncio
async def test_chat_json_retries_planning_prose_then_succeeds() -> None:
    calls: list[str] = []

    async def fake_request(_system, user, *_args, **_kwargs):
        calls.append(user)
        if len(calls) == 1:
            return "我们根据用户提供的原文节选和场景上下文，为scene_8和scene_9补充对白lines…"
        return '{"nodes": {"s1": {"id": "s1", "title": "ok", "lines": []}}}'

    with patch("llm._request_completion", side_effect=fake_request):
        data = await chat_json("sys", "user", max_attempts=2, step_label="场景对白")
    assert "s1" in (data.get("nodes") or {})
    assert len(calls) == 2
    assert "只输出 JSON" in calls[1]
