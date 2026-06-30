"""Tests for shared transport authentication helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
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


def _request_on_app(
    app: MagicMock,
    *,
    authorization: str | None = "Bearer host.jwt",
) -> Request:
    headers: list[tuple[bytes, bytes]] = []
    if authorization is not None:
        headers.append((b"authorization", authorization.encode()))
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/asap/agent/register",
            "headers": headers,
            "app": app,
        }
    )


@pytest.fixture
def identity_app() -> MagicMock:
    app = MagicMock()
    app.state.identity_host_store = MagicMock()
    app.state.identity_jwt_audience = "urn:asap:agent:test-server"
    return app


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


@pytest.mark.asyncio
async def test_verify_host_bearer_missing_token_returns_401(identity_app: MagicMock) -> None:
    request = _request_on_app(identity_app, authorization=None)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 401
    assert err.body == b'{"detail":"Authentication required"}'


@pytest.mark.asyncio
@patch("asap.transport._auth_helpers.verify_host_jwt", new_callable=AsyncMock)
async def test_verify_host_bearer_revoked_host_error_returns_403(
    mock_verify: AsyncMock,
    identity_app: MagicMock,
) -> None:
    mock_verify.return_value = JwtVerifyResult(ok=False, error=HOST_REVOKED_ERROR)
    request = _request_on_app(identity_app)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 403
    assert err.body == b'{"detail":"host revoked"}'


@pytest.mark.asyncio
@patch("asap.transport._auth_helpers.verify_host_jwt", new_callable=AsyncMock)
async def test_verify_host_bearer_invalid_signature_returns_401(
    mock_verify: AsyncMock,
    identity_app: MagicMock,
) -> None:
    mock_verify.return_value = JwtVerifyResult(ok=False, error="invalid signature")
    request = _request_on_app(identity_app)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 401


@pytest.mark.asyncio
@patch("asap.transport._auth_helpers.verify_host_jwt", new_callable=AsyncMock)
async def test_verify_host_bearer_missing_iss_claim_returns_400(
    mock_verify: AsyncMock,
    identity_app: MagicMock,
) -> None:
    mock_verify.return_value = JwtVerifyResult(
        ok=True,
        claims={"sub": "host"},
        host=None,
    )
    request = _request_on_app(identity_app)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 400
    assert err.body == b'{"detail":"missing iss in host JWT"}'


@pytest.mark.asyncio
@patch("asap.transport._auth_helpers.verify_host_jwt", new_callable=AsyncMock)
async def test_verify_host_bearer_defensive_revoked_host_status_returns_403(
    mock_verify: AsyncMock,
    identity_app: MagicMock,
) -> None:
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    revoked_host = HostIdentity(
        host_id="host-1",
        public_key=ed25519_public_jwk(host_sk),
        status="revoked",
        created_at=now,
        updated_at=now,
    )
    mock_verify.return_value = JwtVerifyResult(
        ok=True,
        claims={"iss": "urn:asap:host:host-1"},
        host=revoked_host,
    )
    request = _request_on_app(identity_app)

    result, err = await verify_host_bearer(request, jti_replay_cache=None)

    assert result is None
    assert err is not None
    assert err.status_code == 403


@pytest.mark.asyncio
@patch("asap.transport._auth_helpers.verify_host_jwt", new_callable=AsyncMock)
async def test_verify_host_bearer_success_returns_verified_result(
    mock_verify: AsyncMock,
    identity_app: MagicMock,
) -> None:
    now = datetime.now(timezone.utc)
    host_sk = Ed25519PrivateKey.generate()
    active_host = HostIdentity(
        host_id="host-1",
        public_key=ed25519_public_jwk(host_sk),
        status="active",
        created_at=now,
        updated_at=now,
    )
    verified = JwtVerifyResult(
        ok=True,
        claims={"iss": "urn:asap:host:host-1"},
        host=active_host,
    )
    mock_verify.return_value = verified
    request = _request_on_app(identity_app)

    result, err = await verify_host_bearer(request, jti_replay_cache=MagicMock())

    assert err is None
    assert result is verified
    mock_verify.assert_awaited_once()
    call_kwargs: dict[str, Any] = mock_verify.await_args.kwargs
    assert call_kwargs["expected_audience"] == "urn:asap:agent:test-server"
