"""Unit tests for OAuth2 token introspection (RFC 7662)."""

import time

import httpx
import pytest

from asap.auth.introspection import (
    INACTIVE_TOKEN_CACHE_TTL_SECONDS,
    MAX_ACTIVE_CACHE_TTL_SECONDS,
    TokenInfo,
    TokenIntrospector,
)


def _make_introspection_transport(
    response_json: dict,
    status_code: int = 200,
    expected_path: str = "/oauth/introspect",
) -> httpx.MockTransport:
    """Build MockTransport that validates introspection request and returns given JSON."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert expected_path in str(request.url) or request.url.path.endswith("introspect")
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("Basic ")
        assert request.headers.get("Accept") == "application/json"
        body = request.content.decode()
        assert "token=" in body
        return httpx.Response(status_code=status_code, json=response_json)

    return httpx.MockTransport(handler)


async def test_introspect_returns_token_info_for_active_token() -> None:
    """Verify introspect returns TokenInfo when token is active."""
    now = int(time.time())
    resp = {
        "active": True,
        "sub": "urn:asap:agent:test",
        "scope": "asap:read asap:execute",
        "exp": now + 3600,
        "client_id": "my-client",
        "token_type": "Bearer",
    }

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="client",
        client_secret="secret",
        transport=_make_introspection_transport(resp),
    )

    result = await introspector.introspect("opaque-token-xyz")

    assert result is not None
    assert isinstance(result, TokenInfo)
    assert result.active is True
    assert result.sub == "urn:asap:agent:test"
    assert "asap:read" in result.scope
    assert "asap:execute" in result.scope
    assert result.exp == now + 3600
    assert result.client_id == "my-client"
    assert result.token_type == "Bearer"


async def test_introspect_returns_none_for_inactive_token() -> None:
    """Verify introspect returns None when token is inactive (RFC 7662)."""
    resp = {"active": False}

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="client",
        client_secret="secret",
        transport=_make_introspection_transport(resp),
    )

    result = await introspector.introspect("revoked-token")

    assert result is None


async def test_introspect_caches_active_token_result() -> None:
    """Verify second introspect call uses cache and does not hit transport."""
    call_count = 0
    now = int(time.time())

    def counting_transport(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(
            status_code=200,
            json={
                "active": True,
                "sub": "cached-sub",
                "scope": "asap:read",
                "exp": now + 3600,
            },
        )

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="c",
        client_secret="s",
        transport=httpx.MockTransport(counting_transport),
    )

    first = await introspector.introspect("same-token")
    second = await introspector.introspect("same-token")

    assert first is not None
    assert second is not None
    assert first.sub == second.sub == "cached-sub"
    assert call_count == 1


async def test_introspect_caches_inactive_token_result() -> None:
    """Verify inactive result is cached to reduce introspection endpoint load."""
    call_count = 0

    def counting_transport(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(status_code=200, json={"active": False})

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="c",
        client_secret="s",
        transport=httpx.MockTransport(counting_transport),
    )

    first = await introspector.introspect("invalid-token")
    second = await introspector.introspect("invalid-token")

    assert first is None
    assert second is None
    assert call_count == 1


async def test_introspect_parses_scope_as_list() -> None:
    """Verify scope can be a JSON array (some providers return list)."""
    now = int(time.time())
    resp = {
        "active": True,
        "sub": "sub",
        "scope": ["asap:read", "asap:execute"],
        "exp": now + 3600,
    }

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/introspect",
        client_id="c",
        client_secret="s",
        transport=_make_introspection_transport(resp, expected_path="introspect"),
    )

    result = await introspector.introspect("t")

    assert result is not None
    assert result.scope == ["asap:read", "asap:execute"]


async def test_introspect_raises_on_http_error() -> None:
    """Verify introspect raises when introspection endpoint returns 401."""

    def fail_transport(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=401, json={"error": "unauthorized"})

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="bad",
        client_secret="bad",
        transport=httpx.MockTransport(fail_transport),
    )

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await introspector.introspect("token")

    assert exc_info.value.response.status_code == 401


async def test_introspect_raises_on_network_error() -> None:
    """Verify introspect raises on network/connection errors."""

    def fail_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    introspector = TokenIntrospector(
        introspection_url="https://auth.example.com/oauth/introspect",
        client_id="c",
        client_secret="s",
        transport=httpx.MockTransport(fail_transport),
    )

    with pytest.raises(httpx.ConnectError) as exc_info:
        await introspector.introspect("token")

    assert "Connection refused" in str(exc_info.value)


def test_token_info_cache_ttl_for_active_token() -> None:
    """Verify cache_ttl_seconds uses exp for active tokens (capped at max)."""
    now = int(time.time())
    info = TokenInfo(
        active=True,
        sub="sub",
        scope=[],
        exp=now + 1800,  # 30 min - within cap
    )
    ttl = info.cache_ttl_seconds()
    # exp - now - 30 buffer ≈ 1770, capped at 3600
    assert 1700 < ttl <= 1800
    assert ttl <= MAX_ACTIVE_CACHE_TTL_SECONDS


def test_token_info_cache_ttl_for_inactive_token() -> None:
    """Verify cache_ttl_seconds returns INACTIVE_TOKEN_CACHE_TTL for inactive."""
    info = TokenInfo(active=False, sub=None, scope=[], exp=None)
    assert info.cache_ttl_seconds() == INACTIVE_TOKEN_CACHE_TTL_SECONDS


def test_token_info_cache_ttl_caps_at_max() -> None:
    """Verify cache TTL is capped at MAX_ACTIVE_CACHE_TTL_SECONDS."""
    now = int(time.time())
    info = TokenInfo(
        active=True,
        sub="sub",
        scope=[],
        exp=now + 86400 * 7,  # 7 days
    )
    assert info.cache_ttl_seconds() == MAX_ACTIVE_CACHE_TTL_SECONDS
