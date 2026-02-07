"""Unit tests for OIDC discovery and OIDC + JWKS integration."""

import time

import httpx
import pytest
from joserfc import jwk
from joserfc import jwt as jose_jwt
from joserfc.errors import JoseError

from asap.auth.jwks import JWKSValidator
from asap.auth.oidc import OIDCDiscovery


def _discovery_response(jwks_uri: str = "https://auth.example.com/.well-known/jwks.json") -> dict:
    """Minimal valid OIDC discovery document."""
    return {
        "issuer": "https://auth.example.com",
        "token_endpoint": "https://auth.example.com/oauth/token",
        "jwks_uri": jwks_uri,
        "scopes_supported": ["openid", "asap:execute"],
    }


def _make_jwks_response(public_key: jwk.RSAKey) -> dict:
    """Build JWKS JSON response from RSA key."""
    return {"keys": [public_key.as_dict(private=False)]}


async def test_discover_fetches_and_parses_config() -> None:
    """Verify discover() fetches and parses OIDC config from well-known URL."""
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_discovery_response())

    discovery = OIDCDiscovery(
        "https://auth.example.com",
        transport=httpx.MockTransport(mock_handler),
    )
    config = await discovery.discover()

    assert config.issuer == "https://auth.example.com"
    assert config.token_endpoint == "https://auth.example.com/oauth/token"
    assert config.jwks_uri == "https://auth.example.com/.well-known/jwks.json"
    assert "openid" in config.scopes_supported
    assert "asap:execute" in config.scopes_supported
    assert call_count == 1


async def test_discover_second_call_uses_cache() -> None:
    """Verify second discover() uses cache (no extra HTTP call)."""
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=_discovery_response())

    discovery = OIDCDiscovery(
        "https://auth.example.com",
        transport=httpx.MockTransport(mock_handler),
    )

    config_1 = await discovery.discover()
    config_2 = await discovery.discover()

    assert config_1.issuer == config_2.issuer
    assert config_1 is config_2
    assert call_count == 1


async def test_discover_raises_on_missing_issuer() -> None:
    """Verify discover() raises ValueError when issuer is missing."""
    data = _discovery_response()
    del data["issuer"]

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    discovery = OIDCDiscovery(
        "https://auth.example.com",
        transport=httpx.MockTransport(mock_handler),
    )

    with pytest.raises(ValueError, match="issuer"):
        await discovery.discover()


async def test_discover_raises_on_http_error() -> None:
    """Verify discover() raises on HTTP error."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    discovery = OIDCDiscovery(
        "https://auth.example.com",
        transport=httpx.MockTransport(mock_handler),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await discovery.discover()


async def test_oidc_jwks_integration_jwt_validation_with_discovered_jwks_uri() -> None:
    """Verify JWT validation using OIDC-discovered jwks_uri (OIDC + JWKS integration)."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    jwks_json = _make_jwks_response(key)
    jwks_url = "https://auth.example.com/.well-known/jwks.json"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "openid-configuration" in str(request.url) or request.url.path.endswith(
            "openid-configuration"
        ):
            return httpx.Response(
                200,
                json=_discovery_response(jwks_uri=jwks_url),
            )
        if "jwks" in str(request.url) or "jwks.json" in str(request.url):
            return httpx.Response(200, json=jwks_json)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    discovery = OIDCDiscovery("https://auth.example.com", transport=transport)
    config = await discovery.discover()

    validator = JWKSValidator(config.jwks_uri, transport=transport)
    now = int(time.time())
    token = jose_jwt.encode(
        {"alg": "RS256"},
        {"sub": "urn:asap:agent:test", "scope": "asap:execute", "exp": now + 3600},
        key,
    )

    claims = await validator.validate_token(token)

    assert claims["sub"] == "urn:asap:agent:test"
    assert "asap:execute" in (claims.get("scope") or "").split()


async def test_oidc_jwks_integration_rejects_invalid_token() -> None:
    """Verify invalid token is rejected when validating with OIDC-discovered jwks_uri."""
    key = jwk.RSAKey.generate_key(2048, private=True)
    other_key = jwk.RSAKey.generate_key(2048, private=True)
    jwks_json = _make_jwks_response(other_key)
    jwks_url = "https://auth.example.com/.well-known/jwks.json"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if "openid-configuration" in str(request.url) or request.url.path.endswith(
            "openid-configuration"
        ):
            return httpx.Response(
                200,
                json=_discovery_response(jwks_uri=jwks_url),
            )
        if "jwks" in str(request.url) or "jwks.json" in str(request.url):
            return httpx.Response(200, json=jwks_json)
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    discovery = OIDCDiscovery("https://auth.example.com", transport=transport)
    config = await discovery.discover()

    validator = JWKSValidator(config.jwks_uri, transport=transport)
    now = int(time.time())
    token = jose_jwt.encode(
        {"alg": "RS256"},
        {"sub": "urn:asap:agent:test", "exp": now + 3600},
        key,
    )

    with pytest.raises(JoseError):
        await validator.validate_token(token)


async def test_oidc_discover_raises_on_missing_jwks_uri() -> None:
    """Verify discover() raises ValueError when jwks_uri is missing."""
    data = _discovery_response()
    del data["jwks_uri"]

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=data)

    discovery = OIDCDiscovery(
        "https://auth.example.com",
        transport=httpx.MockTransport(mock_handler),
    )

    with pytest.raises(ValueError, match="jwks_uri"):
        await discovery.discover()
