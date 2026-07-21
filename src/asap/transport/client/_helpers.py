"""Module-level helpers and constants for the ASAP async HTTP client.

- ``_parse_max_age_from_cache_control`` — Cache-Control TTL parsing for manifest caching.
- ``_record_send_error_metrics`` — send error metric emission.
- ``_parse_retry_after`` — ``Retry-After`` header (delta-seconds or HTTP-date) parsing.
- ``_log_circuit_event`` — deduplicated circuit-breaker OPEN/CLOSED transition logging.
- ``_RetryableSend`` — internal sentinel signalling a retryable ``send`` attempt.

These helpers keep ``ASAPClient`` focused on orchestration.
"""

from __future__ import annotations

import re
import time
from email.utils import parsedate_to_datetime

import httpx

from asap.observability import get_logger, get_metrics
from asap.transport.circuit_breaker import CircuitBreaker, CircuitState

# Re-exported by ``client/__init__.py`` for test patching.
logger = get_logger(__name__)

# Default timeout in seconds
DEFAULT_TIMEOUT = 60.0

# Default maximum retries
DEFAULT_MAX_RETRIES = 3

# Connection pool defaults (support 1000+ concurrent via reuse)
DEFAULT_POOL_CONNECTIONS = 100
DEFAULT_POOL_MAXSIZE = 100
# Timeout for acquiring a connection from the pool (distinct from request timeout)
DEFAULT_POOL_TIMEOUT = 5.0
# Maximum time to wait for manifest retrieval
MANIFEST_REQUEST_TIMEOUT = 10.0
# Cap for Cache-Control max-age when caching manifests (1 day)
DISCOVER_CACHE_MAX_AGE_CAP = 86400.0


def _parse_max_age_from_cache_control(cache_control: str | None) -> float | None:
    """Parse a ``Cache-Control`` header's ``max-age`` directive into seconds.

    Args:
        cache_control: The raw ``Cache-Control`` header value (or ``None``).

    Returns:
        The capped max-age in seconds, or ``None`` when absent/invalid/zero.
    """
    if not cache_control:
        return None
    match = re.search(r"max-age\s*=\s*(\d+)", cache_control, re.IGNORECASE)
    if not match:
        return None
    seconds = int(match.group(1))
    return min(seconds, DISCOVER_CACHE_MAX_AGE_CAP) if seconds > 0 else None


def _record_send_error_metrics(start_time: float, error: BaseException) -> None:
    """Emit the standard send-error counter and duration histogram."""
    duration_seconds = time.perf_counter() - start_time
    metrics = get_metrics()
    metrics.increment_counter("asap_transport_send_total", {"status": "error"})
    metrics.increment_counter(
        "asap_transport_send_errors_total",
        {"reason": type(error).__name__},
    )
    metrics.observe_histogram(
        "asap_transport_send_duration_seconds",
        duration_seconds,
        {"status": "error"},
    )


def _parse_retry_after(response: httpx.Response) -> float | None:
    """Parse a ``Retry-After`` header into a delay in seconds.

    The header may be either delta-seconds (numeric) or an HTTP-date per RFC 7231.
    Returns ``None`` when the header is absent or unparseable so callers can fall
    back to calculated exponential backoff. HTTP-dates in the past (or otherwise
    yielding a non-positive delay) also return ``None``.

    Args:
        response: The HTTP response carrying the (optional) ``Retry-After`` header.

    Returns:
        The delay in seconds, or ``None`` if the header is missing/invalid.
    """
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    # Delta-seconds: a non-negative integer/float.
    if raw.replace(".", "", 1).isdigit():
        return float(raw)
    # HTTP-date form.
    try:
        retry_date = parsedate_to_datetime(raw)
    except (ValueError, TypeError, AttributeError, OSError):
        return None
    if retry_date is None:
        return None
    calculated = retry_date.timestamp() - time.time()
    return calculated if calculated > 0 else None


def _log_circuit_event(
    breaker: CircuitBreaker,
    *,
    base_url: str,
    opened: bool,
    rate_limited: bool = False,
) -> None:
    """Log a circuit-breaker state transition if one occurred on this call.

    Inspects the breaker's state after a ``record_failure``/``record_success``
    call (the caller mutates the breaker, then invokes this helper). Centralises
    the four duplicated "circuit opened" / "circuit closed" log blocks that were
    scattered through ``send``.

    Args:
        breaker: The circuit breaker instance (already mutated by the caller).
        base_url: Sanitised target URL for log context.
        opened: When ``True``, the caller recorded a failure and we log an
            OPEN transition; when ``False``, the caller recorded a success and
            we log a CLOSED transition.
        rate_limited: Whether the failure was a 429 (used only to vary the
            opened log message wording).
    """
    current_state = breaker.get_state()
    target_state = CircuitState.OPEN if opened else CircuitState.CLOSED
    if current_state != target_state:
        return
    if opened:
        consecutive_failures = breaker.get_consecutive_failures()
        suffix = " (rate limited)" if rate_limited else ""
        logger.warning(
            "asap.client.circuit_opened",
            target_url=base_url,
            consecutive_failures=consecutive_failures,
            threshold=breaker.threshold,
            message=(
                f"Circuit breaker opened after {consecutive_failures} consecutive failures{suffix}"
            ),
        )
    else:
        logger.info(
            "asap.client.circuit_closed",
            target_url=base_url,
            message="Circuit breaker closed after successful request",
        )


class _RetryableSend(Exception):
    """Internal sentinel signalling that ``send`` should retry the current attempt.

    Carries the exception to record as ``last_exception`` for the retry path.
    Never escapes ``send``; caught by its retry loop.
    """

    def __init__(self, exc: Exception) -> None:
        super().__init__(exc)
        self.exc = exc
