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
import itertools
import random
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
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
from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.observability import get_logger
from asap.transport.cache import ManifestCache
from asap.transport.circuit_breaker import CircuitBreaker, CircuitState, get_registry
from asap.transport.jsonrpc import ASAP_METHOD
from asap.utils.sanitization import sanitize_url

# Module logger
logger = get_logger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT = 60.0

# Default maximum retries
DEFAULT_MAX_RETRIES = 3

# Connection pool defaults (support 1000+ concurrent via reuse)
DEFAULT_POOL_CONNECTIONS = 100
DEFAULT_POOL_MAXSIZE = 100
DEFAULT_POOL_TIMEOUT = 5.0


@dataclass
class RetryConfig:
    """Configuration for retry logic and circuit breaker.

    Groups retry and circuit breaker parameters to simplify client initialization
    and avoid boolean trap issues.

    Attributes:
        max_retries: Maximum retry attempts for transient failures (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)
        max_delay: Maximum delay in seconds for exponential backoff (default: 60.0)
        jitter: Whether to add random jitter to backoff delays (default: True)
        circuit_breaker_enabled: Enable circuit breaker pattern (default: False)
        circuit_breaker_threshold: Number of consecutive failures before opening circuit (default: 5)
        circuit_breaker_timeout: Seconds before transitioning OPEN -> HALF_OPEN (default: 60.0)
    """

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    jitter: bool = True
    circuit_breaker_enabled: bool = False
    circuit_breaker_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD
    circuit_breaker_timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT


