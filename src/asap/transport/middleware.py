"""Authentication and rate limiting middleware for ASAP protocol server.

This module provides middleware that:
- Validates Bearer tokens based on manifest configuration
- Verifies sender identity matches authenticated agent
- Supports custom token validation logic
- Returns proper JSON-RPC error responses for auth failures
- Implements IP-based rate limiting to prevent DoS attacks

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

import hashlib
import uuid
from typing import Any, Awaitable, Callable, Protocol
from collections.abc import Sequence

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from asap.models.entities import Manifest
from asap.observability import get_logger

logger = get_logger(__name__)

# Authentication header scheme
AUTH_SCHEME_BEARER = "bearer"

# Rate limiting default configuration
DEFAULT_RATE_LIMIT = "100/minute"


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
    # Try to extract sender from envelope if already parsed (early returns reduce complexity)
    try:
        # Check if envelope is stored in request state (after parsing)
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

    # Fallback to client IP address
    remote_addr = get_remote_address(request)
    # Type narrowing: get_remote_address returns str, but mypy may see it as Any
    if isinstance(remote_addr, str):
        return remote_addr
    return str(remote_addr)


# Create rate limiter instance with IP-based key function
# Note: The key function attempts to extract sender but always falls back to IP
# because rate limiting executes before request body parsing
limiter = Limiter(
    key_func=_get_sender_from_envelope,
    default_limits=[DEFAULT_RATE_LIMIT],
    storage_uri="memory://",
)


def create_test_limiter(limits: Sequence[str] | None = None) -> Limiter:
    """Create a new limiter instance for testing isolation.

    This allows tests to use isolated rate limiters to avoid interference
    between test cases.

    Args:
        limits: Optional list of rate limit strings. Defaults to high limits for testing.

    Returns:
        New Limiter instance with isolated storage

    Example:
        >>> test_limiter = create_test_limiter(["100000/minute"])
        >>> app.state.limiter = test_limiter
    """
    if limits is None:
        limits = ["100000/minute"]  # Very high limit for testing

    # Use unique storage URI to ensure complete isolation between test instances
    unique_storage_id = str(uuid.uuid4())
    return Limiter(
        key_func=_get_sender_from_envelope,
        default_limits=list(limits),
        storage_uri=f"memory://{unique_storage_id}",  # Each instance gets its own memory storage
    )


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
    # Type narrowing: FastAPI passes RateLimitExceeded but handler signature uses Exception
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

    # Calculate retry_after from exception or use default
    retry_after = 60  # Default to 60 seconds
    if hasattr(exc, "retry_after") and exc.retry_after is not None:
        try:
            retry_after = int(exc.retry_after)
        except (ValueError, TypeError):
            retry_after = 60

    # Get limit information if available
    limit_str = DEFAULT_RATE_LIMIT
    if hasattr(exc, "limit") and exc.limit is not None:
        limit_str = str(exc.limit)

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
ERROR_INVALID_TOKEN = "Invalid authentication token"
ERROR_SENDER_MISMATCH = "Sender does not match authenticated identity"
ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"


class TokenValidator(Protocol):
    """Protocol for token validation implementations.

    Custom validators must implement this interface to integrate
    with the authentication middleware.

    Example:
        >>> class MyTokenValidator:
        ...     def __call__(self, token: str) -> str | None:
        ...         # Validate token against database, JWT, etc.
        ...         if is_valid(token):
        ...             return extract_agent_id(token)
        ...         return None
    """

    def __call__(self, token: str) -> str | None:
        """Validate a token and return the authenticated agent ID.

        Args:
            token: The authentication token to validate

        Returns:
            The agent ID (URN) if token is valid, None otherwise

        Example:
            >>> validator = BearerTokenValidator(my_validate_func)
            >>> agent_id = validator("token-123")
            >>> print(agent_id)  # "urn:asap:agent:client-1" or None
        """
        ...


class BearerTokenValidator:
    """Default Bearer token validator implementation.

    Wraps a validation function to conform to the TokenValidator protocol.
    The validation function should take a token string and return an agent ID
    if valid, or None if invalid.

    Attributes:
        validate_func: Function that validates tokens and returns agent IDs

    Example:
        >>> def my_validator(token: str) -> str | None:
        ...     # Check token in database
        ...     if token in valid_tokens:
        ...         return valid_tokens[token]["agent_id"]
        ...     return None
        >>>
        >>> validator = BearerTokenValidator(my_validator)
        >>> agent_id = validator("abc123")
    """

    def __init__(self, validate_func: Callable[[str], str | None]) -> None:
        """Initialize the Bearer token validator.

        Args:
            validate_func: Function that validates tokens and returns agent IDs
        """
        self.validate_func = validate_func

    def __call__(self, token: str) -> str | None:
        """Validate a token and return the authenticated agent ID.

        Args:
            token: The authentication token to validate

        Returns:
            The agent ID (URN) if token is valid, None otherwise
        """
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
        """Initialize authentication middleware.

        Args:
            manifest: Agent manifest with auth configuration
            validator: Token validator implementation (optional if auth not required)

        Raises:
            ValueError: If manifest requires auth but no validator provided
        """
        self.manifest = manifest
        self.validator = validator
        self.security = HTTPBearer(auto_error=False)

        # Validate configuration
        if self._is_auth_required() and validator is None:
            raise ValueError(
                "Token validator required when authentication is configured in manifest"
            )

    def _is_auth_required(self) -> bool:
        """Check if authentication is required by manifest.

        Returns:
            True if manifest has auth configuration, False otherwise
        """
        return self.manifest.auth is not None

    def _supports_bearer_auth(self) -> bool:
        """Check if manifest supports Bearer token authentication.

        Returns:
            True if "bearer" is in auth schemes, False otherwise
        """
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

        # Validate Authorization scheme (case-insensitive)
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

        # Validate Bearer token support in manifest
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

        # Validate token and get agent ID
        token = credentials.credentials
        # Type narrowing: validator is not None when auth is required (validated in __init__)
        if self.validator is None:
            raise RuntimeError(
                "Token validator is None but authentication is required. "
                "This should not happen if middleware was initialized correctly."
            )
        agent_id = self.validator(token)

        if agent_id is None:
            # Log token hash instead of prefix to avoid exposing token data
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            logger.warning(
                "asap.auth.invalid_token",
                manifest_id=self.manifest.id,
                token_hash=token_hash,
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

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
        """Process request and validate size before routing.

        Args:
            request: FastAPI request object
            call_next: Next middleware or route handler

        Returns:
            Response from next handler or error response if size exceeded
        """
        # Check Content-Length header if present
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
                        content={"detail": f"Request size ({size} bytes) exceeds maximum ({self.max_size} bytes)"},
                    )
            except ValueError:
                # Invalid Content-Length header, let route handler validate actual body size
                pass

        # Continue to next middleware or route handler
        response = await call_next(request)
        return response


# Export rate limiting components
__all__ = [
    "AuthenticationMiddleware",
    "BearerTokenValidator",
    "TokenValidator",
    "SizeLimitMiddleware",
    "limiter",
    "rate_limit_handler",
    "create_test_limiter",
    "_get_sender_from_envelope",
]
