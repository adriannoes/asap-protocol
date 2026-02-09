"""Token bucket for per-connection WebSocket message rate limiting.

HTTP rate limiting (middleware) does not apply once a WebSocket connection
is established. One bucket per connection in handle_websocket_connection.
"""

import time


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
    "DEFAULT_WS_MESSAGES_PER_SECOND",
    "WebSocketTokenBucket",
]
