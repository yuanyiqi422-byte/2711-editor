"""Health endpoint smoke tests — no LLM calls."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_payload_shape(client: AsyncClient) -> None:
    data = (await client.get("/api/health")).json()
    assert "ok" in data
    assert "version" in data
    assert "model" in data
    assert "has_key" in data
    assert "upload" in data
    assert "extract" in data
    assert isinstance(data["styles"], dict)


@pytest.mark.asyncio
async def test_frontend_index_served(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
