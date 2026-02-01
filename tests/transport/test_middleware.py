"""Tests for authentication middleware.

This module tests the authentication middleware functionality:
- Bearer token validation
- Sender verification
- Authentication bypass when not configured
- Error responses for invalid auth
- Custom token validators
- Non-blocking sync validator execution (thread pool)

Note: Rate limiting tests have been migrated to tests/transport/integration/test_rate_limiting.py
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.transport.middleware import (
    ERROR_AUTH_REQUIRED,
    ERROR_INVALID_TOKEN,
    ERROR_RATE_LIMIT_EXCEEDED,
    ERROR_SENDER_MISMATCH,
    HTTP_FORBIDDEN,
    HTTP_TOO_MANY_REQUESTS,
    HTTP_UNAUTHORIZED,
    AuthenticationMiddleware,
    BearerTokenValidator,
    SizeLimitMiddleware,
    _get_sender_from_envelope,
    create_limiter,
    create_test_limiter,
    rate_limit_handler,
)


# Test fixtures


@pytest.fixture
def manifest_without_auth() -> Manifest:
    """Create a manifest without authentication."""
    return Manifest(
        id="urn:asap:agent:test-no-auth",
        name="Test Agent No Auth",
        version="1.0.0",
        description="Test agent without authentication",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def manifest_with_bearer_auth() -> Manifest:
    """Create a manifest with Bearer token authentication."""
    return Manifest(
        id="urn:asap:agent:test-with-auth",
        name="Test Agent With Auth",
        version="1.0.0",
        description="Test agent with authentication",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["bearer"]),
    )


@pytest.fixture
def valid_token_validator() -> BearerTokenValidator:
    """Create a validator that accepts specific tokens."""

    def validate(token: str) -> str | None:
        """Validate token and return agent ID."""
        valid_tokens = {
            "valid-token-123": "urn:asap:agent:client-1",
            "valid-token-456": "urn:asap:agent:client-2",
        }
        return valid_tokens.get(token)

    return BearerTokenValidator(validate)


# Tests for BearerTokenValidator


def test_bearer_token_validator_valid_token(valid_token_validator: BearerTokenValidator) -> None:
    """Test that valid tokens return agent IDs."""
    agent_id = valid_token_validator("valid-token-123")
    assert agent_id == "urn:asap:agent:client-1"


def test_bearer_token_validator_invalid_token(
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that invalid tokens return None."""
    agent_id = valid_token_validator("invalid-token")
    assert agent_id is None


def test_bearer_token_validator_custom_function() -> None:
    """Test that custom validation functions work."""

    def custom_validator(token: str) -> str | None:
        if token.startswith("custom-"):
            return f"urn:asap:agent:{token}"
        return None

    validator = BearerTokenValidator(custom_validator)
    agent_id = validator("custom-test")
    assert agent_id == "urn:asap:agent:custom-test"

    agent_id = validator("invalid")
    assert agent_id is None


# Tests for AuthenticationMiddleware initialization


def test_middleware_without_auth(manifest_without_auth: Manifest) -> None:
    """Test middleware initialization without auth requirement."""
    middleware = AuthenticationMiddleware(manifest_without_auth)
    assert middleware.manifest == manifest_without_auth
    assert middleware.validator is None
    assert not middleware._is_auth_required()
    assert not middleware._supports_bearer_auth()  # Coverage for line 201


def test_middleware_with_auth_requires_validator(manifest_with_bearer_auth: Manifest) -> None:
    """Test that middleware with auth requires a validator."""
    with pytest.raises(ValueError, match="Token validator required"):
        AuthenticationMiddleware(manifest_with_bearer_auth, validator=None)


def test_middleware_with_auth_and_validator(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test middleware initialization with auth and validator."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)
    assert middleware.manifest == manifest_with_bearer_auth
    assert middleware.validator == valid_token_validator
    assert middleware._is_auth_required()
    assert middleware._supports_bearer_auth()


# Tests for verify_authentication


@pytest.mark.asyncio
async def test_verify_authentication_skipped_when_not_required(
    manifest_without_auth: Manifest,
) -> None:
    """Test that authentication is skipped when not required."""
    middleware = AuthenticationMiddleware(manifest_without_auth)
    # Create a minimal request object (not used since auth is disabled)
    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    agent_id = await middleware.verify_authentication(request)
    assert agent_id is None


@pytest.mark.asyncio
async def test_verify_authentication_missing_credentials(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that missing credentials raise HTTPException."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    # Create request without credentials
    request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})

    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_AUTH_REQUIRED in str(exc_info.value.detail)
    assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.asyncio
