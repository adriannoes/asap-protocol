"""OAuth2 client for ASAP Protocol.

Provides token acquisition and refresh using:
- client_credentials: Machine-to-machine authentication (agent-to-agent)
- authorization_code: Human-in-the-loop scenarios (placeholder for v1.1.1+)

Uses Authlib's AsyncOAuth2Client internally (ADR-12).
"""

import time
from typing import Any, Optional

import httpx
from authlib.integrations.httpx_client import AsyncOAuth2Client
from pydantic import Field

from asap.models.base import ASAPBaseModel
from asap.observability import get_logger

logger = get_logger(__name__)

TOKEN_REFRESH_BUFFER_SECONDS = 30
DEFAULT_TOKEN_LIFETIME_SECONDS = 3600


class Token(ASAPBaseModel):
    """OAuth2 access token with expiry metadata.

    Represents a token obtained from an OAuth2 token endpoint.

    Attributes:
        access_token: The opaque access token string.
        expires_at: Unix timestamp when the token expires.
        token_type: Token type, typically "Bearer".
    """

    access_token: str = Field(..., description="The opaque access token string")
    expires_at: int = Field(..., description="Unix timestamp when the token expires")
    token_type: str = Field(default="Bearer", description="Token type for Authorization header")

    def is_expired(self, buffer_seconds: float = 0) -> bool:
        """Check if the token is expired or within buffer of expiry.

        Args:
            buffer_seconds: Seconds before actual expiry to consider token expired.

        Returns:
            True if token is expired or within buffer, False otherwise.
        """
        return time.time() >= (self.expires_at - buffer_seconds)


def _parse_token_response(raw_token: dict[str, Any]) -> Token:
    """Convert Authlib's raw token dict into an ASAP Token model.

    Args:
        raw_token: Dict returned by Authlib's fetch_token().

    Returns:
        Token with access_token, expires_at, and token_type.
    """
    access_token: str = raw_token["access_token"]
    token_type: str = raw_token.get("token_type", "Bearer")

    if "expires_at" in raw_token:
        expires_at = int(raw_token["expires_at"])
    elif "expires_in" in raw_token:
        expires_at = int(time.time()) + int(raw_token["expires_in"])
    else:
        expires_at = int(time.time()) + DEFAULT_TOKEN_LIFETIME_SECONDS

    return Token(
        access_token=access_token,
        expires_at=expires_at,
        token_type=token_type,
    )


class OAuth2ClientCredentials:
    """OAuth2 client for client_credentials grant.

    Obtains access tokens from any standard OAuth2 token endpoint
    using the client_credentials flow (machine-to-machine auth).

    Internally uses Authlib's AsyncOAuth2Client (see ADR-12).

    Example:
        >>> client = OAuth2ClientCredentials(
        ...     client_id="my-client",
        ...     client_secret="secret",
        ...     token_url="https://auth.example.com/oauth/token",
        ... )
        >>> token = await client.get_access_token()
        >>> headers = {"Authorization": f"{token.token_type} {token.access_token}"}
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        *,
        scope: Optional[str] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        """Initialize the OAuth2 client credentials client.

        Args:
            client_id: OAuth2 client ID from the provider.
            client_secret: OAuth2 client secret from the provider.
            token_url: URL of the OAuth2 token endpoint.
            scope: Optional space-separated scopes to request.
            transport: Optional httpx transport for testing (e.g. MockTransport).
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._scope = scope
        self._transport = transport
        self._cached_token: Optional[Token] = None

    async def get_valid_token(self, scope: Optional[str] = None) -> Token:
        """Return a valid token, using cache if not expired or refreshing if near expiry.

        Reuses the cached token when it is still valid. Refreshes 30 seconds
        before actual expiry to prevent race conditions (see TOKEN_REFRESH_BUFFER_SECONDS).

        Args:
            scope: Optional scopes to request (overrides constructor scope).

        Returns:
            Token that is valid for at least TOKEN_REFRESH_BUFFER_SECONDS.

        Raises:
            httpx.HTTPStatusError: Token endpoint returned an error status.
            httpx.HTTPError: Network or transport error.
        """
        if self._cached_token is not None and not self._cached_token.is_expired(
            buffer_seconds=TOKEN_REFRESH_BUFFER_SECONDS
        ):
            return self._cached_token
        token = await self.get_access_token(scope=scope)
        self._cached_token = token
        return token

    async def get_access_token(self, scope: Optional[str] = None) -> Token:
        """Obtain a new access token from the token endpoint.

        Args:
            scope: Optional scopes to request (overrides constructor scope).

        Returns:
            Token with access_token, expires_at, and token_type.

        Raises:
            httpx.HTTPStatusError: Token endpoint returned an error status.
            httpx.HTTPError: Network or transport error.
        """
        requested_scope = scope or self._scope

        kwargs: dict[str, Any] = {"timeout": httpx.Timeout(10.0)}
        if self._transport is not None:
            kwargs["transport"] = self._transport

        async with AsyncOAuth2Client(
            client_id=self._client_id,
            client_secret=self._client_secret,
            scope=requested_scope,
            **kwargs,
        ) as client:
            raw_token: dict[str, Any] = await client.fetch_token(
                url=self._token_url,
                grant_type="client_credentials",
            )

        token = _parse_token_response(raw_token)
        expires_in = token.expires_at - int(time.time())
        logger.info(
            "asap.oauth2.token_acquired",
            token_endpoint=self._token_url,
            expires_in=expires_in,
        )
        return token
