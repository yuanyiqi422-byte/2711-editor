"""Pytest fixtures for 2711 Editor API tests."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure backend modules resolve and .env loads before app import
os.environ.setdefault("AI_API_KEY", "test-key-for-pytest-only")
os.environ.setdefault("AI_API_BASE", "https://api.example.com")
os.environ.setdefault("AI_MODEL", "test-model")

from main import app


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