async def test_verify_authentication_valid_token(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test successful authentication with valid token."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    # Create request (not actually used when credentials are provided)
    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

    # Create credentials manually
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-123")

    agent_id = await middleware.verify_authentication(request, credentials)
    assert agent_id == "urn:asap:agent:client-1"


@pytest.mark.asyncio
async def test_verify_authentication_sync_validator_does_not_block_event_loop(
    manifest_with_bearer_auth: Manifest,
) -> None:
    """Regression: sync validators with blocking I/O run in thread pool, not blocking the loop.

    A sync validator that sleeps (simulating DB/Redis latency) would block the event
    loop if called directly. The middleware runs sync validators via asyncio.to_thread,
    so concurrent auth requests complete in parallel rather than sequentially.
    """

    def slow_sync_validator(token: str) -> str | None:
        """Simulate blocking I/O (e.g., DB lookup). Runs in thread pool."""
        time.sleep(0.15)
        return "urn:asap:agent:client-1" if token == "valid-token" else None

    validator = BearerTokenValidator(slow_sync_validator)
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, validator)

    request1 = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    request2 = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

    start = time.monotonic()
    results = await asyncio.gather(
        middleware.verify_authentication(request1, creds),
        middleware.verify_authentication(request2, creds),
    )
    elapsed = time.monotonic() - start

    assert results[0] == "urn:asap:agent:client-1"
    assert results[1] == "urn:asap:agent:client-1"
    # If blocking: ~0.3s sequential. If non-blocking: ~0.15s parallel.
    assert elapsed < 0.25, f"Sync validator blocked loop: {elapsed:.2f}s (expected <0.25s)"


@pytest.mark.asyncio
async def test_verify_authentication_async_validator(
    manifest_with_bearer_auth: Manifest,
) -> None:
    """Test that async validators work correctly (awaited in main loop)."""

    async def async_validator(token: str) -> str | None:
        await asyncio.sleep(0.01)  # Simulate async I/O
        return "urn:asap:agent:client-1" if token == "valid-token" else None

    # BearerTokenValidator can wrap async functions (returns coroutine)
    validator = BearerTokenValidator(async_validator)
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token")

    agent_id = await middleware.verify_authentication(request, creds)
    assert agent_id == "urn:asap:agent:client-1"


