"""Scene batch resilience when LLM returns truncated / incomplete JSON (no live API)."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from llm import LLMError
from narrative_service import (
    _batch_max_tokens,
    _is_truncated_json_llm_error,
    _run_scene_batch_resilient,
)


def _node_payload(nid: str) -> dict:
    return {
        "id": nid,
        "title": nid,
        "lines": [{"speaker": "旁白", "text": f"{nid} 对白"}],
        "choices": [],
        "after_lines_next": "",
    }


def test_is_truncated_json_llm_error_detects_known_messages() -> None:
    assert _is_truncated_json_llm_error(
        LLMError("模型输出不完整，服务端将自动重试或拆分批次，请直接重试创建。")
    )
    assert _is_truncated_json_llm_error(
        LLMError("模型返回的 JSON 不完整，请缩短输入文本后重试。")
    )
    assert _is_truncated_json_llm_error(
        LLMError("模型输出被截断，请缩短输入文本后重试。")
    )
    assert not _is_truncated_json_llm_error(LLMError("未配置 AI_API_KEY"))
    assert not _is_truncated_json_llm_error(ValueError("JSON 不完整"))


def test_batch_max_tokens_boosts_on_retry_attempt() -> None:
    base = _batch_max_tokens(3, attempt=0)
    boosted = _batch_max_tokens(3, attempt=1)
    assert boosted > base


@pytest.mark.asyncio
async def test_resilient_splits_batch_after_truncated_json() -> None:
    calls: list[tuple[list[str], int]] = []

    async def run_batch(batch_ids: list[str], attempt: int = 0) -> dict:
        calls.append((list(batch_ids), attempt))
        if len(batch_ids) > 1:
            raise LLMError("模型输出不完整，服务端将自动重试或拆分批次，请直接重试创建。")
        nid = batch_ids[0]
        return {"nodes": {nid: _node_payload(nid)}}

    on_tick = AsyncMock()
    result = await _run_scene_batch_resilient(
        ["s1", "s2"],
        chars=2000,
        completed=6,
        total=8,
        run_batch=run_batch,
        on_tick=on_tick,
    )

    nodes = result.get("nodes") or {}
    assert set(nodes) == {"s1", "s2"}
    multi_calls = [c for c in calls if len(c[0]) > 1]
    single_calls = [c for c in calls if len(c[0]) == 1]
    assert len(multi_calls) == 2  # attempts 0–1 before split on final attempt
    assert len(single_calls) == 2


@pytest.mark.asyncio
async def test_resilient_retries_single_node_with_higher_attempt() -> None:
    calls: list[int] = []

    async def run_batch(batch_ids: list[str], attempt: int = 0) -> dict:
        calls.append(attempt)
        if attempt < 1:
            raise LLMError("模型输出被截断，请缩短输入文本后重试。")
        return {"nodes": {batch_ids[0]: _node_payload(batch_ids[0])}}

    on_tick = AsyncMock()
    result = await _run_scene_batch_resilient(
        ["ending_good"],
        chars=2000,
        completed=7,
        total=8,
        run_batch=run_batch,
        on_tick=on_tick,
        allow_split=False,
    )

    assert "ending_good" in (result.get("nodes") or {})
    assert calls == [0, 1]


@pytest.mark.asyncio
async def test_resilient_reraises_non_truncated_llm_error() -> None:
    async def run_batch(batch_ids: list[str], attempt: int = 0) -> dict:
        raise LLMError("未配置 AI_API_KEY")

    with pytest.raises(LLMError, match="AI_API_KEY"):
        await _run_scene_batch_resilient(
            ["s1"],
            chars=2000,
            completed=0,
            total=1,
            run_batch=run_batch,
            on_tick=AsyncMock(),
        )
