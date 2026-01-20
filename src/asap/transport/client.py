"""Async HTTP client for ASAP protocol communication.

This module provides an async HTTP client for sending ASAP messages
between agents using JSON-RPC 2.0 over HTTP.

The ASAPClient provides:
- Async context manager for connection lifecycle
- send() method for envelope exchange
- Automatic JSON-RPC wrapping
- Retry logic with idempotency keys
- Proper error handling and timeouts

Example:
    >>> from asap.transport.client import ASAPClient
    >>> from asap.models.envelope import Envelope
    >>>
    >>> async with ASAPClient("http://agent.example.com") as client:
    ...     response = await client.send(request_envelope)
    ...     print(response.payload_type)
"""

from typing import Any

import httpx

from asap.models.envelope import Envelope
from asap.models.ids import generate_id

# Default timeout in seconds
DEFAULT_TIMEOUT = 60.0

# Default maximum retries
DEFAULT_MAX_RETRIES = 3


class ASAPConnectionError(Exception):
    """Raised when connection to remote agent fails.

    This error occurs when the HTTP connection cannot be established
    or when the remote server returns an HTTP error status.

    Attributes:
        message: Error description
        cause: Original exception that caused this error
    """

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize connection error.

        Args:
            message: Error description
            cause: Original exception that caused this error
        """
        super().__init__(message)
        self.message = message
        self.cause = cause


class ASAPTimeoutError(Exception):
    """Raised when request to remote agent times out.

    This error occurs when the HTTP request exceeds the configured
    timeout duration.

    Attributes:
        message: Error description
        timeout: Timeout value in seconds
    """

    def __init__(self, message: str, timeout: float | None = None) -> None:
        """Initialize timeout error.

        Args:
            message: Error description
            timeout: Timeout value in seconds
        """
        super().__init__(message)
        self.message = message
        self.timeout = timeout


class ASAPRemoteError(Exception):
    """Raised when remote agent returns an error response.

    This error occurs when the JSON-RPC response contains an error
    object, indicating the remote agent could not process the request.

    Attributes:
        code: JSON-RPC error code
        message: Error message from remote
        data: Optional additional error data
    """

    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None) -> None:
        """Initialize remote error.

        Args:
            code: JSON-RPC error code
            message: Error message from remote
            data: Optional additional error data
        """
        super().__init__(f"Remote error {code}: {message}")
        self.code = code
        self.message = message
        self.data = data or {}


class ASAPClient:
    """Async HTTP client for ASAP protocol communication.

    ASAPClient manages HTTP connections to remote ASAP agents and provides
    methods for sending envelopes and receiving responses.

    The client should be used as an async context manager to ensure
    proper connection lifecycle management.

    Attributes:
        base_url: Base URL of the remote agent
        timeout: Request timeout in seconds
        max_retries: Maximum retry attempts for transient failures
        is_connected: Whether the client has an active connection

    Example:
        >>> async with ASAPClient("http://localhost:8000") as client:
        ...     response = await client.send(envelope)
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
    ) -> None:
        """Initialize ASAP client.

        Args:
            base_url: Base URL of the remote agent (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts for transient failures (default: 3)
            transport: Optional custom transport (for testing). Can be sync or async.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._request_counter = 0

    @property
    def is_connected(self) -> bool:
        """Check if client has an active connection."""
        return self._client is not None

    async def __aenter__(self) -> "ASAPClient":
        """Enter async context and open connection."""
        # Create the async client
        if self._transport:
            # MockTransport works for both sync and async, so we cast it
            # This is safe because httpx.MockTransport is compatible with async usage
            self._client = httpx.AsyncClient(
                transport=self._transport,  # type: ignore[arg-type]
                timeout=self.timeout,
            )
        else:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit async context and close connection."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def send(self, envelope: Envelope) -> Envelope:
        """Send an envelope to the remote agent and receive response.

        Wraps the envelope in a JSON-RPC 2.0 request, sends it to the
        remote agent's /asap endpoint, and unwraps the response.

        Args:
            envelope: ASAP envelope to send

        Returns:
            Response envelope from the remote agent

        Raises:
            ASAPConnectionError: If connection fails or HTTP error occurs
            ASAPTimeoutError: If request times out
            ASAPRemoteError: If remote agent returns JSON-RPC error
        """
        if not self._client:
            raise ASAPConnectionError("Client not connected. Use 'async with' context.")

        # Generate idempotency key for retries
        idempotency_key = generate_id()

        # Increment request counter for JSON-RPC id
        self._request_counter += 1
        request_id = f"req-{self._request_counter}"

        # Build JSON-RPC request
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": envelope.model_dump(mode="json"),
                "idempotency_key": idempotency_key,
            },
            "id": request_id,
        }

        # Attempt with retries
        last_exception: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.post(
                    f"{self.base_url}/asap",
                    json=json_rpc_request,
                    headers={
                        "Content-Type": "application/json",
                        "X-Idempotency-Key": idempotency_key,
                    },
                )

                # Check HTTP status
                if response.status_code >= 400:
                    raise ASAPConnectionError(f"HTTP error {response.status_code}: {response.text}")

                # Parse JSON response
                try:
                    json_response = response.json()
                except Exception as e:
                    raise ASAPRemoteError(-32700, f"Invalid JSON response: {e}") from e

                # Check for JSON-RPC error
                if "error" in json_response:
                    error = json_response["error"]
                    raise ASAPRemoteError(
                        error.get("code", -32603),
                        error.get("message", "Unknown error"),
                        error.get("data"),
                    )

                # Extract envelope from result
                result = json_response.get("result", {})
                envelope_data = result.get("envelope")
                if not envelope_data:
                    raise ASAPRemoteError(-32603, "Missing envelope in response")

                return Envelope(**envelope_data)

            except httpx.ConnectError as e:
                last_exception = ASAPConnectionError(f"Connection error: {e}", cause=e)
                # Retry on connection errors
                if attempt < self.max_retries - 1:
                    continue
                raise last_exception from e

            except httpx.TimeoutException as e:
                last_exception = ASAPTimeoutError(
                    f"Request timeout after {self.timeout}s", timeout=self.timeout
                )
                # Don't retry on timeout
                raise last_exception from e

            except (ASAPConnectionError, ASAPRemoteError, ASAPTimeoutError):
                # Re-raise our custom errors
                raise

            except Exception as e:
                # Wrap unexpected errors
                raise ASAPConnectionError(f"Unexpected error: {e}", cause=e) from e

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise ASAPConnectionError("Max retries exceeded")
