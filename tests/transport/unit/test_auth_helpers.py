"""Tests for shared transport authentication helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import pytest
from fastapi import FastAPI
from starlette.requests import Request

from asap.auth.agent_jwt import HOST_REVOKED_ERROR, JwtVerifyResult
from asap.auth.identity import HostIdentity
from asap.transport._auth_helpers import bearer_token_from_request, verify_host_bearer
from tests.crypto.jwk_helpers import ed25519_public_jwk


def _request_with_authorization(value: str | None) -> Request:
    """Build a minimal HTTP request carrying an optional Authorization header."""
    headers: list[tuple[bytes, bytes]] = []
    if value is not None:
        headers.append((b"authorization", value.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
        }
    )


def test_bearer_token_from_request_extracts_token() -> None:
    request = _request_with_authorization("Bearer abc.def")

    assert bearer_token_from_request(request) == "abc.def"


def test_bearer_token_from_request_strips_token_whitespace() -> None:
    request = _request_with_authorization("Bearer   abc.def   ")

    assert bearer_token_from_request(request) == "abc.def"


def test_bearer_token_from_request_missing_or_empty_returns_none() -> None:
    assert bearer_token_from_request(_request_with_authorization(None)) is None
    assert bearer_token_from_request(_request_with_authorization("Bearer ")) is None
    assert bearer_token_from_request(_request_with_authorization("Bearer   ")) is None


def test_bearer_token_from_request_non_bearer_returns_none() -> None:
    request = _request_with_authorization("Basic abc.def")

    assert bearer_token_from_request(request) is None


def _http_request_with_bearer(token: str | None = None) -> Request:
    """Build a minimal HTTP request with optional Bearer auth and app state."""
    headers: list[tuple[bytes, bytes]] = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/asap/agent/register",
            "headers": headers,
        }
    )
    app = FastAPI()
    app.state.identity_host_store = MagicMock()
    app.state.identity_jwt_audience = "urn:asap:agent:test-server"
    request.scope["app"] = app
    return request


@pytest.mark.asyncio
async def test_verify_host_bearer_missing_token_returns_401() -> None:
    """Requests without Bearer credentials must receive 401."""
    request = _http_request_with_bearer(None)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 401
    assert err.body == b'{"detail":"Authentication required"}'


@pytest.mark.asyncio
async def test_verify_host_bearer_revoked_host_error_returns_403() -> None:
    """HOST_REVOKED_ERROR from verify_host_jwt must map to 403, not 401."""
    request = _http_request_with_bearer("host.jwt.token")
    revoked = JwtVerifyResult(ok=False, error=HOST_REVOKED_ERROR)

    with patch(
        "asap.transport._auth_helpers.verify_host_jwt",
        new_callable=AsyncMock,
        return_value=revoked,
    ):
        result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 403
    assert err.body == b'{"detail":"host revoked"}'


@pytest.mark.asyncio
async def test_verify_host_bearer_missing_iss_claim_returns_400() -> None:
    """A verified token without iss must be rejected with 400."""
    request = _http_request_with_bearer("host.jwt.token")
    verified = JwtVerifyResult(ok=True, claims={"sub": "host-1"})

    with patch(
        "asap.transport._auth_helpers.verify_host_jwt",
        new_callable=AsyncMock,
        return_value=verified,
    ):
        result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 400
    assert err.body == b'{"detail":"missing iss in host JWT"}'


@pytest.mark.asyncio
async def test_verify_host_bearer_revoked_host_object_returns_403() -> None:
    """Defensive re-check rejects revoked host even when verify_host_jwt returns ok=True."""
    request = _http_request_with_bearer("host.jwt.token")
    host = HostIdentity(
        host_id="urn:asap:host:abc",
        public_key=ed25519_public_jwk(Ed25519PrivateKey.generate()),
        status="revoked",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    verified = JwtVerifyResult(
        ok=True,
        claims={"iss": "urn:asap:host:abc"},
        host=host,
    )

    with patch(
        "asap.transport._auth_helpers.verify_host_jwt",
        new_callable=AsyncMock,
        return_value=verified,
    ):
        result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 403
    assert err.body == b'{"detail":"host revoked"}'
