"""Error recovery patterns example for ASAP protocol.

This module demonstrates retry with backoff, circuit breaker, and fallback
patterns using ASAP's built-in support and small helpers you can reuse.

Patterns:
    1. Retry with backoff: RetryConfig + ASAPClient, or a standalone retry loop.
    2. Circuit breaker: CircuitBreaker (and ASAPClient with circuit_breaker_enabled).
    3. Fallback: Try primary operation; on failure use fallback result or backup agent.

Run:
    uv run python -m asap.examples.error_recovery
"""

from __future__ import annotations

import argparse
import random
import time
from typing import Callable, Sequence, TypeVar

from asap.observability import get_logger
from asap.transport.circuit_breaker import CircuitBreaker, CircuitState
from asap.transport.client import RetryConfig

logger = get_logger(__name__)

T = TypeVar("T")

# Demo defaults (short delays so the example runs quickly)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 0.05
DEFAULT_MAX_DELAY = 0.5
DEFAULT_CB_THRESHOLD = 2
DEFAULT_CB_TIMEOUT = 0.2


def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    jitter: bool = True,
) -> T:
    """Call fn(); on exception, retry with exponential backoff until success or max_retries.

    Same idea as ASAPClient's internal retry: delay = min(base_delay * 2^attempt, max_delay)
    with optional jitter. Use this for custom operations outside the client.

    Args:
        fn: Callable that may raise. No arguments.
        max_retries: Number of retries after the first attempt (total attempts = max_retries + 1).
        base_delay: Base delay in seconds for exponential backoff.
        max_delay: Cap on delay in seconds.
        jitter: If True, add random jitter to each delay.

    Returns:
        Result of fn().

    Raises:
        Last exception raised by fn() if all attempts fail.
    """
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except BaseException as e:
            last_exc = e
            if attempt == max_retries:
                raise
            delay = min(base_delay * (2**attempt), max_delay)
            if jitter:
                delay = delay * (0.5 + random.random())  # nosec B311
            logger.info(
                "asap.error_recovery.retry",
                attempt=attempt + 1,
                max_retries=max_retries,
                delay_seconds=round(delay, 3),
                error=str(e),
            )
            time.sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("retry_with_backoff: no result and no exception")


def with_fallback(
    primary_fn: Callable[[], T],
    fallback_fn: Callable[[], T],
) -> T:
    """Try primary_fn(); on exception, call fallback_fn() and return its result.

    Use when you have a backup (e.g. cached value, secondary agent, default payload).

    Args:
        primary_fn: Operation that may raise.
        fallback_fn: Called only if primary_fn raises; should not raise.

    Returns:
        Result of primary_fn or fallback_fn.
    """
    try:
        return primary_fn()
    except Exception as e:
        logger.warning(
            "asap.error_recovery.fallback",
            primary_error=str(e),
            message="Using fallback",
        )
        return fallback_fn()


def demo_retry_with_backoff(
    fails_then_succeeds_at: int = 2,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> None:
    """Demonstrate retry with backoff using a flaky callable that fails N times then succeeds."""
    call_count = 0

    def flaky_op() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < fails_then_succeeds_at:
            raise ConnectionError(f"Simulated failure (call #{call_count})")
        return "ok"

    result = retry_with_backoff(
        flaky_op,
        max_retries=max_retries,
        base_delay=DEFAULT_BASE_DELAY,
        max_delay=DEFAULT_MAX_DELAY,
    )
    logger.info(
        "asap.error_recovery.retry_demo_complete",
        result=result,
        calls=call_count,
    )


def demo_circuit_breaker(
    threshold: int = DEFAULT_CB_THRESHOLD,
    timeout: float = DEFAULT_CB_TIMEOUT,
) -> None:
    """Demonstrate circuit breaker: record failures until OPEN, wait, then HALF_OPEN and recover."""
    breaker = CircuitBreaker(threshold=threshold, timeout=timeout)

    # CLOSED -> record failures until OPEN
    for _ in range(threshold):
        breaker.record_failure()
    assert breaker.get_state() == CircuitState.OPEN  # nosec B101
    assert breaker.can_attempt() is False  # nosec B101
    logger.info(
        "asap.error_recovery.circuit_open",
        state=breaker.get_state().value,
        consecutive_failures=breaker.get_consecutive_failures(),
    )

    # Wait for timeout -> HALF_OPEN
    time.sleep(timeout + 0.05)
    assert breaker.can_attempt() is True  # nosec B101
    assert breaker.get_state() == CircuitState.HALF_OPEN  # nosec B101
    logger.info(
        "asap.error_recovery.circuit_half_open",
        state=breaker.get_state().value,
    )

    # Success -> CLOSED
    breaker.record_success()
    assert breaker.get_state() == CircuitState.CLOSED  # nosec B101
    logger.info(
        "asap.error_recovery.circuit_closed",
        state=breaker.get_state().value,
    )


def demo_fallback() -> None:
    """Demonstrate fallback: primary raises, fallback returns default result."""

    def primary() -> str:
        raise RuntimeError("Primary agent unavailable")

    def fallback() -> str:
        return '{"status": "fallback", "message": "default result"}'

    result = with_fallback(primary, fallback)
    logger.info(
        "asap.error_recovery.fallback_demo_complete",
        result=result,
    )


def show_client_retry_config() -> None:
    """Log how to use RetryConfig with ASAPClient (for reference)."""
    config = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        jitter=True,
        circuit_breaker_enabled=True,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=60.0,
    )
    logger.info(
        "asap.error_recovery.client_retry_config",
        message="Use ASAPClient(..., retry_config=RetryConfig(...)); CircuitOpenError when circuit is open",
        max_retries=config.max_retries,
        circuit_breaker_enabled=config.circuit_breaker_enabled,
    )


def run_demo(
    skip_retry: bool = False,
    skip_circuit: bool = False,
    skip_fallback: bool = False,
) -> None:
    """Run all error recovery demos (retry, circuit breaker, fallback)."""
    if not skip_retry:
        demo_retry_with_backoff()
    if not skip_circuit:
        demo_circuit_breaker()
    if not skip_fallback:
        demo_fallback()
    show_client_retry_config()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the error recovery demo."""
    parser = argparse.ArgumentParser(
        description="Error recovery patterns: retry with backoff, circuit breaker, fallback."
    )
    parser.add_argument("--skip-retry", action="store_true", help="Skip retry demo.")
    parser.add_argument("--skip-circuit", action="store_true", help="Skip circuit breaker demo.")
    parser.add_argument("--skip-fallback", action="store_true", help="Skip fallback demo.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run error recovery pattern demos."""
    args = parse_args(argv)
    run_demo(
        skip_retry=args.skip_retry,
        skip_circuit=args.skip_circuit,
        skip_fallback=args.skip_fallback,
    )


if __name__ == "__main__":
    main()
