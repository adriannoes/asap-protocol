"""Rate limiting for ASAP protocol transport layer.

This module provides:
    - **HTTP rate limiting**: ``ASAPRateLimiter`` wraps the ``limits`` package to enforce
      per-key (IP/sender) rate limits on FastAPI endpoints. Replaces the deprecated
      ``slowapi`` dependency to eliminate ``asyncio.iscoroutinefunction`` warnings
      (Python 3.12+).
    - **WebSocket rate limiting**: ``WebSocketTokenBucket`` provides a per-connection
      token bucket for message rate limiting after the HTTP upgrade.

HTTP rate limiting storage:
    Default is ``memory://`` (per-process). In multi-worker deployments (e.g. Gunicorn
    with 4 workers) the effective rate is approximately limit × number of workers.
    For shared limits in production, use a Redis URI (planned for v1.2.0).

Public exports:
    ASAPRateLimiter: HTTP rate limiter using ``limits`` package.
    RateLimitExceeded: Exception raised when a rate limit is exceeded.
    WebSocketTokenBucket: Per-connection token bucket for WebSocket messages.
    DEFAULT_WS_MESSAGES_PER_SECOND: Default WebSocket message rate.
    create_limiter: Factory for production rate limiters.
    create_test_limiter: Factory for test rate limiters (isolated storage).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Sequence

from fastapi import Request
from limits import RateLimitItem, parse_many
from limits.storage import MemoryStorage, Storage
from limits.strategies import MovingWindowRateLimiter

from asap.observability import get_logger

logger = get_logger(__name__)

# Default rate limit: burst + sustained (token bucket pattern).
DEFAULT_RATE_LIMIT = "10/second;100/minute"


class RateLimitExceeded(Exception):
    """Raised when a rate limit is exceeded.

    Drop-in replacement for ``slowapi.errors.RateLimitExceeded``.

    Attributes:
        detail: Human-readable description of the exceeded limit.
        retry_after: Seconds until the client may retry.
        limit: String representation of the limit that was hit.
    """

    def __init__(
        self,
        detail: str,
        *,
        retry_after: int = 60,
        limit: str = "",
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after
        self.limit = limit


class ASAPRateLimiter:
    """HTTP rate limiter backed by the ``limits`` package.

    Replaces ``slowapi.Limiter`` with a simpler, deprecation-free implementation.
    Each instance owns its own ``Storage`` so multiple app instances have
    independent counters (unless a shared Redis URI is provided).

    Example:
        >>> limiter = ASAPRateLimiter(
        ...     key_func=lambda req: req.client.host,
        ...     limits=["10/second;100/minute"],
        ... )
        >>> # In a FastAPI route:
        >>> limiter.check(request)  # raises RateLimitExceeded on 429
    """

    def __init__(
        self,
        *,
        key_func: Callable[[Request], str],
        limits: list[str] | None = None,
        storage_uri: str | None = None,
    ) -> None:
        self._key_func = key_func

        limit_strings = limits or [DEFAULT_RATE_LIMIT]
        self._rate_limits: list[RateLimitItem] = []
        for limit_str in limit_strings:
            self._rate_limits.extend(parse_many(limit_str))

        if storage_uri is None:
            storage_uri = f"memory://{uuid.uuid4().hex}"

        self._storage: Storage = MemoryStorage(uri=storage_uri)
        self._strategy = MovingWindowRateLimiter(self._storage)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, request: Request) -> None:
        """Raise ``RateLimitExceeded`` if *request* violates any configured limit.

        Two-phase approach: test all limits (read-only) first, then hit all
        counters only if every limit passes. Prevents double-counting drift.
        """
        key = self._key_func(request)

        # Phase 1: Test all limits without consuming hits.
        for rate_limit in self._rate_limits:
            if not self._strategy.test(rate_limit, key):
                window_stats = self._strategy.get_window_stats(rate_limit, key)
                # window_stats[0] is the reset timestamp (epoch seconds).
                retry_seconds = max(1, int(window_stats[0] - time.time()))
                raise RateLimitExceeded(
                    detail=f"Rate limit exceeded: {rate_limit}",
                    retry_after=retry_seconds,
                    limit=str(rate_limit),
                )

        # Phase 2: All limits pass — now increment all counters.
        for rate_limit in self._rate_limits:
            self._strategy.hit(rate_limit, key)

    def test(self, request: Request) -> bool:
        """Return True if *request* would pass all limits (no counter increment)."""
        key = self._key_func(request)
        return all(self._strategy.test(rate_limit, key) for rate_limit in self._rate_limits)

    @property
    def limits(self) -> list[RateLimitItem]:
        return list(self._rate_limits)


# ------------------------------------------------------------------
# Factory functions (backward-compatible with previous slowapi API)
# ------------------------------------------------------------------


def create_limiter(
    limits: Sequence[str] | None = None,
    *,
    key_func: Callable[[Request], str] | None = None,
    storage_uri: str | None = None,
) -> ASAPRateLimiter:
    """Create a production rate limiter.

    Returns a fully independent instance with its own storage.
    ``memory://`` is per-process; use a Redis URI for shared limits across workers.
    """
    if key_func is None:
        key_func = get_remote_address

    if limits is None:
        limits = [DEFAULT_RATE_LIMIT]

    if storage_uri is None:
        storage_uri = f"memory://{uuid.uuid4().hex}"
        logger.warning(
            "asap.rate_limit.memory_storage",
            message=(
                "memory:// storage is per-process; in multi-worker deployments "
                "(e.g. Gunicorn), effective rate = limit × workers. Use Redis for shared limits."
            ),
        )

    return ASAPRateLimiter(
        key_func=key_func,
        limits=list(limits),
        storage_uri=storage_uri,
    )


def create_test_limiter(
    limits: Sequence[str] | None = None,
    *,
    key_func: Callable[[Request], str] | None = None,
) -> ASAPRateLimiter:
    """Create a rate limiter for testing with isolated ``memory://`` storage."""
    if key_func is None:
        key_func = get_remote_address

    if limits is None:
        limits = ["100000/minute"]

    return ASAPRateLimiter(
        key_func=key_func,
        limits=list(limits),
        storage_uri=f"memory://test-{uuid.uuid4().hex}",
    )


