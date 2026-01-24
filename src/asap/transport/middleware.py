"""Authentication middleware for ASAP protocol server.

This module provides authentication middleware that:
- Validates Bearer tokens based on manifest configuration
- Verifies sender identity matches authenticated agent
- Supports custom token validation logic
- Returns proper JSON-RPC error responses for auth failures

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
from typing import Callable, Protocol

from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from asap.models.entities import Manifest
from asap.observability import get_logger

logger = get_logger(__name__)

# Authentication header scheme
AUTH_SCHEME_BEARER = "bearer"

# HTTP status codes
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403

# Error messages
ERROR_AUTH_REQUIRED = "Authentication required"
ERROR_INVALID_TOKEN = "Invalid authentication token"
ERROR_SENDER_MISMATCH = "Sender does not match authenticated identity"


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
