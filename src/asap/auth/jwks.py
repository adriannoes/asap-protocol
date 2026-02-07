"""JWKS validation for ASAP Protocol.

Fetches JSON Web Key Sets from provider URIs and validates JWT signatures
using joserfc. Supports key rotation (unknown kid triggers refresh).
Caches JWKS with TTL 24 hours; cache is invalidated on validation failure.
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Any, Optional

import httpx
from joserfc import jwk
from joserfc import jwt as jose_jwt
from joserfc.errors import JoseError

from asap.observability import get_logger

logger = get_logger(__name__)

JWKS_CACHE_TTL_SECONDS = 86400.0


class _JWKSCacheEntry:
    """Cache entry for JWKS KeySet with TTL."""

    def __init__(self, key_set: jwk.KeySet, ttl: float) -> None:
        self.key_set = key_set
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


# Type alias for decoded JWT claims
Claims = dict[str, Any]


async def fetch_keys(
    jwks_uri: str,
    *,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> jwk.KeySet:
    """Fetch JWKS from URI and return a joserfc KeySet.

    Args:
        jwks_uri: URL of the JWKS endpoint (e.g. from OIDC discovery).
        transport: Optional httpx transport for testing.

    Returns:
        KeySet usable with jose_jwt.decode() for JWT validation.

    Raises:
        httpx.HTTPError: On network or protocol errors.
    """
    kwargs: dict[str, Any] = {"timeout": httpx.Timeout(10.0)}
    if transport is not None:
        kwargs["transport"] = transport

    async with httpx.AsyncClient(**kwargs) as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        data = resp.json()

    key_set = jwk.KeySet.import_key_set(data)
    logger.info("asap.jwks.fetched", uri=jwks_uri, key_count=len(key_set.keys))
    return key_set


def validate_jwt(token: str, key_set: jwk.KeySet) -> Claims:
    """Validate JWT signature and return claims.

    Decodes the JWT and verifies the signature using the provided KeySet.
    Does not check exp, nbf, or other claims—caller should validate as needed.

    Args:
        token: Raw JWT string (e.g. from Authorization: Bearer <token>).
        key_set: JWKS KeySet from fetch_keys().

    Returns:
        Decoded claims dict (sub, scope, exp, etc.).

    Raises:
        JoseError: If signature is invalid or token is malformed (BadSignatureError,
            DecodeError, InvalidKeyIdError, etc.).
    """
    token_obj = jose_jwt.decode(token, key_set)
    return dict(token_obj.claims)


class JWKSValidator:
    """JWKS fetcher and JWT validator with key rotation support.

    Fetches keys from jwks_uri, validates JWTs, and refetches keys when
    validation fails (e.g. unknown kid due to key rotation).

    Example:
        >>> validator = JWKSValidator(jwks_uri="https://auth.example.com/jwks.json")
        >>> keys = await validator.fetch_keys()
        >>> claims = validator.validate_jwt(token, keys)
        >>> # Or with auto-refresh on unknown kid:
        >>> claims = await validator.validate_token(token)
    """

    def __init__(
        self,
        jwks_uri: str,
        *,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        """Initialize the validator.

        Args:
            jwks_uri: URL of the JWKS endpoint.
            transport: Optional httpx transport for testing.
        """
        self._jwks_uri = jwks_uri
        self._transport = transport
        self._key_set: Optional[jwk.KeySet] = None
        self._keys_cache: Optional[_JWKSCacheEntry] = None
        self._lock = Lock()

    async def fetch_keys(self, jwks_uri: Optional[str] = None) -> jwk.KeySet:
        """Fetch JWKS from URI and return KeySet.

        Uses a thread-safe cache with TTL of 24 hours. Repeated calls
        within TTL return the cached KeySet without HTTP request.

        Args:
            jwks_uri: Override URI (defaults to constructor value).

        Returns:
            KeySet for JWT validation.
        """
        uri = jwks_uri or self._jwks_uri
        with self._lock:
            if (
                self._keys_cache is not None
                and not self._keys_cache.is_expired()
                and uri == self._jwks_uri
            ):
                self._key_set = self._keys_cache.key_set
                return self._keys_cache.key_set

        key_set = await fetch_keys(uri, transport=self._transport)

        with self._lock:
            self._keys_cache = _JWKSCacheEntry(key_set, JWKS_CACHE_TTL_SECONDS)
            self._key_set = key_set
        return key_set

    def _invalidate_keys_cache(self) -> None:
        """Clear JWKS cache on unknown kid or key rotation."""
        with self._lock:
            self._keys_cache = None
            self._key_set = None

    def validate_jwt(self, token: str, key_set: jwk.KeySet) -> Claims:
        """Validate JWT with given KeySet and return claims.

        Args:
            token: Raw JWT string.
            key_set: KeySet from fetch_keys().

        Returns:
            Decoded claims dict.

        Raises:
            JoseError: If signature is invalid or token malformed.
        """
        return validate_jwt(token, key_set)

    async def validate_token(self, token: str) -> Claims:
        """Validate JWT using cached keys; refetch on failure (key rotation).

        Fetches keys if not cached, validates token. On JoseError
        (e.g. unknown kid), invalidates cache, refetches keys and retries once.

        Args:
            token: Raw JWT string.

        Returns:
            Decoded claims dict.

        Raises:
            JoseError: If validation fails after refetch (e.g. BadSignatureError).
            httpx.HTTPError: On network errors during fetch.
        """
        key_set = await self.fetch_keys(self._jwks_uri)

        try:
            return self.validate_jwt(token, key_set)
        except JoseError:
            self._invalidate_keys_cache()
            key_set = await self.fetch_keys(self._jwks_uri)
            return self.validate_jwt(token, key_set)
