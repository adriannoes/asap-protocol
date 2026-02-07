"""OAuth2 token introspection for opaque tokens (RFC 7662).

Provides introspection of non-JWT (opaque) tokens via the provider's
token introspection endpoint. Results are cached using TTL derived from
the token's remaining lifetime.
"""

from __future__ import annotations

import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

import httpx
from pydantic import Field

from asap.models.base import ASAPBaseModel

# Default TTL for inactive token cache entries (reduce introspection endpoint load)
INACTIVE_TOKEN_CACHE_TTL_SECONDS = 60.0

# Max TTL cap for active token cache (e.g. 1 hour)
MAX_ACTIVE_CACHE_TTL_SECONDS = 3600.0

# Buffer before expiry to consider token near-expired (seconds)
EXPIRY_BUFFER_SECONDS = 30


def _parse_scope(claim: Any) -> list[str]:
    """Normalize scope claim to a list of strings.

    RFC 7662: scope is a space-separated string. Some providers may return a list.
    """
    if claim is None:
        return []
    if isinstance(claim, list):
        return [str(s) for s in claim]
    if isinstance(claim, str):
        return [s.strip() for s in claim.split() if s.strip()]
    return []


class TokenInfo(ASAPBaseModel):
    """Token metadata from OAuth2 introspection (RFC 7662).

    Represents the response from a token introspection endpoint.
    Only populated when the token is active (active=True).

    Attributes:
        active: Whether the token is currently active.
        sub: Subject (e.g. agent URN or user id).
        scope: List of scope strings.
        exp: Expiration timestamp (Unix). None if not provided.
        client_id: Client that requested the token (optional).
        username: Resource owner identifier (optional).
        token_type: Token type, typically "Bearer" (optional).
    """

    active: bool = Field(..., description="Whether the token is currently active")
    sub: str | None = Field(default=None, description="Subject of the token")
    scope: list[str] = Field(default_factory=list, description="Authorized scopes")
    exp: int | None = Field(default=None, description="Expiration timestamp (Unix)")
    client_id: str | None = Field(default=None, description="Client identifier")
    username: str | None = Field(default=None, description="Resource owner identifier")
    token_type: str | None = Field(default=None, description="Token type")

    def cache_ttl_seconds(self) -> float:
        """Compute cache TTL from token lifetime.

        Returns TTL for active tokens based on exp, or INACTIVE_TOKEN_CACHE_TTL_SECONDS
        for inactive tokens.
        """
        if not self.active:
            return INACTIVE_TOKEN_CACHE_TTL_SECONDS
        if self.exp is None:
            return INACTIVE_TOKEN_CACHE_TTL_SECONDS
        remaining = self.exp - time.time() - EXPIRY_BUFFER_SECONDS
        if remaining <= 0:
            return 0.0
        return min(float(remaining), MAX_ACTIVE_CACHE_TTL_SECONDS)


class _CacheEntry:
    """Cache entry for introspection results with TTL."""

    def __init__(self, info: TokenInfo, ttl: float) -> None:
        self.info = info
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class TokenIntrospector:
    """RFC 7662 token introspection client with caching.

    Calls the OAuth2 provider's introspection endpoint to validate opaque
    tokens. Authenticates using client credentials (Basic auth).
    Caches results with TTL derived from token lifetime.

    Example:
        >>> introspector = TokenIntrospector(
        ...     introspection_url="https://auth.example.com/oauth/introspect",
        ...     client_id="my-client",
        ...     client_secret="secret",
        ... )
        >>> info = await introspector.introspect("opaque-token-here")
        >>> if info and info.active:
        ...     print(info.sub, info.scope)
    """

    def __init__(
        self,
        introspection_url: str,
        client_id: str,
        client_secret: str,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        max_cache_size: int = 1000,
    ) -> None:
        """Initialize the introspection client.

        Args:
            introspection_url: URL of the introspection endpoint (RFC 7662).
            client_id: OAuth2 client ID for Basic auth to the endpoint.
            client_secret: OAuth2 client secret for Basic auth.
            transport: Optional httpx transport for testing.
            max_cache_size: Maximum introspection result cache entries (0 = unlimited).
        """
        self._url = introspection_url
        self._client_id = client_id
        self._client_secret = client_secret
        self._transport = transport
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._max_size = max_cache_size

    async def introspect(self, token: str) -> TokenInfo | None:
        """Introspect a token and return metadata if active.

        Returns cached result when valid. For active tokens, TTL is derived
        from exp. For inactive tokens, a short TTL is used to reduce load.

        Args:
            token: The opaque access token to introspect.

        Returns:
            TokenInfo if the token is active, None if inactive or invalid.
            Raises httpx.HTTPError on network or protocol errors.
        """
        with self._lock:
            entry = self._cache.get(token)
            if entry is not None and not entry.is_expired():
                self._cache.move_to_end(token)
                return entry.info if entry.info.active else None

        info = await self._do_introspect(token)

        with self._lock:
            ttl = info.cache_ttl_seconds()
            if token in self._cache:
                del self._cache[token]
            elif self._max_size > 0:
                while len(self._cache) >= self._max_size:
                    self._cache.popitem(last=False)
            self._cache[token] = _CacheEntry(info, ttl)

        return info if info.active else None

    async def _do_introspect(self, token: str) -> TokenInfo:
        """Perform the HTTP introspection request."""
        auth = (self._client_id, self._client_secret)
        data = {"token": token, "token_type_hint": "access_token"}

        kwargs: dict[str, Any] = {}
        if self._transport is not None:
            kwargs["transport"] = self._transport

        async with httpx.AsyncClient(**kwargs) as client:
            resp = await client.post(
                self._url,
                auth=auth,
                data=data,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            body = resp.json()

        active = body.get("active", False)
        if not isinstance(active, bool):
            active = False

        sub = body.get("sub")
        sub_str = str(sub) if sub is not None else None

        scope_list = _parse_scope(body.get("scope"))

        exp = body.get("exp")
        if exp is not None:
            try:
                exp_int = int(exp) if isinstance(exp, (int, float)) else None
            except (TypeError, ValueError):
                exp_int = None
        else:
            exp_int = None

        client_id = body.get("client_id")
        client_id_str = str(client_id) if client_id is not None else None

        username = body.get("username")
        username_str = str(username) if username is not None else None

        token_type = body.get("token_type")
        token_type_str = str(token_type) if token_type is not None else None

        return TokenInfo(
            active=active,
            sub=sub_str,
            scope=scope_list,
            exp=exp_int,
            client_id=client_id_str,
            username=username_str,
            token_type=token_type_str,
        )
