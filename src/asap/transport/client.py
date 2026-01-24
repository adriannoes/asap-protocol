"""Async HTTP client for ASAP protocol communication.

This module provides an async HTTP client for sending ASAP messages
between agents using JSON-RPC 2.0 over HTTP.

The ASAPClient provides:
- Async context manager for connection lifecycle
- send() method for envelope exchange
- Automatic JSON-RPC wrapping
- Retry logic with idempotency keys
- Proper error handling and timeouts
- Structured logging for observability

Example:
    >>> from asap.transport.client import ASAPClient
    >>> from asap.models.envelope import Envelope
    >>>
    >>> async with ASAPClient("http://agent.example.com") as client:
    ...     response = await client.send(request_envelope)
    ...     print(response.payload_type)
"""

import time
from typing import Any

import httpx

from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.observability import get_logger
from asap.transport.jsonrpc import ASAP_METHOD

# Module logger
logger = get_logger(__name__)

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
        # Validate URL format
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                f"Invalid base_url format: {base_url}. Must be a valid URL (e.g., http://localhost:8000)"
            )

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

        Example:
            >>> async with ASAPClient("http://localhost:8000") as client:
            ...     response = await client.send(envelope)
            ...     response.payload_type
        """
        if not self._client:
            raise ASAPConnectionError("Client not connected. Use 'async with' context.")

        start_time = time.perf_counter()

        # Generate idempotency key for retries
        idempotency_key = generate_id()

        # Increment request counter for JSON-RPC id
        self._request_counter += 1
        request_id = f"req-{self._request_counter}"

        # Log send attempt
        logger.info(
            "asap.client.send",
            target_url=self.base_url,
            envelope_id=envelope.id,
            trace_id=envelope.trace_id,
            payload_type=envelope.payload_type,
            idempotency_key=idempotency_key,
        )

        # Build JSON-RPC request
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": ASAP_METHOD,
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
                if response.status_code >= 500:
                    # Server errors (5xx) are retriable
                    if attempt < self.max_retries - 1:
                        logger.warning(
                            "asap.client.server_error",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                        )
                        last_exception = ASAPConnectionError(
                            f"HTTP server error {response.status_code}: {response.text}"
                        )
                        continue
                    raise ASAPConnectionError(
                        f"HTTP server error {response.status_code}: {response.text}"
                    )
                if response.status_code >= 400:
                    # Client errors (4xx) are not retriable
                    raise ASAPConnectionError(
                        f"HTTP client error {response.status_code}: {response.text}"
                    )

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

                response_envelope = Envelope(**envelope_data)

                # Calculate duration and log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "asap.client.response",
                    target_url=self.base_url,
                    envelope_id=envelope.id,
                    response_id=response_envelope.id,
                    trace_id=envelope.trace_id,
                    duration_ms=round(duration_ms, 2),
                    attempts=attempt + 1,
                )

                return response_envelope

            except httpx.ConnectError as e:
                last_exception = ASAPConnectionError(f"Connection error: {e}", cause=e)
                # Log retry attempt
                if attempt < self.max_retries - 1:
                    logger.warning(
                        "asap.client.retry",
                        target_url=self.base_url,
                        envelope_id=envelope.id,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        error=str(e),
                    )
                    continue
                # Log final failure
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    "asap.client.error",
                    target_url=self.base_url,
                    envelope_id=envelope.id,
                    error="Connection failed after retries",
                    error_type="ASAPConnectionError",
                    duration_ms=round(duration_ms, 2),
                    attempts=attempt + 1,
                )
                raise last_exception from e

            except httpx.TimeoutException as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                last_exception = ASAPTimeoutError(
                    f"Request timeout after {self.timeout}s", timeout=self.timeout
                )
                # Log timeout (don't retry)
                logger.error(
                    "asap.client.error",
                    target_url=self.base_url,
                    envelope_id=envelope.id,
                    error="Request timeout",
                    error_type="ASAPTimeoutError",
                    timeout=self.timeout,
                    duration_ms=round(duration_ms, 2),
                )
                raise last_exception from e

            except (ASAPConnectionError, ASAPRemoteError, ASAPTimeoutError):
                # Re-raise our custom errors
                raise

            except Exception as e:
                # Log unexpected error
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.exception(
                    "asap.client.error",
                    target_url=self.base_url,
                    envelope_id=envelope.id,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=round(duration_ms, 2),
                )
                # Wrap unexpected errors
                raise ASAPConnectionError(f"Unexpected error: {e}", cause=e) from e

        # Defensive code: This should never be reached because the loop above
        # always either returns successfully or raises an exception.
        # Kept as a safety net for future code changes.
        if last_exception:  # pragma: no cover
            raise last_exception
        raise ASAPConnectionError("Max retries exceeded")  # pragma: no cover
