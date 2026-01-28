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

import asyncio
import random
import threading
import time
from enum import Enum
from typing import Any, Optional
from urllib.parse import ParseResult

import httpx

from asap.errors import CircuitOpenError
from asap.models.constants import (
    DEFAULT_BASE_DELAY,
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
    DEFAULT_MAX_DELAY,
)
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


class CircuitState(str, Enum):
    """Circuit breaker states.

    CLOSED: Normal operation, requests are allowed
    OPEN: Circuit is open, requests are rejected immediately
    HALF_OPEN: Testing state, allows one request to test if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker pattern implementation for resilient request handling.

    The circuit breaker prevents cascading failures by opening the circuit
    after a threshold of consecutive failures, then attempting to recover
    after a timeout period.

    States:
    - CLOSED: Normal operation, all requests allowed
    - OPEN: Circuit is open, all requests rejected immediately
    - HALF_OPEN: Testing state, allows one request to test recovery

    This implementation is thread-safe using RLock for concurrent access.

    Attributes:
        threshold: Number of consecutive failures before opening circuit
        timeout: Seconds to wait before transitioning from OPEN to HALF_OPEN
        _state: Current circuit state
        _consecutive_failures: Number of consecutive failures
        _last_failure_time: Timestamp of last failure (for timeout calculation)
        _lock: Thread lock for thread-safe state transitions
    """

    def __init__(
        self,
        threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
    ) -> None:
        """Initialize circuit breaker.

        Args:
            threshold: Number of consecutive failures before opening (default: 5)
            timeout: Seconds before transitioning OPEN -> HALF_OPEN (default: 60.0)
        """
        self.threshold = threshold
        self.timeout = timeout
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._last_failure_time: float | None = None
        self._lock = threading.RLock()

    def record_success(self) -> None:
        """Record a successful request.

        Resets failure count and closes circuit if it was HALF_OPEN.
        """
        with self._lock:
            self._consecutive_failures = 0
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED
                self._last_failure_time = None

    def record_failure(self) -> None:
        """Record a failed request.

        Increments failure count and opens circuit if threshold is reached.
        """
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()

            if self._consecutive_failures >= self.threshold:
                if self._state == CircuitState.CLOSED:
                    self._state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        """Check if a request can be attempted.

        Returns:
            True if request can be attempted, False if circuit is open
        """
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.timeout:
                        # Transition to HALF_OPEN to test recovery
                        self._state = CircuitState.HALF_OPEN
                        return True
                # Still in OPEN state, reject request
                return False

            # CLOSED or HALF_OPEN: allow request
            return True

    def get_state(self) -> CircuitState:
        """Get current circuit state.

        Returns:
            Current circuit state
        """
        with self._lock:
            return self._state

    def get_consecutive_failures(self) -> int:
        """Get number of consecutive failures.

        Returns:
            Number of consecutive failures
        """
        with self._lock:
            return self._consecutive_failures


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
        require_https: Whether HTTPS is required for non-localhost connections
        is_connected: Whether the client has an active connection
        _circuit_breaker: Optional circuit breaker instance

    Example:
        >>> async with ASAPClient("http://localhost:8000") as client:
        ...     response = await client.send(envelope)
    """

    _circuit_breaker: Optional[CircuitBreaker]

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | httpx.BaseTransport | None = None,
        require_https: bool = True,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        jitter: bool = True,
        circuit_breaker_enabled: bool = False,
        circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        circuit_breaker_timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
    ) -> None:
        """Initialize ASAP client.

        Args:
            base_url: Base URL of the remote agent (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds (default: 60)
            max_retries: Maximum retry attempts for transient failures (default: 3)
            transport: Optional custom transport (for testing). Can be sync or async.
            require_https: If True, enforces HTTPS for non-localhost connections (default: True).
                HTTP connections to localhost are allowed with a warning for development.
            base_delay: Base delay in seconds for exponential backoff (default: 1.0)
            max_delay: Maximum delay in seconds for exponential backoff (default: 60.0)
            jitter: Whether to add random jitter to backoff delays (default: True)
            circuit_breaker_enabled: Enable circuit breaker pattern (default: False)
            circuit_breaker_threshold: Number of consecutive failures before opening circuit (default: 5)
            circuit_breaker_timeout: Seconds before transitioning OPEN -> HALF_OPEN (default: 60.0)

        Raises:
            ValueError: If URL format is invalid, scheme is not HTTP/HTTPS, or HTTPS is
                required but URL uses HTTP for non-localhost connections.
        """
        # Validate URL format and scheme
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(
                f"Invalid base_url format: {base_url}. Must be a valid URL (e.g., http://localhost:8000)"
            )

        # Restrict to HTTP/HTTPS schemes only
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(
                f"Invalid URL scheme: {parsed.scheme}. Only 'http' and 'https' are allowed. "
                f"Received: {base_url}"
            )

        # Validate HTTPS requirement
        is_https = parsed.scheme.lower() == "https"
        is_local = self._is_localhost(parsed)

        if require_https and not is_https:
            if is_local:
                # Allow HTTP for localhost with warning
                logger.warning(
                    "asap.client.http_localhost",
                    url=base_url,
                    message=(
                        "Using HTTP for localhost connection. "
                        "For production, use HTTPS. "
                        "To disable this warning, set require_https=False."
                    ),
                )
            else:
                # Reject HTTP for non-localhost
                raise ValueError(
                    f"HTTPS is required for non-localhost connections. "
                    f"Received HTTP URL: {base_url}. "
                    f"Please use HTTPS or set require_https=False to override "
                    f"(not recommended for production)."
                )

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.require_https = require_https
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        self._request_counter = 0

        # Initialize circuit breaker if enabled
        if circuit_breaker_enabled:
            self._circuit_breaker = CircuitBreaker(
                threshold=circuit_breaker_threshold,
                timeout=circuit_breaker_timeout,
            )
        else:
            self._circuit_breaker = None

    @staticmethod
    def _is_localhost(parsed_url: ParseResult) -> bool:
        """Check if URL points to localhost.

        Detects localhost, 127.0.0.1, and ::1 (IPv6 localhost).

        Args:
            parsed_url: Parsed URL from urlparse

        Returns:
            True if URL points to localhost, False otherwise
        """
        hostname = parsed_url.hostname
        if not hostname:
            return False

        hostname_lower = hostname.lower()
        # Handle both ::1 and [::1] (bracket notation from URL parsing)
        return hostname_lower in ("localhost", "127.0.0.1", "::1", "[::1]")

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay for retry attempt.

        Implements exponential backoff with optional jitter:
        delay = base_delay * (2 ** attempt) + jitter

        The delay is capped at max_delay to prevent excessively long waits.

        Args:
            attempt: Zero-based attempt number (0 = first retry)

        Returns:
            Delay in seconds before next retry attempt
        """
        # Calculate exponential delay: base_delay * (2 ** attempt)
        delay = self.base_delay * (2 ** attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled (random value between 0 and 10% of delay)
        if self.jitter:
            jitter_amount: float = random.uniform(0, delay * 0.1)
            delay += jitter_amount

        return float(delay)

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
            CircuitOpenError: If circuit breaker is open and request is rejected

        Example:
            >>> async with ASAPClient("http://localhost:8000") as client:
            ...     response = await client.send(envelope)
            ...     response.payload_type
        """
        if not self._client:
            raise ASAPConnectionError("Client not connected. Use 'async with' context.")

        # Check circuit breaker state before attempting request
        if self._circuit_breaker is not None:
            if not self._circuit_breaker.can_attempt():
                consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                raise CircuitOpenError(
                    base_url=self.base_url,
                    consecutive_failures=consecutive_failures,
                )

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
                    error_msg = f"HTTP server error {response.status_code}: {response.text}"
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            "asap.client.server_error",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        logger.info(
                            "asap.client.retry",
                            target_url=self.base_url,
                            envelope_id=envelope.id,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        await asyncio.sleep(delay)
                        last_exception = ASAPConnectionError(error_msg)
                        continue
                    # All retries exhausted, record failure in circuit breaker
                    if self._circuit_breaker is not None:
                        previous_state = self._circuit_breaker.get_state()
                        self._circuit_breaker.record_failure()
                        current_state = self._circuit_breaker.get_state()
                        consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                        # Log state change if circuit opened
                        if previous_state != current_state and current_state == CircuitState.OPEN:
                            logger.warning(
                                "asap.client.circuit_opened",
                                target_url=self.base_url,
                                consecutive_failures=consecutive_failures,
                                threshold=self._circuit_breaker.threshold,
                                message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                            )
                    raise ASAPConnectionError(error_msg)
                if response.status_code == 429:
                    # Rate limit (429) is retriable, respect Retry-After header
                    if attempt < self.max_retries - 1:
                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            try:
                                # Retry-After can be seconds (int) or HTTP date
                                delay = float(retry_after)
                                logger.info(
                                    "asap.client.retry_after",
                                    target_url=self.base_url,
                                    envelope_id=envelope.id,
                                    attempt=attempt + 1,
                                    retry_after_seconds=delay,
                                    message=f"Respecting server Retry-After: {delay}s",
                                )
                            except ValueError:
                                # If Retry-After is a date, fall back to calculated backoff
                                delay = self._calculate_backoff(attempt)
                                logger.warning(
                                    "asap.client.retry_after_invalid",
                                    target_url=self.base_url,
                                    envelope_id=envelope.id,
                                    retry_after_header=retry_after,
                                    fallback_delay=round(delay, 2),
                                    message="Invalid Retry-After format, using calculated backoff",
                                )
                        else:
                            # No Retry-After header, use calculated backoff
                            delay = self._calculate_backoff(attempt)
                        logger.warning(
                            "asap.client.rate_limited",
                            status_code=429,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        logger.info(
                            "asap.client.retry",
                            target_url=self.base_url,
                            envelope_id=envelope.id,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        await asyncio.sleep(delay)
                        last_exception = ASAPConnectionError(
                            f"HTTP rate limit error 429: {response.text}"
                        )
                        continue
                    raise ASAPConnectionError(
                        f"HTTP rate limit error 429: {response.text}"
                    )
                if response.status_code >= 400:
                    # Client errors (4xx) are not retriable (except 429 handled above)
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

                # Record success in circuit breaker
                if self._circuit_breaker is not None:
                    previous_state = self._circuit_breaker.get_state()
                    self._circuit_breaker.record_success()
                    current_state = self._circuit_breaker.get_state()
                    # Log state change if circuit was closed
                    if previous_state != current_state and current_state == CircuitState.CLOSED:
                        logger.info(
                            "asap.client.circuit_closed",
                            target_url=self.base_url,
                            message="Circuit breaker closed after successful request",
                        )

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
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        "asap.client.retry",
                        target_url=self.base_url,
                        envelope_id=envelope.id,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        error=str(e),
                        delay_seconds=round(delay, 2),
                    )
                    await asyncio.sleep(delay)
                    continue
                # All retries exhausted, record failure in circuit breaker
                if self._circuit_breaker is not None:
                    previous_state = self._circuit_breaker.get_state()
                    self._circuit_breaker.record_failure()
                    current_state = self._circuit_breaker.get_state()
                    consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                    # Log state change if circuit opened
                    if previous_state != current_state and current_state == CircuitState.OPEN:
                        logger.warning(
                            "asap.client.circuit_opened",
                            target_url=self.base_url,
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )
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
                # Record failure in circuit breaker
                if self._circuit_breaker is not None:
                    previous_state = self._circuit_breaker.get_state()
                    self._circuit_breaker.record_failure()
                    current_state = self._circuit_breaker.get_state()
                    consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                    # Log state change if circuit opened
                    if previous_state != current_state and current_state == CircuitState.OPEN:
                        logger.warning(
                            "asap.client.circuit_opened",
                            target_url=self.base_url,
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )
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
                # Re-raise our custom errors (but record failure if not already recorded)
                if self._circuit_breaker is not None and attempt == self.max_retries - 1:
                    # Only record on final attempt to avoid double-counting
                    previous_state = self._circuit_breaker.get_state()
                    self._circuit_breaker.record_failure()
                    current_state = self._circuit_breaker.get_state()
                    consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                    # Log state change if circuit opened
                    if previous_state != current_state and current_state == CircuitState.OPEN:
                        logger.warning(
                            "asap.client.circuit_opened",
                            target_url=self.base_url,
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )
                raise

            except Exception as e:
                # Record failure in circuit breaker
                if self._circuit_breaker is not None:
                    previous_state = self._circuit_breaker.get_state()
                    self._circuit_breaker.record_failure()
                    current_state = self._circuit_breaker.get_state()
                    consecutive_failures = self._circuit_breaker.get_consecutive_failures()
                    # Log state change if circuit opened
                    if previous_state != current_state and current_state == CircuitState.OPEN:
                        logger.warning(
                            "asap.client.circuit_opened",
                            target_url=self.base_url,
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )
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
