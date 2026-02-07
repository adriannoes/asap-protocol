"""OAuth2 token validation middleware for ASAP Protocol.

Validates JWT Bearer tokens using JWKS (via joserfc), extracts claims
(sub, scope, exp), and returns 401 when invalid or 403 when scope is insufficient.
Supports Custom Claims identity binding (ADR-17).
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from joserfc import jwt as jose_jwt
from joserfc import jwk
from joserfc.errors import JoseError
from starlette.middleware.base import BaseHTTPMiddleware

from asap.auth.utils import parse_scope
from asap.observability import get_logger

logger = get_logger(__name__)

HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
ERROR_AUTH_REQUIRED = "Authentication required"
ERROR_INVALID_TOKEN = "Invalid authentication token"
ERROR_INSUFFICIENT_SCOPE = "Insufficient scope"
ERROR_IDENTITY_MISMATCH = "Identity mismatch: custom claim does not match agent manifest"

DEFAULT_CUSTOM_CLAIM = "https://github.com/adriannoes/asap-protocol/agent_id"
ENV_SUBJECT_MAP = "ASAP_AUTH_SUBJECT_MAP"


def _parse_subject_map() -> dict[str, str | list[str]]:
    """Parse ASAP_AUTH_SUBJECT_MAP env var (JSON dict: agent_id -> sub or list of subs).

    Returns empty dict on parse error or when env is unset.
    """
    raw = os.environ.get(ENV_SUBJECT_MAP)
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items() if isinstance(v, (str, list))}


@dataclass
class OAuth2Config:
    """Configuration for OAuth2 JWT validation on ASAP server routes.

    When passed to create_app(oauth2_config=...), OAuth2Middleware is applied
    to all requests under path_prefix (default /asap), validating Bearer JWTs
    using the provider's JWKS endpoint. Supports Custom Claims identity binding
    (ADR-17) when manifest_id is provided.

    Attributes:
        jwks_uri: URL of the JWKS endpoint (e.g. from OIDC discovery).
        required_scope: Optional scope that tokens must contain (e.g. "asap:execute").
        path_prefix: Path prefix to protect; default "/asap".
        jwks_fetcher: Optional async (uri) -> KeySet for tests; default fetches via httpx.
        manifest_id: Optional agent manifest id for identity binding; when set,
            validates custom claim or allowlist fallback. If None, identity binding
            is disabled.
        custom_claim: Optional JWT claim key for agent_id; when None, uses
            ASAP_AUTH_CUSTOM_CLAIM env var (default: DEFAULT_CUSTOM_CLAIM).
    """

    jwks_uri: str
    required_scope: str | None = None
    path_prefix: str = "/asap"
    jwks_fetcher: Callable[[str], Awaitable[jwk.KeySet]] | None = None
    manifest_id: str | None = None
    custom_claim: str | None = None


@dataclass
class OAuth2Claims:
    """Claims extracted from a validated JWT.

    Attributes:
        sub: Subject (e.g. agent URN or user id).
        scope: List of scope strings (e.g. ["asap:execute", "asap:read"]).
        exp: Expiration timestamp (Unix).
    """

    sub: str
    scope: list[str]
    exp: int


def _get_bearer_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None


DEFAULT_HTTP_TIMEOUT = 10.0


async def _fetch_jwks(
    jwks_uri: str, transport: httpx.AsyncBaseTransport | None = None
) -> jwk.KeySet:
    """Fetch JWKS from URI and return a joserfc KeySet."""
    async with httpx.AsyncClient(
        transport=transport, timeout=httpx.Timeout(DEFAULT_HTTP_TIMEOUT)
    ) as client:
        resp = await client.get(jwks_uri)
        resp.raise_for_status()
        data = resp.json()
    return jwk.KeySet.import_key_set(data)


class OAuth2Middleware(BaseHTTPMiddleware):
    """Middleware that validates JWT Bearer tokens using JWKS.

    Extracts Authorization: Bearer <token>, validates the JWT signature
    with keys from jwks_uri, checks exp, and optionally enforces a
    required scope. Sets request.state.oauth2_claims on success.

    Returns 401 if the token is missing or invalid, 403 if scope is insufficient.
    """

    def __init__(
        self,
        app: Any,
        jwks_uri: str,
        *,
        required_scope: str | None = None,
        path_prefix: str | None = "/asap",
        jwks_fetcher: Callable[[str], Awaitable[jwk.KeySet]] | None = None,
        manifest_id: str | None = None,
        custom_claim: str | None = None,
    ) -> None:
        """Initialize OAuth2 middleware.

        Args:
            app: ASGI application.
            jwks_uri: URL of the JWKS endpoint (e.g. from OIDC discovery).
            required_scope: If set, token must contain this scope or 403 is returned.
            path_prefix: If set, only requests under this path are validated; others pass through.
            jwks_fetcher: Optional async (uri) -> KeySet for tests; default fetches via httpx.
            manifest_id: Optional agent manifest id for identity binding (ADR-17). If set,
                validates custom claim or allowlist fallback.
            custom_claim: Optional JWT claim key for agent_id; when None, uses
                ASAP_AUTH_CUSTOM_CLAIM env var.
        """
        super().__init__(app)
        self._jwks_uri = jwks_uri
        self._required_scope = required_scope
        self._path_prefix = path_prefix
        self._jwks_fetcher = jwks_fetcher or _fetch_jwks
        self._manifest_id = manifest_id
        self._custom_claim = custom_claim
        self._custom_claim_key = self._custom_claim or os.environ.get(
            "ASAP_AUTH_CUSTOM_CLAIM", DEFAULT_CUSTOM_CLAIM
        )
        self._subject_map = _parse_subject_map()
        self._jwks_cache: jwk.KeySet | None = None
        self._jwks_cache_time: float = 0.0
        self._jwks_cache_ttl = 3600.0  # 1 hour
        self._jwks_lock = asyncio.Lock()

    def _should_validate(self, path: str) -> bool:
        """Return True if this request path should be validated."""
        if self._path_prefix is None:
            return True
        return path.startswith(self._path_prefix)

    async def _get_key_set(self) -> jwk.KeySet:
        """Return JWKS, from cache or by fetching."""
        async with self._jwks_lock:
            now = time.time()
            if (
                self._jwks_cache is not None
                and (now - self._jwks_cache_time) < self._jwks_cache_ttl
            ):
                return self._jwks_cache
            key_set = await self._jwks_fetcher(self._jwks_uri)
            self._jwks_cache = key_set
            self._jwks_cache_time = now
            return key_set

    async def _invalidate_jwks_cache(self) -> None:
        """Clear JWKS cache."""
        async with self._jwks_lock:
            self._jwks_cache = None
            self._jwks_cache_time = 0.0

    def _validate_scope(self, scope_list: list[str]) -> bool:
        """Check if required_scope is present in scope list."""
        if self._required_scope is None:
            return True
        return self._required_scope in scope_list

    def _validate_identity_binding(
        self, claims: dict[str, Any], sub: str
    ) -> tuple[bool, str | None, bool, bool]:
        """Validate JWT identity binding via custom claim or allowlist (ADR-17)."""
        if self._manifest_id is None:
            return True, None, False, False

        claim_key = self._custom_claim_key
        claim_value = claims.get(claim_key)

        if claim_value is not None:
            agent_id = str(claim_value).strip()
            if agent_id != self._manifest_id:
                return (
                    False,
                    f"Custom claim {claim_key!r} has {agent_id!r}, expected {self._manifest_id!r}",
                    False,
                    False,
                )
            return True, None, False, False

        allowed = self._subject_map.get(self._manifest_id)
        if allowed is not None:
            if isinstance(allowed, str) and allowed == sub:
                return True, None, False, True
            if isinstance(allowed, list) and sub in allowed:
                return True, None, False, True

        return True, None, True, False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Validate JWT and optionally scope; return 401/403 or pass to next."""
        if not self._should_validate(request.url.path):
            return await call_next(request)

        token = _get_bearer_token(request)
        if not token:
            logger.warning("asap.oauth2.missing_token", path=request.url.path)
            return JSONResponse(
                status_code=HTTP_UNAUTHORIZED,
                content={"detail": ERROR_AUTH_REQUIRED},
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            key_set = await self._get_key_set()
            token_obj = jose_jwt.decode(token, key_set)
        except httpx.HTTPError as e:
            logger.error(
                "asap.oauth2.jwks_fetch_failed",
                path=request.url.path,
                jwks_uri=self._jwks_uri,
                error=str(e),
            )
            return JSONResponse(
                status_code=503,
                content={"detail": "Authentication service unavailable"},
            )
        except JoseError:
            await self._invalidate_jwks_cache()
            try:
                key_set = await self._get_key_set()
                token_obj = jose_jwt.decode(token, key_set)
            except httpx.HTTPError as e2:
                logger.error(
                    "asap.oauth2.jwks_fetch_failed",
                    path=request.url.path,
                    jwks_uri=self._jwks_uri,
                    error=str(e2),
                )
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Authentication service unavailable"},
                )
            except JoseError as e2:
                logger.warning("asap.oauth2.invalid_token", path=request.url.path, error=str(e2))
                return JSONResponse(
                    status_code=HTTP_UNAUTHORIZED,
                    content={"detail": ERROR_INVALID_TOKEN},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        claims = token_obj.claims
        exp = claims.get("exp")
        try:
            exp_ts = int(exp) if isinstance(exp, (int, float)) else 0
        except (TypeError, ValueError):
            exp_ts = 0
        if exp is not None and exp_ts > 0 and exp_ts < time.time():
            logger.warning("asap.oauth2.expired_token", path=request.url.path)
            return JSONResponse(
                status_code=HTTP_UNAUTHORIZED,
                content={"detail": ERROR_INVALID_TOKEN},
                headers={"WWW-Authenticate": "Bearer"},
            )

        sub = claims.get("sub")
        if not sub or not isinstance(sub, str):
            logger.warning("asap.oauth2.missing_sub", path=request.url.path)
            return JSONResponse(
                status_code=HTTP_UNAUTHORIZED,
                content={"detail": ERROR_INVALID_TOKEN},
                headers={"WWW-Authenticate": "Bearer"},
            )

        scope_list = parse_scope(claims.get("scope"))
        if not self._validate_scope(scope_list):
            logger.warning(
                "asap.oauth2.insufficient_scope",
                path=request.url.path,
                required=self._required_scope,
                has_scopes=scope_list,
            )
            return JSONResponse(
                status_code=HTTP_FORBIDDEN,
                content={"detail": ERROR_INSUFFICIENT_SCOPE},
            )

        success, err_detail, claim_missing, use_allowlist = self._validate_identity_binding(
            claims, sub
        )
        if not success:
            logger.warning(
                "asap.oauth2.identity_mismatch",
                path=request.url.path,
                detail=err_detail,
            )
            detail_msg = (
                f"{ERROR_IDENTITY_MISMATCH} (expected: {self._manifest_id})"
                if self._manifest_id
                else ERROR_IDENTITY_MISMATCH
            )
            return JSONResponse(
                status_code=HTTP_FORBIDDEN,
                content={"detail": detail_msg},
            )
        if use_allowlist:
            logger.warning(
                "asap.oauth2.identity_via_allowlist",
                path=request.url.path,
                manifest_id=self._manifest_id,
                sub=sub,
            )
        elif claim_missing:
            logger.warning(
                "asap.oauth2.identity_unverified",
                path=request.url.path,
                manifest_id=self._manifest_id,
            )

        request.state.oauth2_claims = OAuth2Claims(sub=sub, scope=scope_list, exp=exp_ts)
        return await call_next(request)
