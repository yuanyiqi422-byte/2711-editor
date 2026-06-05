"""SSE format smoke tests — validates streaming headers without calling LLM."""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_stream_rejects_empty_text(client: AsyncClient) -> None:
    response = await client.post(
        "/api/create/stream",
        json={"text": "", "style": "campus"},
    )
    # Pydantic validation or early error — must not 500
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sse_helper_format() -> None:
    """Unit-level: _sse produces valid event-stream line format."""
    from main import _sse

    payload = {"progress": 5, "msg": "测试"}
    chunk = _sse("status", payload)
    assert chunk.startswith("event: status\n")
    assert "data:" in chunk
    assert chunk.endswith("\n\n")
    parsed = json.loads(chunk.split("data: ", 1)[1].strip())
    assert parsed["progress"] == 5
    assert parsed["msg"] == "测试"
