"""OpenID Connect discovery for ASAP Protocol.

Fetches OAuth2/OIDC configuration from provider's well-known endpoint
(/.well-known/openid-configuration), enabling auto-configuration for
Auth0, Keycloak, Azure AD, and other OIDC-compliant providers.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Optional

import httpx
from authlib.oidc.discovery import get_well_known_url
from pydantic import Field

from asap.models.base import ASAPBaseModel
from asap.observability import get_logger

logger = get_logger(__name__)

DISCOVERY_CACHE_TTL_SECONDS = 3600.0


class _DiscoveryCacheEntry:
    """Cache entry for OIDC discovery config with TTL."""

    def __init__(self, config: "OIDCConfig", ttl: float) -> None:
        self.config = config
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class OIDCConfig(ASAPBaseModel):
    """OIDC provider configuration from discovery endpoint.

    Subset of OpenID Provider Metadata (OpenID Connect Discovery 1.0)
    needed for ASAP OAuth2 client and JWT validation.

    Attributes:
        issuer: Provider issuer identifier (REQUIRED in OIDC).
        token_endpoint: OAuth2 token endpoint URL.
        jwks_uri: JWKS endpoint URL for JWT signature validation.
        scopes_supported: Optional list of supported scopes (e.g. openid, profile).
    """

    issuer: str = Field(..., description="Provider issuer identifier")
    token_endpoint: str = Field(..., description="OAuth2 token endpoint URL")
    jwks_uri: str = Field(..., description="JWKS endpoint URL")
    scopes_supported: list[str] = Field(
        default_factory=list,
        description="Supported OAuth2 scopes",
    )


class OIDCDiscovery:
    """OpenID Connect discovery client.

    Fetches provider configuration from {issuer}/.well-known/openid-configuration
    per OpenID Connect Discovery 1.0. Uses Authlib's well-known URL builder.

    Example:
        >>> discovery = OIDCDiscovery(issuer_url="https://auth.example.com")
        >>> config = await discovery.discover()
        >>> oauth2_client = OAuth2ClientCredentials(
        ...     client_id="my-client",
        ...     client_secret="secret",
        ...     token_url=config.token_endpoint,
        ... )
        >>> # Use config.jwks_uri for OAuth2Config middleware
    """

    def __init__(
        self,
        issuer_url: str,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        """Initialize the discovery client.

        Args:
            issuer_url: Issuer URL (e.g. https://auth.example.com or
                https://tenant.auth0.com).
            transport: Optional httpx transport for testing.
        """
        self._issuer_url = issuer_url.rstrip("/")
        self._transport = transport
        self._cache_entry: Optional[_DiscoveryCacheEntry] = None
        self._lock = Lock()

    async def discover(self) -> OIDCConfig:
        """Fetch and parse OIDC configuration from the provider.

        Uses a thread-safe cache with TTL of 1 hour. Second call within TTL
        returns cached config without HTTP request.

        Returns:
            OIDCConfig with token_endpoint, jwks_uri, issuer, scopes_supported.

        Raises:
            httpx.HTTPError: On network or protocol errors.
            ValueError: If required fields (issuer, token_endpoint, jwks_uri)
                are missing from the discovery response.
        """
        with self._lock:
            if self._cache_entry is not None and not self._cache_entry.is_expired():
                return self._cache_entry.config

        config = await self._fetch_discovery()

        with self._lock:
            self._cache_entry = _DiscoveryCacheEntry(config, DISCOVERY_CACHE_TTL_SECONDS)
        return config

    async def _fetch_discovery(self) -> OIDCConfig:
        """Perform HTTP fetch and parse discovery document (no cache)."""
        url = get_well_known_url(self._issuer_url, external=True)

        kwargs: dict[str, Any] = {"timeout": httpx.Timeout(10.0)}
        if self._transport is not None:
            kwargs["transport"] = self._transport

        async with httpx.AsyncClient(**kwargs) as client:
            resp = await client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()

        issuer = data.get("issuer")
        token_endpoint = data.get("token_endpoint")
        jwks_uri = data.get("jwks_uri")

        if not issuer or not isinstance(issuer, str):
            raise ValueError("Discovery response missing required 'issuer'")
        if not token_endpoint or not isinstance(token_endpoint, str):
            raise ValueError("Discovery response missing required 'token_endpoint'")
        if not jwks_uri or not isinstance(jwks_uri, str):
            raise ValueError("Discovery response missing required 'jwks_uri'")

        scopes = data.get("scopes_supported")
        scopes_list = [str(s) for s in scopes] if isinstance(scopes, list) else []

        config = OIDCConfig(
            issuer=issuer,
            token_endpoint=token_endpoint,
            jwks_uri=jwks_uri,
            scopes_supported=scopes_list,
        )
        logger.info("asap.oidc.discovered", issuer=config.issuer)
        return config
