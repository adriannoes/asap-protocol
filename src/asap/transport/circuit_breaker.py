"""Circuit breaker implementation for resilient request handling.

This module provides the CircuitBreaker pattern implementation and a registry
for sharing circuit breaker state across multiple client instances.
"""

import threading
import time
from enum import Enum

from asap.models.constants import (
    DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
)
from asap.observability import get_logger

logger = get_logger(__name__)


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

        Increments failure count and opens circuit if threshold is reached
        or if the circuit was in HALF_OPEN state.
        """
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()

            threshold_reached = (
                self._consecutive_failures >= self.threshold and self._state == CircuitState.CLOSED
            )

            if self._state == CircuitState.HALF_OPEN or threshold_reached:
                self._state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        """Check if a request can be attempted.

        Returns:
            True if request can be attempted, False if circuit is open
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                if self._last_failure_time is not None:
                    elapsed = time.time() - self._last_failure_time
                    if elapsed >= self.timeout:
                        self._state = CircuitState.HALF_OPEN
                        return True
                return False

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


class CircuitBreakerRegistry:
    """Registry for managing shared CircuitBreaker instances.

    Ensures that multiple clients connecting to the same implementation
    share the same circuit breaker state.
    """

    def __init__(self) -> None:
        """Initialize registry."""
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()

    def get_or_create(
        self,
        base_url: str,
        threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create a new one.

        Args:
            base_url: The target URL (key for the registry)
            threshold: Threshold for new breakers (ignored if exists)
            timeout: Timeout for new breakers (ignored if exists)

        Returns:
            Shared CircuitBreaker instance
        """
        with self._lock:
            if base_url not in self._breakers:
                logger.info(
                    "asap.circuit_breaker.created",
                    base_url=base_url,
                    threshold=threshold,
                    timeout=timeout,
                    message=f"Created shared circuit breaker for {base_url}",
                )
                self._breakers[base_url] = CircuitBreaker(threshold=threshold, timeout=timeout)
            return self._breakers[base_url]

    def clear(self) -> None:
        """Clear all registered circuit breakers (mostly for testing)."""
        with self._lock:
            self._breakers.clear()


# Global registry instance
# In a more complex app, this might be injected, but a module-level singleton
# is standard for this pattern in Python clients.
# WARNING: This state persists across tests. Use get_registry().clear() in tearDown.
_registry = CircuitBreakerRegistry()


def get_circuit_breaker(
    base_url: str,
    threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
    timeout: float = DEFAULT_CIRCUIT_BREAKER_TIMEOUT,
) -> CircuitBreaker:
    """Helper to get a circuit breaker from the global registry."""
    return _registry.get_or_create(base_url, threshold, timeout)


def get_registry() -> CircuitBreakerRegistry:
    """Helper to get the global registry instance."""
    return _registry
