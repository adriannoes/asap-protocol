"""Tests for authentication middleware.

This module tests the authentication middleware functionality:
- Bearer token validation
- Sender verification
- Authentication bypass when not configured
- Error responses for invalid auth
- Custom token validators
"""

import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.transport.middleware import (
    ERROR_AUTH_REQUIRED,
    ERROR_INVALID_TOKEN,
    ERROR_SENDER_MISMATCH,
    HTTP_FORBIDDEN,
    HTTP_UNAUTHORIZED,
    AuthenticationMiddleware,
    BearerTokenValidator,
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
    """Test that supports_bearer_auth returns False for OAuth2-only manifest."""
    manifest_oauth2 = Manifest(
        id="urn:asap:agent:oauth2-only",
        name="OAuth2 Only Agent",
        version="1.0.0",
        description="Agent with OAuth2 only",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["oauth2"]),  # No "bearer"
    )

    def dummy_validator(token: str) -> str | None:
        return "urn:asap:agent:client"

    validator = BearerTokenValidator(dummy_validator)
    middleware = AuthenticationMiddleware(manifest_oauth2, validator)

    assert not middleware._supports_bearer_auth()


@pytest.mark.asyncio
async def test_verify_authentication_with_oauth2_scheme_fails() -> None:
    """Test that OAuth2 scheme (non-Bearer) is rejected."""
    manifest_oauth2 = Manifest(
        id="urn:asap:agent:oauth2-only",
        name="OAuth2 Only Agent",
        version="1.0.0",
        description="Agent with OAuth2 only",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="test", description="Test skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["oauth2"]),  # No "bearer" support
    )

    def dummy_validator(token: str) -> str | None:
        return "urn:asap:agent:client"

    validator = BearerTokenValidator(dummy_validator)
    middleware = AuthenticationMiddleware(manifest_oauth2, validator)

    request = Request(scope={"type": "http", "method": "POST", "path": "/asap", "headers": []})
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="some-token")

    # Should fail because manifest doesn't support bearer scheme
    with pytest.raises(HTTPException) as exc_info:
        await middleware.verify_authentication(request, credentials)

    assert exc_info.value.status_code == HTTP_UNAUTHORIZED
    assert ERROR_INVALID_TOKEN in str(exc_info.value.detail)
