"""Integration tests for OAuth2 token validation middleware.

Covers: missing token (401), expired token (401), insufficient scope (403),
valid token with correct scope (200). Uses joserfc for JWT signing and
jwks_fetcher for JWKS mocking.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from joserfc import jwk, jwt as jose_jwt
from starlette.testclient import TestClient

from asap.auth.middleware import OAuth2Middleware


def _minimal_app() -> FastAPI:
    """Minimal FastAPI app that returns 200 on GET /asap and GET /other."""
    app = FastAPI()

    @app.get("/asap")
    async def asap() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/other")
    async def other() -> dict[str, str]:
        return {"status": "ok"}

    return app


async def _mock_jwks_fetcher(_uri: str) -> jwk.KeySet:
    """Return a minimal RSA key set for testing (used to validate signed JWTs)."""
    # Single RSA public key for verification (tests will sign with matching key)
    key = jwk.RSAKey.generate_key(2048, private=True)
    return jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})


def test_oauth2_middleware_rejects_request_without_bearer_token() -> None:
    """Verify OAuth2Middleware returns 401 when Authorization header is missing."""
    app = _minimal_app()
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/.well-known/jwks.json",
        path_prefix="/asap",
        jwks_fetcher=lambda uri: _mock_jwks_fetcher(uri),
    )

    with TestClient(app) as client:
        response = client.get("/asap")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_oauth2_middleware_rejects_request_with_wrong_scheme() -> None:
    """Verify OAuth2Middleware returns 401 when Authorization is not Bearer."""
    app = _minimal_app()
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        path_prefix="/asap",
        jwks_fetcher=lambda uri: _mock_jwks_fetcher(uri),
    )

    with TestClient(app) as client:
        response = client.get("/asap", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required"}


def test_oauth2_middleware_passes_through_unprotected_path() -> None:
    """Verify requests to path outside path_prefix are not validated."""
    app = _minimal_app()
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        path_prefix="/asap",
        jwks_fetcher=lambda uri: _mock_jwks_fetcher(uri),
    )

    with TestClient(app) as client:
        response = client.get("/other")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_oauth2_middleware_accepts_valid_jwt_with_required_scope() -> None:
    """Verify valid JWT with required scope returns 200 and sets oauth2_claims."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = FastAPI()

    @app.get("/asap/me")
    async def asap_me(request: Request) -> dict[str, Any]:
        claims = getattr(request.state, "oauth2_claims", None)
        if claims is None:
            return {"claims": None}
        return {"claims": {"sub": claims.sub, "scope": claims.scope, "exp": claims.exp}}

    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        required_scope="asap:execute",
        path_prefix="/asap",
        jwks_fetcher=jwks_fetcher,
    )

    # Build valid JWT with sub, scope, exp
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": "urn:asap:agent:test-client",
        "scope": "asap:read asap:execute",
        "exp": now + 3600,
        "iat": now,
    }
    token = jose_jwt.encode(header, claims, key)

    with TestClient(app) as client:
        response = client.get("/asap/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()
    assert data["claims"]["sub"] == "urn:asap:agent:test-client"
    assert "asap:execute" in data["claims"]["scope"]


def test_oauth2_middleware_rejects_expired_token() -> None:
    """Verify OAuth2Middleware returns 401 when JWT is expired."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = _minimal_app()
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        path_prefix="/asap",
        jwks_fetcher=jwks_fetcher,
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": "urn:asap:agent:expired",
        "scope": "asap:execute",
        "exp": now - 3600,  # Expired 1 hour ago
        "iat": now - 7200,
    }
    token = jose_jwt.encode(header, claims, key)

    with TestClient(app) as client:
        response = client.get("/asap", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid authentication token"}


def test_oauth2_middleware_returns_403_when_scope_insufficient() -> None:
    """Verify JWT without required scope returns 403."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})

    async def jwks_fetcher(_uri: str) -> jwk.KeySet:
        return key_set

    app = _minimal_app()
    app.add_middleware(
        OAuth2Middleware,
        jwks_uri="https://auth.example.com/jwks.json",
        required_scope="asap:admin",
        path_prefix="/asap",
        jwks_fetcher=jwks_fetcher,
    )

    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {"sub": "urn:asap:agent:client", "scope": "asap:read asap:execute", "exp": now + 3600}
    token = jose_jwt.encode(header, claims, key)

    with TestClient(app) as client:
        response = client.get("/asap", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient scope"}