def get_remote_address(request: Request) -> str:
    if request.client is not None:
        return str(request.client.host)
    return "127.0.0.1"


# ------------------------------------------------------------------
# WebSocket token bucket (unchanged from previous implementation)
# ------------------------------------------------------------------

DEFAULT_WS_MESSAGES_PER_SECOND = 10.0


class WebSocketTokenBucket:
    """Per-connection token bucket: refill at rate/sec, one token per message. Not thread-safe."""

    __slots__ = ("_rate", "_capacity", "_tokens", "_last_refill")

    def __init__(
        self,
        rate: float = DEFAULT_WS_MESSAGES_PER_SECOND,
        capacity: float | None = None,
    ) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        self._rate = float(rate)
        self._capacity = float(capacity if capacity is not None else rate)
        self._tokens = self._capacity
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """First call may grant full capacity if bucket was created long before first message."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._capacity,
            self._tokens + elapsed * self._rate,
        )
        self._last_refill = now

    def consume(self, n: int = 1) -> bool:
        if n <= 0:
            return True
        self._refill()
        if self._tokens >= n:
            self._tokens -= n
            return True
        return False

    @property
    def rate(self) -> float:
        return self._rate


__all__ = [
    # HTTP rate limiting
    "ASAPRateLimiter",
    "RateLimitExceeded",
    "DEFAULT_RATE_LIMIT",
    "create_limiter",
    "create_test_limiter",
    "get_remote_address",
    # WebSocket rate limiting
    "DEFAULT_WS_MESSAGES_PER_SECOND",
    "WebSocketTokenBucket",
]