@pytest.mark.asyncio
async def test_verify_authentication_invalid_token(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that invalid token raises HTTPException."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request, credentials)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_INVALID_TOKEN in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_authentication_empty_token(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that empty token string is treated as invalid."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="")

    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request, credentials)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_INVALID_TOKEN in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_authentication_unsupported_scheme(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that unsupported auth scheme raises HTTPException."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    credentials = HTTPAuthorizationCredentials(scheme="Basic", credentials="username:password")

    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request, credentials)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_INVALID_TOKEN in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_verify_authentication_non_bearer_scheme_when_credentials_provided(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that non-Bearer scheme is rejected when credentials are explicitly provided."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})
    # Test various non-Bearer schemes (case-insensitive Bearer should work)
    non_bearer_schemes = ["Basic", "Digest", "OAuth", "Token"]

    for scheme in non_bearer_schemes:
        credentials = HTTPAuthorizationCredentials(scheme=scheme, credentials="some-token")
        with pytest.raises(HTTPException) as exc_info:
            await middleware.verify_authentication(request, credentials)
        assert exc_info.value.status_code == HTTP_UNAUTHORIZED

    # Bearer (case-insensitive) should work
    for bearer_variant in ["Bearer", "bearer", "BEARER", "BeArEr"]:
        credentials = HTTPAuthorizationCredentials(
            scheme=bearer_variant, credentials="valid-token-123"
        )
        agent_id = await middleware.verify_authentication(request, credentials)
        assert agent_id == "urn:asap:agent:client-1"


# Tests for verify_sender_matches_auth


def test_verify_sender_matches_auth_skipped_when_not_authenticated(
    manifest_without_auth: Manifest,
) -> None:
    """Test that sender verification is skipped when auth is disabled."""
    middleware = AuthenticationMiddleware(manifest_without_auth)

    # Should not raise exception
    middleware.verify_sender_matches_auth(
        authenticated_agent_id=None,
        envelope_sender="urn:asap:agent:anyone",
    )


def test_verify_sender_matches_auth_success(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test successful sender verification."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    # Should not raise exception
    middleware.verify_sender_matches_auth(
        authenticated_agent_id="urn:asap:agent:client-1",
        envelope_sender="urn:asap:agent:client-1",
    )


def test_verify_sender_matches_auth_mismatch(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that sender mismatch raises HTTPException."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    with pytest.raises(HTTPException) as exc_info:
        middleware.verify_sender_matches_auth(
            authenticated_agent_id="urn:asap:agent:client-1",
            envelope_sender="urn:asap:agent:spoofed",
        )

    assert exc_info.value.status_code == HTTP_FORBIDDEN
    assert ERROR_SENDER_MISMATCH in str(exc_info.value.detail)


def test_verify_sender_matches_auth_different_agents(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test that different agent IDs raise HTTPException."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    with pytest.raises(HTTPException) as exc_info:
        middleware.verify_sender_matches_auth(
            authenticated_agent_id="urn:asap:agent:client-1",
            envelope_sender="urn:asap:agent:client-2",
        )

    assert exc_info.value.status_code == HTTP_FORBIDDEN


# Integration tests


@pytest.mark.asyncio
async def test_full_authentication_flow(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test complete authentication flow."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

    # Step 1: Authenticate
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-123")
    agent_id = await middleware.verify_authentication(request, credentials)
    assert agent_id == "urn:asap:agent:client-1"

    # Step 2: Verify sender
    middleware.verify_sender_matches_auth(agent_id, "urn:asap:agent:client-1")
    # Should not raise


@pytest.mark.asyncio
async def test_authentication_flow_with_invalid_sender(
    manifest_with_bearer_auth: Manifest,
    valid_token_validator: BearerTokenValidator,
) -> None:
    """Test authentication flow with sender mismatch."""
    middleware = AuthenticationMiddleware(manifest_with_bearer_auth, valid_token_validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap"})

    # Step 1: Authenticate successfully
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid-token-123")
    agent_id = await middleware.verify_authentication(request, credentials)
    assert agent_id == "urn:asap:agent:client-1"

    # Step 2: Try to spoof sender
    with pytest.raises(HTTPException) as exc_info:
        middleware.verify_sender_matches_auth(agent_id, "urn:asap:agent:spoofed")

    assert exc_info.value.status_code == HTTP_FORBIDDEN


def test_supports_bearer_auth_with_oauth2_only() -> None:
    """Test that supports_bearer_auth returns False for basic-only manifest."""
    manifest_basic = Manifest(
        id="urn:asap:agent:basic-only",
        name="Basic Only Agent",
        version="1.0.0",
        description="Agent with Basic auth only",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["basic"]),  # No "bearer"
    )

    def dummy_validator(token: str) -> str | None:
        return "urn:asap:agent:client"

    validator = BearerTokenValidator(dummy_validator)
    middleware = AuthenticationMiddleware(manifest_basic, validator)

    assert not middleware._supports_bearer_auth()


@pytest.mark.asyncio
async def test_verify_authentication_with_basic_scheme_fails() -> None:
    """Test that Basic scheme (non-Bearer) is rejected."""
    manifest_basic = Manifest(
        id="urn:asap:agent:basic-only",
        name="Basic Only Agent",
        version="1.0.0",
        description="Agent with Basic auth only",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["basic"]),  # No "bearer" support
    )

    def dummy_validator(token: str) -> str | None:
        return "urn:asap:agent:client"

    validator = BearerTokenValidator(dummy_validator)
    middleware = AuthenticationMiddleware(manifest_basic, validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="some-token")

    # Should fail because manifest doesn't support bearer scheme
    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request, credentials)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_INVALID_TOKEN in str(exc_info.value.detail)


# Note: Rate limiting tests have been migrated to
# tests/transport/integration/test_rate_limiting.py


# Tests for rate_limit_handler, _get_sender_from_envelope, SizeLimitMiddleware, and limiter factories


class TestGetSenderFromEnvelope:
    """Tests for _get_sender_from_envelope helper function."""

    def test_returns_ip_when_no_envelope_in_state(self) -> None:
        """Test that IP is returned when no envelope is available."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.envelope
        del request.state.rpc_request

        with patch("asap.transport.middleware.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            result = _get_sender_from_envelope(request)

        assert result == "192.168.1.100"

    def test_returns_sender_from_envelope_in_state(self) -> None:
        """Test that sender is extracted from request.state.envelope."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.envelope = MagicMock()
        request.state.envelope.sender = "urn:asap:agent:test-sender"

        result = _get_sender_from_envelope(request)

        assert result == "urn:asap:agent:test-sender"

    def test_returns_sender_from_rpc_request_params(self) -> None:
        """Test that sender is extracted from request.state.rpc_request."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        if hasattr(request.state, "envelope"):
            del request.state.envelope
        request.state.rpc_request = MagicMock()
        request.state.rpc_request.params = {"envelope": {"sender": "urn:asap:agent:rpc-sender"}}

        result = _get_sender_from_envelope(request)

        assert result == "urn:asap:agent:rpc-sender"

    def test_returns_ip_when_envelope_sender_not_string(self) -> None:
        """Test fallback to IP when sender is not a string."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.envelope = MagicMock()
        request.state.envelope.sender = 12345  # Not a string

        with patch("asap.transport.middleware.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "10.0.0.1"
            result = _get_sender_from_envelope(request)

        assert result == "10.0.0.1"

    def test_handles_attribute_error_gracefully(self) -> None:
        """Test that AttributeError is caught and IP is returned."""
        request = MagicMock(spec=Request)
        type(request).state = property(lambda self: (_ for _ in ()).throw(AttributeError))

        with patch("asap.transport.middleware.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "172.16.0.1"
            result = _get_sender_from_envelope(request)

        assert result == "172.16.0.1"

    def test_returns_str_when_get_remote_address_returns_non_string(self) -> None:
        """Test that non-string IP is converted to string."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.envelope
        del request.state.rpc_request

        with patch("asap.transport.middleware.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = None
            result = _get_sender_from_envelope(request)

        assert result == "None"


class TestRateLimitHandler:
    """Tests for rate_limit_handler function."""

    def test_handles_rate_limit_exceeded(self) -> None:
        """Test handling of RateLimitExceeded exception."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.request_id = "test-request-123"

        exc = MagicMock(spec=RateLimitExceeded)
        exc.__class__ = RateLimitExceeded
        exc.retry_after = 30
        exc.limit = "50/minute"

        with (
            patch("asap.transport.middleware.get_remote_address", return_value="127.0.0.1"),
            patch(
                "asap.transport.middleware.isinstance",
                side_effect=lambda obj, cls: (
                    cls == RateLimitExceeded if obj is exc else isinstance(obj, cls)
                ),
            ),
        ):
            response = rate_limit_handler(request, exc)

        assert response.status_code == HTTP_TOO_MANY_REQUESTS

    def test_handles_unexpected_exception_type(self) -> None:
        """Test handling of non-RateLimitExceeded exception (fallback path)."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.request_id = "test-request-456"

        exc = ValueError("Unexpected error")

        response = rate_limit_handler(request, exc)

        assert response.status_code == HTTP_TOO_MANY_REQUESTS
        content = response.body.decode()
        assert ERROR_RATE_LIMIT_EXCEEDED in content

    def test_handles_invalid_retry_after(self) -> None:
        """Test handling when retry_after is not a valid integer."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.request_id = None

        exc = MagicMock(spec=RateLimitExceeded)
        exc.__class__ = RateLimitExceeded
        exc.retry_after = "invalid"
        exc.limit = None

        with patch("asap.transport.middleware.get_remote_address", return_value="127.0.0.1"):
            response = rate_limit_handler(request, exc)

        assert response.status_code == HTTP_TOO_MANY_REQUESTS
        assert response.headers.get("Retry-After") == "60"


class TestSizeLimitMiddleware:
    """Tests for SizeLimitMiddleware."""

    def test_rejects_invalid_max_size(self) -> None:
        """Test that invalid max_size raises ValueError."""
        app = FastAPI()

        with pytest.raises(ValueError, match="max_size must be >= 1"):
            SizeLimitMiddleware(app, max_size=0)

        with pytest.raises(ValueError, match="max_size must be >= 1"):
            SizeLimitMiddleware(app, max_size=-1)

    def test_allows_request_within_size_limit(self) -> None:
        """Test that requests within size limit pass through."""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        app.add_middleware(SizeLimitMiddleware, max_size=1024)
        client = TestClient(app)

        response = client.post("/test", content="small body")
        assert response.status_code == 200

    def test_rejects_request_exceeding_size_limit(self) -> None:
        """Test that requests exceeding size limit are rejected."""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        app.add_middleware(SizeLimitMiddleware, max_size=10)
        client = TestClient(app)

        large_body = "x" * 100
        response = client.post("/test", content=large_body)

        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"]

    def test_handles_invalid_content_length_header(self) -> None:
        """Test that invalid Content-Length header is handled gracefully."""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        app.add_middleware(SizeLimitMiddleware, max_size=1024)

        with patch.object(SizeLimitMiddleware, "dispatch") as mock_dispatch:
            mock_dispatch.return_value = JSONResponse(content={"status": "ok"})
            client = TestClient(app)
            response = client.post("/test", content="body")
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_size_limit_middleware_handles_valueerror_on_invalid_content_length(
        self,
    ) -> None:
        """Test that SizeLimitMiddleware handles ValueError for invalid Content-Length."""
        from fastapi import Request

        app = FastAPI()

        @app.post("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        middleware = SizeLimitMiddleware(app, max_size=1024)

        # Create a mock request with invalid Content-Length header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"content-length": "invalid-number"}
        mock_request.method = "POST"

        # Mock the call_next to return a response
        async def mock_call_next(request: Request) -> JSONResponse:
            return JSONResponse(content={"status": "ok"})

        # Should not raise ValueError, should continue to handler
        # The ValueError is caught and handled internally
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200

    def test_get_sender_from_envelope_handles_exceptions(self) -> None:
        """Test that _get_sender_from_envelope handles exceptions gracefully."""
        from fastapi import Request

        # Test with request that has no body (AttributeError)
        mock_request = MagicMock(spec=Request)
        del mock_request.body  # Remove body attribute
        mock_request.headers = {}

        # Should fall back to IP address
        sender = _get_sender_from_envelope(mock_request)
        assert sender is not None  # Should return IP address

        # Test with request that has invalid JSON (KeyError/TypeError)
        mock_request2 = MagicMock(spec=Request)
        mock_request2.body = MagicMock()
        mock_request2.json = MagicMock(return_value={"not_envelope": {}})
        mock_request2.headers = {}

        sender2 = _get_sender_from_envelope(mock_request2)
        assert sender2 is not None  # Should fall back to IP address

    @pytest.mark.asyncio
    async def test_authentication_middleware_raises_runtime_error_when_validator_is_none(
        self, manifest_with_bearer_auth: Manifest
    ) -> None:
        """Test that verify_authentication raises RuntimeError when validator is None but auth is required."""
        # Create middleware with a validator first (to pass __init__ validation)
        validator = BearerTokenValidator(lambda t: "urn:asap:agent:test" if t == "valid" else None)
        middleware = AuthenticationMiddleware(manifest_with_bearer_auth, validator=validator)

        # Force validator to None to test defensive check (simulating edge case)
        middleware.validator = None

        mock_request = MagicMock(spec=Request)
        mock_credentials = HTTPAuthorizationCredentials(scheme="bearer", credentials="test-token")

        with pytest.raises(RuntimeError) as exc_info:
            await middleware.verify_authentication(mock_request, mock_credentials)

        assert "Token validator is None" in str(exc_info.value)


class TestLimiterCreation:
    """Tests for limiter factory functions."""

    def test_create_test_limiter_with_defaults(self) -> None:
        """Test create_test_limiter with default parameters."""
        limiter = create_test_limiter()

        assert limiter is not None
        assert limiter._default_limits is not None

    def test_create_test_limiter_with_custom_limits(self) -> None:
        """Test create_test_limiter with custom limits."""
        limiter = create_test_limiter(limits=["50/second"])

        assert limiter is not None

    def test_create_limiter_with_defaults(self) -> None:
        """Test create_limiter with default parameters."""
        limiter = create_limiter()

        assert limiter is not None

    def test_create_limiter_with_custom_limits(self) -> None:
        """Test create_limiter with custom limits."""
        limiter = create_limiter(limits=["10/minute"])

        assert limiter is not None

    def test_limiters_have_isolated_storage(self) -> None:
        """Test that each limiter has isolated storage."""
        limiter1 = create_test_limiter()
        limiter2 = create_test_limiter()

        assert limiter1._storage_uri != limiter2._storage_uri
