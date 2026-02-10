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
        """Initialize the rate limiter.

        Args:
            key_func: Callable that extracts a rate-limit key from a ``Request``
                (e.g. client IP address).
            limits: List of rate limit strings (e.g. ``["10/second;100/minute"]``).
                Defaults to ``DEFAULT_RATE_LIMIT``.
            storage_uri: URI for the backing store. Defaults to a unique
                ``memory://`` store per instance.
        """
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
        """Check whether *request* is within the configured rate limits.

        Increments the hit counter for every configured limit. If **any**
        limit is exceeded, raises ``RateLimitExceeded`` with ``retry_after``
        set to the longest reset window among all exceeded limits.

        Args:
            request: The incoming FastAPI ``Request``.

        Raises:
            RateLimitExceeded: When at least one limit is exceeded.
        """
        key = self._key_func(request)
        max_retry_after = 0
        exceeded_limit: RateLimitItem | None = None

        for rate_limit in self._rate_limits:
            if not self._strategy.hit(rate_limit, key):
                window_stats = self._strategy.get_window_stats(rate_limit, key)
                # window_stats[0] is the reset timestamp (epoch seconds).
                retry_seconds = max(1, int(window_stats[0] - time.time()))
                if retry_seconds > max_retry_after:
                    max_retry_after = retry_seconds
                    exceeded_limit = rate_limit

        if exceeded_limit is not None:
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded: {exceeded_limit}",
                retry_after=max_retry_after,
                limit=str(exceeded_limit),
            )

    def test(self, request: Request) -> bool:
        """Test whether *request* would be allowed (does **not** consume a hit).

        Args:
            request: The incoming FastAPI ``Request``.

        Returns:
            True if the request would be allowed under all limits.
        """
        key = self._key_func(request)
        return all(self._strategy.test(rate_limit, key) for rate_limit in self._rate_limits)

    @property
    def limits(self) -> list[RateLimitItem]:
        """Return the configured rate limits (read-only)."""
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
    """Create a new rate limiter for production use.

    Each call returns a fully independent instance with its own in-memory
    storage (``memory://``). For shared limits across workers, pass a Redis URI.

    **Multi-worker warning:** ``memory://`` storage is per-process. In
    multi-worker deployments (e.g. Gunicorn with 4 workers), effective
    rate = configured limit × workers. Use Redis for shared limits.

    Args:
        limits: Rate limit strings (e.g. ``["10/second;100/minute"]``).
            Defaults to ``DEFAULT_RATE_LIMIT``.
        key_func: Optional key extraction function. If ``None``, uses
            :func:`get_remote_address` (client IP).
        storage_uri: Optional storage URI. Defaults to unique ``memory://``.

    Returns:
        New ``ASAPRateLimiter`` instance.

    Example:
        >>> limiter = create_limiter(["100/minute"])
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
    """Create a new rate limiter for testing with isolated storage.

    Args:
        limits: Rate limit strings. Defaults to very high limit (``100000/minute``).
        key_func: Optional key extraction function. Defaults to
            :func:`get_remote_address`.

    Returns:
        New ``ASAPRateLimiter`` instance with unique in-memory storage.

    Example:
        >>> test_limiter = create_test_limiter(["100000/minute"])
    """
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
    """Client IP from request, or \"127.0.0.1\" if unavailable (slowapi replacement)."""
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
        """Return True if n tokens available and deducted, else False (rate limited)."""
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