class ASAPConnectionError(Exception):
    """Raised when connection to remote agent fails.

    This error occurs when the HTTP connection cannot be established
    or when the remote server returns an HTTP error status.

    Attributes:
        message: Error description with troubleshooting suggestions
        cause: Original exception that caused this error
        url: URL that failed to connect (if available)
    """

    def __init__(
        self, message: str, cause: Exception | None = None, url: str | None = None
    ) -> None:
        """Initialize connection error.

        Args:
            message: Error description
            cause: Original exception that caused this error
            url: URL that failed to connect (for better error messages)
        """
        # Enhance message with troubleshooting suggestions if URL is provided
        if url and "Verify" not in message and "troubleshooting" not in message.lower():
            enhanced_message = (
                f"{message}\n"
                f"Troubleshooting: Connection failed to {url}. "
                "Verify the agent is running and accessible. "
                "Check the URL format, network connectivity, and firewall settings."
            )
        else:
            enhanced_message = message

        super().__init__(enhanced_message)
        self.message = enhanced_message
        self.cause = cause
        self.url = url


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

    Pool sizing (pool_connections / pool_maxsize):
        Single-agent: 100 (default). Small cluster: 200–500. Large cluster: 500–1000.
        Supports 1000+ concurrent requests via connection reuse when pool_maxsize < concurrency.

    Example:
        >>> async with ASAPClient("http://localhost:8000") as client:
        ...     response = await client.send(envelope)
    """

    _circuit_breaker: Optional[CircuitBreaker]

    def __init__(
        self,
        base_url: str,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
        require_https: bool = True,
        retry_config: Optional[RetryConfig] = None,
        # Connection pool (httpx.Limits); enables 1000+ concurrent via reuse
        pool_connections: int | None = None,
        pool_maxsize: int | None = None,
        pool_timeout: float | None = None,
        # Individual retry parameters (for backward compatibility)
        # If retry_config is provided, these are ignored
        max_retries: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
        jitter: bool | None = None,
        circuit_breaker_enabled: bool | None = None,
        circuit_breaker_threshold: int | None = None,
        circuit_breaker_timeout: float | None = None,
    ) -> None:
        """Initialize ASAP client.

        Args:
            base_url: Base URL of the remote agent (e.g., "http://localhost:8000")
            timeout: Request timeout in seconds (default: 60)
            transport: Optional custom async transport (for testing). Must be an instance
                of httpx.AsyncBaseTransport (e.g., httpx.MockTransport).
            require_https: If True, enforces HTTPS for non-localhost connections (default: True).
            pool_connections: Max keep-alive connections in pool (default: 100). Passed to httpx.Limits.
            pool_maxsize: Max total connections in pool (default: 100). Passed to httpx.Limits.
            pool_timeout: Seconds to wait when acquiring a connection from the pool (default: 5.0).
                HTTP connections to localhost are allowed with a warning for development.
            retry_config: Optional RetryConfig dataclass to group retry and circuit breaker parameters.
                If provided, individual retry parameters are ignored.
            max_retries: Maximum retry attempts for transient failures (default: 3).
                Ignored if retry_config is provided.
            base_delay: Base delay in seconds for exponential backoff (default: 1.0).
                Ignored if retry_config is provided.
            max_delay: Maximum delay in seconds for exponential backoff (default: 60.0).
                Ignored if retry_config is provided.
            jitter: Whether to add random jitter to backoff delays (default: True).
                Ignored if retry_config is provided.
            circuit_breaker_enabled: Enable circuit breaker pattern (default: False).
                Ignored if retry_config is provided.
            circuit_breaker_threshold: Number of consecutive failures before opening circuit (default: 5).
                Ignored if retry_config is provided.
            circuit_breaker_timeout: Seconds before transitioning OPEN -> HALF_OPEN (default: 60.0).
                Ignored if retry_config is provided.

        Raises:
            ValueError: If URL format is invalid, scheme is not HTTP/HTTPS, or HTTPS is
                required but URL uses HTTP for non-localhost connections.

        Example:
            >>> # Using individual parameters (backward compatible)
            >>> client = ASAPClient("http://localhost:8000", max_retries=5)
            >>>
            >>> # Using RetryConfig (recommended)
            >>> config = RetryConfig(max_retries=5, circuit_breaker_enabled=True)
            >>> client = ASAPClient("http://localhost:8000", retry_config=config)
        """
        # Extract retry config values
        if retry_config is not None:
            # Use retry_config values
            max_retries_val = retry_config.max_retries
            base_delay_val = retry_config.base_delay
            max_delay_val = retry_config.max_delay
            jitter_val = retry_config.jitter
            circuit_breaker_enabled_val = retry_config.circuit_breaker_enabled
            circuit_breaker_threshold_val = retry_config.circuit_breaker_threshold
            circuit_breaker_timeout_val = retry_config.circuit_breaker_timeout
        else:
            # Use individual parameters with defaults
            max_retries_val = max_retries if max_retries is not None else DEFAULT_MAX_RETRIES
            base_delay_val = base_delay if base_delay is not None else DEFAULT_BASE_DELAY
            max_delay_val = max_delay if max_delay is not None else DEFAULT_MAX_DELAY
            jitter_val = jitter if jitter is not None else True
            circuit_breaker_enabled_val = (
                circuit_breaker_enabled if circuit_breaker_enabled is not None else False
            )
            circuit_breaker_threshold_val = (
                circuit_breaker_threshold
                if circuit_breaker_threshold is not None
                else DEFAULT_CIRCUIT_BREAKER_THRESHOLD
            )
            circuit_breaker_timeout_val = (
                circuit_breaker_timeout
                if circuit_breaker_timeout is not None
                else DEFAULT_CIRCUIT_BREAKER_TIMEOUT
            )
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
        self._pool_connections = (
            pool_connections if pool_connections is not None else DEFAULT_POOL_CONNECTIONS
        )
        self._pool_maxsize = pool_maxsize if pool_maxsize is not None else DEFAULT_POOL_MAXSIZE
        self._pool_timeout = pool_timeout if pool_timeout is not None else DEFAULT_POOL_TIMEOUT
        self.max_retries = max_retries_val
        self.require_https = require_https
        self.base_delay = base_delay_val
        self.max_delay = max_delay_val
        self.jitter = jitter_val
        self.circuit_breaker_enabled = circuit_breaker_enabled_val
        self._transport = transport
        self._client: httpx.AsyncClient | None = None
        # Thread-safe counter using itertools.count
        self._request_counter = itertools.count(1)

        # Initialize circuit breaker if enabled
        # Use registry to ensure state is shared across multiple client instances
        # for the same base_url
        if circuit_breaker_enabled_val:
            registry = get_registry()
            self._circuit_breaker = registry.get_or_create(
                base_url=sanitize_url(self.base_url),
                threshold=circuit_breaker_threshold_val,
                timeout=circuit_breaker_timeout_val,
            )
        else:
            self._circuit_breaker = None

        # Initialize manifest cache (shared across client instances for efficiency)
        self._manifest_cache = ManifestCache()

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
        delay = self.base_delay * (2**attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled (random value between 0 and 10% of delay)
        # Note: random.uniform is appropriate here - jitter for retry backoff
        # does not require cryptographic security, only statistical distribution
        if self.jitter:
            jitter_amount: float = random.uniform(0, delay * 0.1)  # nosec B311
            delay += jitter_amount

        return float(delay)

    async def _validate_connection(self) -> bool:
        """Validate that the agent endpoint is accessible.

        Performs a pre-flight check by attempting to access the agent's
        manifest endpoint. This can be used to detect connection issues
        before sending actual requests.

        Note: This is an optional validation step that can be disabled
        for performance reasons in production environments.

        Returns:
            True if connection is valid, False otherwise

        Raises:
            ASAPConnectionError: If connection validation fails
        """
        if not self._client:
            raise ASAPConnectionError(
                "Client not connected. Use 'async with' context.",
                url=sanitize_url(self.base_url),
            )

        try:
            # Try to access a lightweight endpoint (manifest or health check)
            # Using HEAD request to minimize bandwidth
            response = await self._client.head(
                f"{self.base_url}/.well-known/asap/manifest.json",
                timeout=min(self.timeout, 5.0),  # Shorter timeout for validation
            )
            # Any 2xx or 3xx response indicates the server is reachable
            is_valid = 200 <= response.status_code < 400
            if not is_valid:
                logger.warning(
                    "asap.client.connection_validation_failed",
                    target_url=sanitize_url(self.base_url),
                    status_code=response.status_code,
                    message=(
                        f"Connection validation failed for {self.base_url}. "
                        f"Server returned status {response.status_code}. "
                        f"Verify the agent is running and the URL is correct."
                    ),
                )
            return is_valid
        except httpx.ConnectError as e:
            logger.warning(
                "asap.client.connection_validation_failed",
                target_url=sanitize_url(self.base_url),
                error=str(e),
                message=(
                    f"Connection validation failed for {self.base_url}. "
                    f"Cannot reach the agent. Verify the agent is running and accessible. "
                    f"Error: {str(e)[:200]}"
                ),
            )
            return False
        except httpx.TimeoutException:
            logger.warning(
                "asap.client.connection_validation_timeout",
                target_url=sanitize_url(self.base_url),
                timeout=self.timeout,
                message=(
                    f"Connection validation timed out for {self.base_url}. "
                    f"Check network connectivity and firewall settings."
                ),
            )
            return False
        except Exception as e:
            logger.warning(
                "asap.client.connection_validation_error",
                target_url=sanitize_url(self.base_url),
                error=str(e),
                error_type=type(e).__name__,
                message=(
                    f"Connection validation encountered an error for {self.base_url}: {e}. "
                    f"Verify the agent is running and accessible."
                ),
            )
            return False

    @property
    def is_connected(self) -> bool:
        """Check if client has an active connection."""
        return self._client is not None

    async def __aenter__(self) -> "ASAPClient":
        """Enter async context and open connection."""
        limits = httpx.Limits(
            max_keepalive_connections=self._pool_connections,
            max_connections=self._pool_maxsize,
            keepalive_expiry=DEFAULT_POOL_TIMEOUT,
        )
        timeout_config = httpx.Timeout(self.timeout, pool=self._pool_timeout)
        if self._transport:
            self._client = httpx.AsyncClient(
                transport=self._transport,
                timeout=timeout_config,
                limits=limits,
            )
        else:
            self._client = httpx.AsyncClient(
                timeout=timeout_config,
                limits=limits,
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
            ValueError: If envelope is None
            ASAPConnectionError: If connection fails or HTTP error occurs
            ASAPTimeoutError: If request times out
            ASAPRemoteError: If remote agent returns JSON-RPC error
            CircuitOpenError: If circuit breaker is open and request is rejected

        Example:
            >>> async with ASAPClient("http://localhost:8000") as client:
            ...     response = await client.send(envelope)
            ...     response.payload_type
        """
        if envelope is None:
            raise ValueError("envelope cannot be None")

        if not self._client:
            raise ASAPConnectionError(
                "Client not connected. Use 'async with' context.",
                url=sanitize_url(self.base_url),
            )

        # Check circuit breaker state before attempting request
        if self._circuit_breaker is not None and not self._circuit_breaker.can_attempt():
            consecutive_failures = self._circuit_breaker.get_consecutive_failures()
            raise CircuitOpenError(
                base_url=sanitize_url(self.base_url),
                consecutive_failures=consecutive_failures,
            )

        start_time = time.perf_counter()

        # Generate idempotency key for retries
        idempotency_key = generate_id()

        # Get next request counter value (thread-safe)
        request_id = f"req-{next(self._request_counter)}"

        # Log send attempt with context (sanitize URL to hide credentials)
        sanitized_url = sanitize_url(self.base_url)
        logger.info(
            "asap.client.send",
            target_url=sanitized_url,
            envelope_id=envelope.id,
            trace_id=envelope.trace_id,
            payload_type=envelope.payload_type,
            idempotency_key=idempotency_key,
            max_retries=self.max_retries,
            message=(
                f"Sending envelope {envelope.id} to {sanitized_url} "
                f"(payload: {envelope.payload_type}, max_retries: {self.max_retries})"
            ),
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
                    error_msg = (
                        f"HTTP server error {response.status_code} from {self.base_url}. "
                        f"Server returned: {response.text[:200]}"
                    )
                    if attempt < self.max_retries - 1:
                        delay = self._calculate_backoff(attempt)
                        logger.warning(
                            "asap.client.server_error",
                            status_code=response.status_code,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                            target_url=sanitize_url(self.base_url),
                            message=f"Server error {response.status_code}, retrying in {delay:.2f}s (attempt {attempt + 1}/{self.max_retries})",
                        )
                        logger.info(
                            "asap.client.retry",
                            target_url=sanitize_url(self.base_url),
                            envelope_id=envelope.id,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        await asyncio.sleep(delay)
                        last_exception = ASAPConnectionError(error_msg, url=self.base_url)
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
                                target_url=sanitize_url(self.base_url),
                                consecutive_failures=consecutive_failures,
                                threshold=self._circuit_breaker.threshold,
                                message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                            )
                    raise ASAPConnectionError(error_msg, url=self.base_url)
                if response.status_code == 429:
                    # Rate limit (429) is retriable, respect Retry-After header
                    if attempt < self.max_retries - 1:
                        # Check for Retry-After header
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            retry_delay: Optional[float] = None
                            # Retry-After can be seconds (int/float) or HTTP date
                            # First, try to parse as seconds (numeric)
                            if retry_after.replace(".", "", 1).isdigit():
                                try:
                                    retry_delay = float(retry_after)
                                    logger.info(
                                        "asap.client.retry_after",
                                        target_url=sanitize_url(self.base_url),
                                        envelope_id=envelope.id,
                                        attempt=attempt + 1,
                                        retry_after_seconds=retry_delay,
                                        message=f"Respecting server Retry-After: {retry_delay}s",
                                    )
                                except ValueError:
                                    pass  # Fall through to date parsing
                            else:
                                # Try to parse as HTTP date
                                try:
                                    retry_date = parsedate_to_datetime(retry_after)
                                    if retry_date:
                                        # Calculate delay in seconds from now until retry_date
                                        now_timestamp = time.time()
                                        retry_timestamp = retry_date.timestamp()
                                        calculated_delay = retry_timestamp - now_timestamp
                                        # If date is in the past or delay is invalid, fall back to calculated backoff
                                        if calculated_delay <= 0:
                                            retry_delay = None  # Will trigger fallback
                                        else:
                                            retry_delay = calculated_delay
                                            logger.info(
                                                "asap.client.retry_after",
                                                target_url=sanitize_url(self.base_url),
                                                envelope_id=envelope.id,
                                                attempt=attempt + 1,
                                                retry_after_seconds=round(retry_delay, 2),
                                                retry_after_date=retry_after,
                                                message=f"Respecting server Retry-After date: {retry_after} ({retry_delay:.2f}s)",
                                            )
                                except (ValueError, TypeError, AttributeError, OSError):
                                    # Invalid date format or timestamp conversion error, fall back to calculated backoff
                                    pass

                            # If parsing failed or delay is invalid (None or <= 0), use calculated backoff
                            if retry_delay is None or retry_delay <= 0:
                                retry_delay = self._calculate_backoff(attempt)
                                logger.warning(
                                    "asap.client.retry_after_invalid",
                                    target_url=sanitize_url(self.base_url),
                                    envelope_id=envelope.id,
                                    retry_after_header=retry_after,
                                    fallback_delay=round(retry_delay, 2),
                                    message="Invalid Retry-After format, using calculated backoff",
                                )
                            delay = retry_delay
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
                            target_url=sanitize_url(self.base_url),
                            envelope_id=envelope.id,
                            attempt=attempt + 1,
                            max_retries=self.max_retries,
                            delay_seconds=round(delay, 2),
                        )
                        await asyncio.sleep(delay)
                        last_exception = ASAPConnectionError(
                            f"HTTP rate limit error 429 from {self.base_url}. "
                            f"Server response: {response.text[:200]}",
                            url=sanitize_url(self.base_url),
                        )
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
                                target_url=sanitize_url(self.base_url),
                                consecutive_failures=consecutive_failures,
                                threshold=self._circuit_breaker.threshold,
                                message=f"Circuit breaker opened after {consecutive_failures} consecutive failures (rate limited)",
                            )
                    raise ASAPConnectionError(
                        f"HTTP rate limit error 429 from {self.base_url} after {self.max_retries} attempts. "
                        f"Server response: {response.text[:200]}",
                        url=sanitize_url(self.base_url),
                    )
                if response.status_code >= 400:
                    # Client errors (4xx) are not retriable (except 429 handled above)
                    # We record a failure in the circuit breaker here because persistent 4xx
                    # (like 401/403) can indicate an unhealthy configuration or system state.
                    if self._circuit_breaker is not None:
                        self._circuit_breaker.record_failure()

                    raise ASAPConnectionError(
                        f"HTTP client error {response.status_code} from {self.base_url}. "
                        f"This indicates a problem with the request. "
                        f"Server response: {response.text[:200]}",
                        url=sanitize_url(self.base_url),
                    )

                # Parse JSON response
                try:
                    json_response = response.json()
                except Exception as e:
                    raise ASAPRemoteError(-32700, f"Invalid JSON response: {e}") from e

                # Check for JSON-RPC error
                if "error" in json_response:
                    # Record success pattern (service is reachable)
                    # A valid JSON-RPC error means the connection and transport are healthy
                    if self._circuit_breaker is not None:
                        self._circuit_breaker.record_success()

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
                            target_url=sanitize_url(self.base_url),
                            message="Circuit breaker closed after successful request",
                        )

                # Calculate duration and log success
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.info(
                    "asap.client.response",
                    target_url=sanitize_url(self.base_url),
                    envelope_id=envelope.id,
                    response_id=response_envelope.id,
                    trace_id=envelope.trace_id,
                    duration_ms=round(duration_ms, 2),
                    attempts=attempt + 1,
                )

                return response_envelope

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                is_timeout = isinstance(e, httpx.TimeoutException)
                error_type = "Timeout" if is_timeout else "Connection error"
                error_msg = (
                    f"{error_type} to {self.base_url}: {e}. "
                    f"Verify the agent is running and accessible."
                )
                if is_timeout:
                    last_exception = ASAPTimeoutError(
                        f"Request timeout after {self.timeout}s", timeout=self.timeout
                    )
                else:
                    last_exception = ASAPConnectionError(error_msg, cause=e, url=self.base_url)

                # Log retry attempt
                if attempt < self.max_retries - 1:
                    delay = self._calculate_backoff(attempt)
                    logger.warning(
                        "asap.client.retry",
                        target_url=sanitize_url(self.base_url),
                        envelope_id=envelope.id,
                        attempt=attempt + 1,
                        max_retries=self.max_retries,
                        error=str(e),
                        delay_seconds=round(delay, 2),
                        message=(
                            f"{error_type} to {self.base_url} (attempt {attempt + 1}/{self.max_retries}). "
                            f"Retrying in {delay:.2f}s. "
                            f"Error: {str(e)[:100]}"
                        ),
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
                            target_url=sanitize_url(self.base_url),
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )

                # Log final failure with detailed context
                duration_ms = (time.perf_counter() - start_time) * 1000
                error_type_name = "ASAPTimeoutError" if is_timeout else "ASAPConnectionError"
                logger.error(
                    "asap.client.error",
                    target_url=sanitize_url(self.base_url),
                    envelope_id=envelope.id,
                    error=f"{error_type} after retries",
                    error_type=error_type_name,
                    duration_ms=round(duration_ms, 2),
                    attempts=attempt + 1,
                    max_retries=self.max_retries,
                    timeout=self.timeout if is_timeout else None,
                    message=(
                        f"{error_type} to {self.base_url} failed after {attempt + 1} attempts. "
                        f"Total duration: {duration_ms:.2f}ms. "
                        f"Troubleshooting: Verify the agent is running, check network connectivity, "
                        f"and ensure the URL is correct. Original error: {str(e)[:200]}"
                    ),
                )
                raise last_exception from e

            except (ASAPConnectionError, ASAPRemoteError, ASAPTimeoutError):
                # Re-raise our custom errors without recording failure again
                # (failures are already recorded before these exceptions are raised)
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
                            target_url=sanitize_url(self.base_url),
                            consecutive_failures=consecutive_failures,
                            threshold=self._circuit_breaker.threshold,
                            message=f"Circuit breaker opened after {consecutive_failures} consecutive failures",
                        )
                # Log unexpected error
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.exception(
                    "asap.client.error",
                    target_url=sanitize_url(self.base_url),
                    envelope_id=envelope.id,
                    error=str(e),
                    error_type=type(e).__name__,
                    duration_ms=round(duration_ms, 2),
                )
                # Wrap unexpected errors
                raise ASAPConnectionError(
                    f"Unexpected error connecting to {self.base_url}: {e}. "
                    f"Verify the agent is running and accessible.",
                    cause=e,
                    url=sanitize_url(self.base_url),
                ) from e

        # Defensive code: This should never be reached because the loop above
        # always either returns successfully or raises an exception.
        # Kept as a safety net for future code changes.
        if last_exception:  # pragma: no cover
            raise last_exception
        raise ASAPConnectionError(
            f"Max retries ({self.max_retries}) exceeded for {self.base_url}. "
            f"Verify the agent is running and accessible.",
            url=sanitize_url(self.base_url),
        )  # pragma: no cover

    async def get_manifest(self, url: str | None = None) -> Manifest:
        """Get agent manifest from cache or HTTP endpoint.

        Checks cache first, then fetches from HTTP if not cached or expired.
        Caches successful responses with TTL (default: 5 minutes).
        Invalidates cache entry on error.

        Args:
            url: Manifest URL (defaults to {base_url}/.well-known/asap/manifest.json)

        Returns:
            Manifest object

        Raises:
            ASAPConnectionError: If HTTP request fails
            ASAPTimeoutError: If request times out
            ValueError: If manifest JSON is invalid

        Example:
            >>> async with ASAPClient("http://agent.example.com") as client:
            ...     manifest = await client.get_manifest()
            ...     print(manifest.id, manifest.name)
        """
        if url is None:
            url = f"{self.base_url}/.well-known/asap/manifest.json"

        if not self._client:
            raise ASAPConnectionError(
                "Client not connected. Use 'async with' context.",
                url=sanitize_url(url),
            )

        # Check cache first
        cached = self._manifest_cache.get(url)
        if cached is not None:
            logger.debug(
                "asap.client.manifest_cache_hit",
                url=sanitize_url(url),
                manifest_id=cached.id,
                message=f"Manifest cache hit for {sanitize_url(url)}",
            )
            return cached

        # Cache miss - fetch from HTTP
        logger.debug(
            "asap.client.manifest_cache_miss",
            url=sanitize_url(url),
            message=f"Manifest cache miss for {sanitize_url(url)}, fetching from HTTP",
        )

        try:
            response = await self._client.get(
                url,
                timeout=min(self.timeout, 10.0),  # Shorter timeout for manifest
            )

            if response.status_code >= 400:
                # HTTP error - invalidate cache if entry exists
                self._manifest_cache.invalidate(url)
                raise ASAPConnectionError(
                    f"HTTP error {response.status_code} fetching manifest from {url}. "
                    f"Server response: {response.text[:200]}",
                    url=sanitize_url(url),
                )

            # Parse JSON response
            try:
                manifest_data = response.json()
            except Exception as e:
                self._manifest_cache.invalidate(url)
                raise ValueError(f"Invalid JSON in manifest response: {e}") from e

            # Parse Manifest object
            try:
                manifest = Manifest(**manifest_data)
            except Exception as e:
                self._manifest_cache.invalidate(url)
                raise ValueError(f"Invalid manifest format: {e}") from e

            # Cache successful response
            self._manifest_cache.set(url, manifest)
            logger.info(
                "asap.client.manifest_fetched",
                url=sanitize_url(url),
                manifest_id=manifest.id,
                message=f"Manifest fetched and cached for {sanitize_url(url)}",
            )

            return manifest

        except httpx.TimeoutException as e:
            self._manifest_cache.invalidate(url)
            raise ASAPTimeoutError(
                f"Manifest request timeout after {self.timeout}s", timeout=self.timeout
            ) from e
        except httpx.ConnectError as e:
            self._manifest_cache.invalidate(url)
            raise ASAPConnectionError(
                f"Connection error fetching manifest from {url}: {e}. "
                f"Verify the agent is running and accessible.",
                cause=e,
                url=sanitize_url(url),
            ) from e
        except (ASAPConnectionError, ASAPTimeoutError, ValueError):
            # Re-raise our custom errors (cache already invalidated above)
            raise
        except Exception as e:
            # Unexpected error - invalidate cache
            self._manifest_cache.invalidate(url)
            logger.exception(
                "asap.client.manifest_error",
                url=sanitize_url(url),
                error=str(e),
                error_type=type(e).__name__,
                message=f"Unexpected error fetching manifest from {url}: {e}",
            )
            raise ASAPConnectionError(
                f"Unexpected error fetching manifest from {url}: {e}. "
                f"Verify the agent is running and accessible.",
                cause=e,
                url=sanitize_url(url),
            ) from e

    async def send_batch(
        self,
        envelopes: list[Envelope],
        return_exceptions: bool = False,
    ) -> list[Envelope | BaseException]:
        """Send multiple envelopes in parallel using asyncio.gather.

        Uses asyncio.gather to send all envelopes concurrently, leveraging
        connection pooling and HTTP/2 multiplexing for optimal throughput.

        Args:
            envelopes: List of ASAP envelopes to send
            return_exceptions: If True, exceptions are returned in the result list
                instead of being raised. If False (default), the first exception
                encountered will be raised.

        Returns:
            List of response envelopes in the same order as input envelopes.
            If return_exceptions=True, failed sends will have the exception
            in their position instead of an Envelope.

        Raises:
            ValueError: If envelopes list is empty
            ASAPConnectionError: If any send fails (when return_exceptions=False)
            ASAPTimeoutError: If any send times out (when return_exceptions=False)
            ASAPRemoteError: If any remote agent returns error (when return_exceptions=False)
            CircuitOpenError: If circuit breaker is open (when return_exceptions=False)

        Example:
            >>> async with ASAPClient("http://localhost:8000") as client:
            ...     responses = await client.send_batch([env1, env2, env3])
            ...     for response in responses:
            ...         print(response.payload_type)
            >>>
            >>> # With error handling
            >>> async with ASAPClient("http://localhost:8000") as client:
            ...     results = await client.send_batch(envelopes, return_exceptions=True)
            ...     for i, result in enumerate(results):
            ...         if isinstance(result, BaseException):
            ...             print(f"Envelope {i} failed: {result}")
            ...         else:
            ...             print(f"Envelope {i} succeeded: {result.id}")
        """
        if not envelopes:
            raise ValueError("envelopes list cannot be empty")

        if not self._client:
            raise ASAPConnectionError(
                "Client not connected. Use 'async with' context.",
                url=sanitize_url(self.base_url),
            )

        batch_size = len(envelopes)
        logger.info(
            "asap.client.send_batch",
            target_url=sanitize_url(self.base_url),
            batch_size=batch_size,
            message=f"Sending batch of {batch_size} envelopes to {sanitize_url(self.base_url)}",
        )

        start_time = time.perf_counter()

        # Create send tasks for all envelopes
        tasks = [self.send(envelope) for envelope in envelopes]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Count successes and failures
        if return_exceptions:
            success_count = sum(1 for r in results if isinstance(r, Envelope))
            failure_count = batch_size - success_count
        else:
            success_count = batch_size
            failure_count = 0

        logger.info(
            "asap.client.send_batch_complete",
            target_url=sanitize_url(self.base_url),
            batch_size=batch_size,
            success_count=success_count,
            failure_count=failure_count,
            duration_ms=round(duration_ms, 2),
            throughput_per_second=round(batch_size / (duration_ms / 1000), 2) if duration_ms > 0 else 0,
            message=(
                f"Batch of {batch_size} envelopes completed in {duration_ms:.2f}ms "
                f"({success_count} succeeded, {failure_count} failed)"
            ),
        )

        return results
