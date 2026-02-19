"""Authentication and rate limiting middleware for ASAP protocol server.

This module provides middleware that:
- Validates Bearer tokens based on manifest configuration
- Verifies sender identity matches authenticated agent
- Supports custom token validation logic
- Returns proper JSON-RPC error responses for auth failures
- Implements IP-based rate limiting to prevent DoS attacks

**Rate limit storage:** The default limiter uses in-memory storage (``memory://``).
The configured limit is per-process; with multiple workers (e.g. Gunicorn), the
effective limit is approximately limit × number of workers. Use Redis for
shared limits in production (planned for v1.2.0).

Example:
    >>> from asap.transport.middleware import AuthenticationMiddleware, BearerTokenValidator
    >>> from asap.models.entities import Manifest, AuthScheme
    >>>
    >>> # Create manifest with auth configuration
    >>> manifest = Manifest(
    ...     id="urn:asap:agent:secure-agent",
    ...     name="Secure Agent",
    ...     version="1.0.0",
    ...     description="Agent with authentication",
    ...     auth=AuthScheme(schemes=["bearer"]),
    ...     # ... other fields
    >>> )
    >>>
    >>> # Create custom token validator
    >>> def validate_token(token: str) -> str | None:
    ...     # Validate token and return agent_id if valid
    ...     if token == "valid-token-123":
    ...         return "urn:asap:agent:authorized-client"
    ...     return None
    >>>
    >>> validator = BearerTokenValidator(validate_token)
    >>> middleware = AuthenticationMiddleware(manifest, validator)
"""
from __future__ import annotations

import asyncio
import inspect
from typing import Any, Awaitable, Callable, Optional, Protocol, cast

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from asap.models.entities import Manifest
from asap.observability import get_logger
from asap.transport.rate_limit import (
    DEFAULT_RATE_LIMIT,
    ASAPRateLimiter,
    RateLimitExceeded,
    create_limiter,
    create_test_limiter,
    get_remote_address,
)
from asap.utils.sanitization import sanitize_token

logger = get_logger(__name__)

# Authentication header scheme
AUTH_SCHEME_BEARER = "bearer"


def _get_sender_from_envelope(request: Request) -> str:
    """Extract identifier from request for rate limiting.

    This function implements IP-based rate limiting for the transport layer.
    The rate limiter executes before the route handler parses the request body,
    so the ASAP envelope is not yet available at rate limit check time.
    Therefore, this function primarily returns the client IP address.

    The function attempts to extract the sender from the envelope if already
    parsed (for future compatibility), but in practice always falls back to
    the client IP address. This IP-based approach is safer for DoS prevention
    as it doesn't require parsing the request body before rate limiting.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address (used as rate limiting key)

    Example:
        >>> sender = _get_sender_from_envelope(request)
        >>> # Returns "192.168.1.1" (IP address, not sender URN)
    """
    try:
        if hasattr(request.state, "envelope") and request.state.envelope:
            envelope = request.state.envelope
            if hasattr(envelope, "sender") and isinstance(envelope.sender, str):
                return envelope.sender

        # Try to extract from JSON-RPC request if already parsed
        if hasattr(request.state, "rpc_request"):
            rpc_request = request.state.rpc_request
            if (
                hasattr(rpc_request, "params")
                and isinstance(rpc_request.params, dict)
                and "envelope" in rpc_request.params
            ):
                envelope_data = rpc_request.params.get("envelope")
                if isinstance(envelope_data, dict) and "sender" in envelope_data:
                    sender = envelope_data["sender"]
                    if isinstance(sender, str):
                        return sender
    except (AttributeError, KeyError, TypeError):
        # Envelope not available, fall back to IP
        pass

    remote_addr = get_remote_address(request)
    if isinstance(remote_addr, str):
        return remote_addr
    return str(remote_addr)


_limiter: ASAPRateLimiter | None = None


def _get_default_limiter() -> ASAPRateLimiter:
    global _limiter  # noqa: PLW0603
    if _limiter is None:
        _limiter = create_limiter(key_func=_get_sender_from_envelope)
    return _limiter


# Backward-compatible alias used by middleware and test fixtures.
# Tests and create_app() override this via monkeypatch or app.state.limiter.
limiter: ASAPRateLimiter | None = None


def rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle rate limit exceeded exceptions with JSON-RPC formatted error.

    Returns a JSON-RPC 2.0 compliant error response with HTTP 429 status
    and Retry-After header indicating when the client can retry.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception (typed as Exception for FastAPI compatibility)

    Returns:
        JSONResponse with JSON-RPC error format and 429 status code

    Example:
        >>> response = rate_limit_handler(request, exc)
        >>> # Returns JSONResponse with status_code=429 and JSON-RPC error
    """
    if not isinstance(exc, RateLimitExceeded):
        # Fallback for unexpected exception types
        logger.warning("asap.rate_limit.unexpected_exception", exc_type=type(exc).__name__)
        return JSONResponse(
            status_code=HTTP_TOO_MANY_REQUESTS,
            content={
                "jsonrpc": "2.0",
                "id": getattr(request.state, "request_id", None),
                "error": {
                    "code": HTTP_TOO_MANY_REQUESTS,
                    "message": ERROR_RATE_LIMIT_EXCEEDED,
                },
            },
        )

    # Calculate retry_after — handle non-integer values gracefully.
    retry_after = 60
    if exc.retry_after is not None:
        try:
            retry_after = int(exc.retry_after)
        except (ValueError, TypeError):
            retry_after = 60

    limit_str = exc.limit if exc.limit else DEFAULT_RATE_LIMIT

    logger.warning(
        "asap.rate_limit.exceeded",
        sender=_get_sender_from_envelope(request),
        retry_after=retry_after,
        limit=limit_str,
    )

    # Return JSON-RPC 2.0 formatted error response
    return JSONResponse(
        status_code=HTTP_TOO_MANY_REQUESTS,
        content={
            "jsonrpc": "2.0",
            "id": getattr(request.state, "request_id", None),
            "error": {
                "code": HTTP_TOO_MANY_REQUESTS,
                "message": ERROR_RATE_LIMIT_EXCEEDED,
                "data": {
                    "retry_after": retry_after,
                    "limit": limit_str,
                },
            },
        },
        headers={"Retry-After": str(retry_after)},
    )


# HTTP status codes
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_TOO_MANY_REQUESTS = 429

# Error messages
ERROR_AUTH_REQUIRED = "Authentication required"
# nosec B105: This is an error message constant, not a hardcoded password
ERROR_INVALID_TOKEN = "Invalid authentication token"  # nosec B105
ERROR_SENDER_MISMATCH = "Sender does not match authenticated identity"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"


class TokenValidator(Protocol):
    """Protocol for token validation implementations.

    Custom validators must implement this interface to integrate
    with the authentication middleware. Validators may be sync or async.
    Sync validators that perform I/O (e.g., DB/Redis lookups) are run
    in a thread pool to avoid blocking the event loop.

    Example (sync):
        >>> class MySyncValidator:
        ...     def __call__(self, token: str) -> str | None:
        ...         if is_valid(token):
        ...             return extract_agent_id(token)
        ...         return None

    Example (async):
        >>> class MyAsyncValidator:
        ...     async def __call__(self, token: str) -> str | None:
        ...         return await db.lookup_agent(token)
    """

    def __call__(self, token: str) -> str | None | Awaitable[str | None]:
        """Validate a token and return the authenticated agent ID.

        Args:
            token: The authentication token to validate

        Returns:
            The agent ID (URN) if token is valid, None otherwise.
            May return a coroutine for async validators.

        Example:
            >>> validator = BearerTokenValidator(my_validate_func)
            >>> agent_id = validator("token-123")
            >>> print(agent_id)  # "urn:asap:agent:client-1" or None
        """
        ...


class BearerTokenValidator:
    """Default Bearer token validator implementation.

    Wraps a validation function to conform to the TokenValidator protocol.
    The validation function may be sync or async. Sync validators that perform
    I/O are run in a thread pool by the middleware to avoid blocking the loop.

    Attributes:
        validate_func: Function that validates tokens and returns agent IDs

    Example:
        >>> def my_validator(token: str) -> str | None:
        ...     if token in valid_tokens:
        ...         return valid_tokens[token]["agent_id"]
        ...     return None
        >>>
        >>> validator = BearerTokenValidator(my_validator)
        >>> agent_id = validator("abc123")
    """

    def __init__(
        self,
        validate_func: Callable[[str], str | None | Awaitable[str | None]],
    ) -> None:
        self.validate_func = validate_func

    def __call__(self, token: str) -> str | None | Awaitable[str | None]:
        return self.validate_func(token)


class AuthenticationMiddleware:
    """FastAPI middleware for ASAP protocol authentication.

    This middleware handles authentication based on the manifest configuration:
    - If manifest has no auth config, authentication is skipped
    - If auth is configured, validates Bearer tokens
    - Verifies sender in envelope matches authenticated identity
    - Returns proper JSON-RPC error responses for failures

    Attributes:
        manifest: The agent manifest with auth configuration
        validator: Token validator implementation
        security: HTTPBearer security scheme from FastAPI

    Example:
        >>> from asap.transport.middleware import AuthenticationMiddleware
        >>> from asap.models.entities import Manifest, AuthScheme
        >>>
        >>> manifest = Manifest(
        ...     id="urn:asap:agent:my-agent",
        ...     auth=AuthScheme(schemes=["bearer"]),
        ...     # ... other fields
        ... )
        >>>
        >>> def validate_token(token: str) -> str | None:
        ...     # Your validation logic
        ...     return "urn:asap:agent:client" if valid else None
        >>>
        >>> validator = BearerTokenValidator(validate_token)
        >>> middleware = AuthenticationMiddleware(manifest, validator)
    """

    def __init__(
        self,
        manifest: Manifest,
        validator: TokenValidator | None = None,
    ) -> None:
        self.manifest = manifest
        self.validator = validator
        self.security = HTTPBearer(auto_error=False)

        if self._is_auth_required() and validator is None:
            raise ValueError(
                "Token validator required when authentication is configured in manifest"
            )

    def _is_auth_required(self) -> bool:
        return self.manifest.auth is not None

    def _supports_bearer_auth(self) -> bool:
        if not self.manifest.auth:
            return False
        return AUTH_SCHEME_BEARER in self.manifest.auth.schemes

    async def verify_authentication(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = None,
    ) -> str | None:
        """Verify authentication for an incoming request.

        This method:
        1. Checks if authentication is required
        2. Extracts credentials from Authorization header
        3. Validates token using the configured validator
        4. Returns authenticated agent ID or raises HTTPException

        Args:
            request: The incoming FastAPI request
            credentials: Optional pre-extracted credentials

        Returns:
            The authenticated agent ID (URN) if auth is required and valid,
            None if auth is not required

        Raises:
            HTTPException: If authentication is required but fails (401 or 403)

        Example:
            >>> middleware = AuthenticationMiddleware(manifest, validator)
            >>> agent_id = await middleware.verify_authentication(request)
            >>> # agent_id is None if auth not required
            >>> # agent_id is agent URN if auth successful
            >>> # HTTPException raised if auth failed
        """
        # Skip authentication if not required
        if not self._is_auth_required():
            logger.debug("asap.auth.skipped", reason="not_required_by_manifest")
            return None

        # Extract credentials if not provided
        if credentials is None:
            credentials = await self.security(request)

        # Require credentials if auth is configured
        if credentials is None:
            logger.warning("asap.auth.missing", manifest_id=self.manifest.id)
            raise HTTPException(
                status_code=HTTP_UNAUTHORIZED,
                detail=ERROR_AUTH_REQUIRED,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if credentials.scheme.lower() != AUTH_SCHEME_BEARER:
            logger.warning(
                "asap.auth.invalid_scheme",
                manifest_id=self.manifest.id,
                provided_scheme=credentials.scheme,
                expected_scheme=AUTH_SCHEME_BEARER,
            )
            raise HTTPException(
                status_code=HTTP_UNAUTHORIZED,
                detail=ERROR_INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not self._supports_bearer_auth():
            logger.warning(
                "asap.auth.scheme_not_supported",
                manifest_id=self.manifest.id,
                provided_scheme=credentials.scheme,
            )
            raise HTTPException(
                status_code=HTTP_UNAUTHORIZED,
                detail=ERROR_INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = credentials.credentials
        if self.validator is None:
            raise RuntimeError(
                "Token validator is None but authentication is required. "
                "This should not happen if middleware was initialized correctly."
            )
        if inspect.iscoroutinefunction(self.validator.__call__):
            result = self.validator(token)
            agent_id = await cast(Awaitable[Optional[str]], result)
        else:
            # Cast: to_thread expects Callable[..., T]; TokenValidator may return Awaitable
            # but we handle that below (BearerTokenValidator wrapping async func)
            agent_id = await asyncio.to_thread(
                cast("Callable[[str], Optional[str]]", self.validator), token
            )
            if inspect.isawaitable(agent_id):
                agent_id = await cast(Awaitable[Optional[str]], agent_id)

        if agent_id is None:
            # Log sanitized token to avoid exposing full token data
            token_prefix = sanitize_token(token)
            logger.warning(
                "asap.auth.invalid_token",
                manifest_id=self.manifest.id,
                token_prefix=token_prefix,
            )
            raise HTTPException(
                status_code=HTTP_UNAUTHORIZED,
                detail=ERROR_INVALID_TOKEN,
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.info(
            "asap.auth.success",
            manifest_id=self.manifest.id,
            authenticated_agent=agent_id,
        )
        return agent_id

    def verify_sender_matches_auth(
        self,
        authenticated_agent_id: str | None,
        envelope_sender: str,
    ) -> None:
        """Verify that envelope sender matches authenticated identity.

        This prevents agents from spoofing the sender field in the envelope.
        Only enforced when authentication is enabled.

        Args:
            authenticated_agent_id: The agent ID from authentication, or None
            envelope_sender: The sender field from the envelope

        Raises:
            HTTPException: If sender doesn't match authenticated identity (403)

        Example:
            >>> middleware.verify_sender_matches_auth(
            ...     authenticated_agent_id="urn:asap:agent:client-1",
            ...     envelope_sender="urn:asap:agent:client-1"
            ... )  # OK
            >>>
            >>> middleware.verify_sender_matches_auth(
            ...     authenticated_agent_id="urn:asap:agent:client-1",
            ...     envelope_sender="urn:asap:agent:spoofed"
            ... )  # Raises HTTPException
        """
        # Skip verification if auth is not enabled
        if authenticated_agent_id is None:
            return

        # Verify sender matches authenticated identity
        if envelope_sender != authenticated_agent_id:
            logger.warning(
                "asap.auth.sender_mismatch",
                authenticated_agent=authenticated_agent_id,
                envelope_sender=envelope_sender,
            )
            raise HTTPException(
                status_code=HTTP_FORBIDDEN,
                detail=ERROR_SENDER_MISMATCH,
            )

        logger.debug(
            "asap.auth.sender_verified",
            authenticated_agent=authenticated_agent_id,
        )


class SizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to validate request size before routing.

    This middleware checks the Content-Length header and rejects requests
    that exceed the maximum allowed size before any routing logic executes.
    This provides early rejection and prevents unnecessary processing.

    The middleware validates the Content-Length header only. Actual body
    size validation during parsing (with streaming) is handled in the
    route handler to prevent OOM attacks.

    Attributes:
        max_size: Maximum allowed request size in bytes

    Example:
        >>> from asap.transport.middleware import SizeLimitMiddleware
        >>> app.add_middleware(SizeLimitMiddleware, max_size=10 * 1024 * 1024)
    """

    def __init__(self, app: Any, max_size: int) -> None:
        """Initialize size limit middleware.

        Args:
            app: The ASGI application
            max_size: Maximum allowed request size in bytes

        Raises:
            ValueError: If max_size is less than 1
        """
        if max_size < 1:
            raise ValueError(f"max_size must be >= 1, got {max_size}")
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Any]]
    ) -> Any:
        """Process request and validate size before routing.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response from next handler or error response if size exceeded
        """
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    logger.warning(
                        "asap.request.size_exceeded",
                        content_length=size,
                        max_size=self.max_size,
                    )
                    # Return JSON response directly (middleware runs before route handlers)
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request size ({size} bytes) exceeds maximum ({self.max_size} bytes)"
                        },
                    )
            except ValueError:
                logger.debug(
                    "asap.middleware.invalid_content_length", content_length=content_length
                )

        # Continue to next middleware or route handler
        return await call_next(request)


# Export rate limiting components
__all__ = [
    "AuthenticationMiddleware",
    "BearerTokenValidator",
    "TokenValidator",
    "SizeLimitMiddleware",
    "ASAPRateLimiter",
    "RateLimitExceeded",
    "limiter",
    "rate_limit_handler",
    "create_limiter",
    "create_test_limiter",
    "get_remote_address",
    "_get_sender_from_envelope",
]
