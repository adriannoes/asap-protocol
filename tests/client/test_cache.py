"""Tests for asap.client.cache."""

from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import httpx
import pytest

from asap.client.cache import (
    DEFAULT_REGISTRY_CACHE_TTL,
    get_registry,
    invalidate,
)

VALID_REGISTRY_JSON = b"""{"version": "1.0", "updated_at": "2026-02-07T00:00:00Z", "agents": [
  {"id": "urn:asap:agent:alpha", "name": "Alpha", "description": "Test", "endpoints": {"http": "https://alpha.example.com/asap"}, "skills": [], "asap_version": "1.1.0"}
]}"""


def _mock_registry_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON)


@pytest.fixture(autouse=True)
def clear_registry_cache_before_each() -> None:
    invalidate()


@pytest.mark.asyncio
async def test_get_registry_returns_parsed_lite_registry() -> None:
    reg = await get_registry(
        "https://test.example/registry.json",
        transport=httpx.MockTransport(_mock_registry_handler),
    )
    assert reg.version == "1.0"
    assert len(reg.agents) == 1
    assert reg.agents[0].id == "urn:asap:agent:alpha"


@pytest.mark.asyncio
async def test_cache_hit_within_ttl_second_call_does_not_fetch() -> None:
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON)

    url = "https://cache-hit.example/registry.json"
    transport = httpx.MockTransport(counting_handler)
    reg1 = await get_registry(url, transport=transport)
    reg2 = await get_registry(url, transport=transport)

    assert call_count == 1
    assert reg1.version == reg2.version
    assert len(reg1.agents) == len(reg2.agents)


@pytest.mark.asyncio
async def test_cache_miss_after_ttl_refetches() -> None:
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON)

    url = "https://cache-ttl.example/registry.json"
    transport = httpx.MockTransport(counting_handler)
    with patch.dict(os.environ, {"ASAP_REGISTRY_CACHE_TTL": "1"}, clear=False):
        await get_registry(url, transport=transport)
        assert call_count == 1
        await asyncio.sleep(2)
        await get_registry(url, transport=transport)
    assert call_count == 2


@pytest.mark.asyncio
async def test_invalidate_clears_cache_next_get_fetches() -> None:
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON)

    url = "https://invalidate.example/registry.json"
    transport = httpx.MockTransport(counting_handler)
    await get_registry(url, transport=transport)
    assert call_count == 1
    invalidate()
    await get_registry(url, transport=transport)
    assert call_count == 2


@pytest.mark.asyncio
async def test_ttl_from_env_used() -> None:
    call_count = 0

    def counting_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, content=VALID_REGISTRY_JSON)

    url = "https://ttl-env.example/registry.json"
    transport = httpx.MockTransport(counting_handler)
    with patch.dict(os.environ, {"ASAP_REGISTRY_CACHE_TTL": "1"}, clear=False):
        await get_registry(url, transport=transport)
        await asyncio.sleep(1.5)
        await get_registry(url, transport=transport)
    assert call_count == 2


def test_default_ttl_constant() -> None:
    assert DEFAULT_REGISTRY_CACHE_TTL == 300
