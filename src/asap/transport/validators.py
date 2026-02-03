"""Validation utilities for ASAP protocol envelopes.

This module provides validation functions for envelope security checks,
including timestamp validation for replay attack prevention and optional
nonce validation for duplicate detection.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

from asap.errors import InvalidNonceError, InvalidTimestampError
from asap.models.constants import (
    MAX_ENVELOPE_AGE_SECONDS,
    MAX_FUTURE_TOLERANCE_SECONDS,
    NONCE_TTL_SECONDS,
)
from asap.models.envelope import Envelope


def validate_envelope_timestamp(envelope: Envelope) -> None:
    """Validate envelope timestamp to prevent replay attacks.

    Checks that the envelope timestamp is:
    - Not older than MAX_ENVELOPE_AGE_SECONDS (default: 5 minutes)
    - Not more than MAX_FUTURE_TOLERANCE_SECONDS in the future (default: 30 seconds)

    Args:
        envelope: The envelope to validate

    Raises:
        InvalidTimestampError: If the timestamp is too old or too far in the future

    Example:
        >>> from asap.models.envelope import Envelope
        >>> from asap.transport.validators import validate_envelope_timestamp
        >>>
        >>> # Recent envelope passes
        >>> recent = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:test",
        ...     recipient="urn:asap:agent:test",
        ...     payload_type="TaskRequest",
        ...     payload={}
        ... )
        >>> validate_envelope_timestamp(recent)  # No exception
        >>>
        >>> # Old envelope raises error
        >>> from datetime import datetime, timezone, timedelta
        >>> old = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:test",
        ...     recipient="urn:asap:agent:test",
        ...     payload_type="TaskRequest",
        ...     payload={},
        ...     timestamp=datetime.now(timezone.utc) - timedelta(minutes=10)
        ... )
        >>> validate_envelope_timestamp(old)  # Raises InvalidTimestampError
    """
    if envelope.timestamp is None:
        raise InvalidTimestampError(
            timestamp="",
            message="Envelope timestamp is required for validation",
            details={"envelope_id": envelope.id},
        )

    now = datetime.now(timezone.utc)
    timestamp = envelope.timestamp

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        # Convert to UTC if needed
        timestamp = timestamp.astimezone(timezone.utc)

    # Calculate age in seconds
    age_seconds = (now - timestamp).total_seconds()

    if age_seconds > MAX_ENVELOPE_AGE_SECONDS:
        raise InvalidTimestampError(
            timestamp=timestamp.isoformat(),
            message=(
                f"Envelope timestamp is too old: {age_seconds:.1f} seconds "
                f"(max: {MAX_ENVELOPE_AGE_SECONDS} seconds)"
            ),
            age_seconds=age_seconds,
            details={
                "envelope_id": envelope.id,
                "max_age_seconds": MAX_ENVELOPE_AGE_SECONDS,
            },
        )

    future_offset_seconds = (timestamp - now).total_seconds()
    if future_offset_seconds > MAX_FUTURE_TOLERANCE_SECONDS:
        raise InvalidTimestampError(
            timestamp=timestamp.isoformat(),
            message=(
                f"Envelope timestamp is too far in the future: "
                f"{future_offset_seconds:.1f} seconds "
                f"(max tolerance: {MAX_FUTURE_TOLERANCE_SECONDS} seconds)"
            ),
            future_offset_seconds=future_offset_seconds,
            details={
                "envelope_id": envelope.id,
                "max_future_tolerance_seconds": MAX_FUTURE_TOLERANCE_SECONDS,
            },
        )


@runtime_checkable
class NonceStore(Protocol):
    """Protocol for nonce storage and validation.

    Implementations must provide thread-safe storage and TTL-based expiration
    for nonce values to prevent replay attacks.
    """

    def is_used(self, nonce: str) -> bool:
        """Check if a nonce has been used.

        Args:
            nonce: The nonce value to check

        Returns:
            True if the nonce has been used, False otherwise
        """
        ...

    def mark_used(self, nonce: str, ttl_seconds: int) -> None:
        """Mark a nonce as used with a TTL.

        Args:
            nonce: The nonce value to mark as used
            ttl_seconds: Time-to-live in seconds for the nonce
        """
        ...

    def check_and_mark(self, nonce: str, ttl_seconds: int) -> bool:
        """Atomically check if nonce is used and mark it if not.

        This method performs both check and mark operations atomically to
        prevent race conditions between concurrent requests.

        Args:
            nonce: The nonce value to check and mark
            ttl_seconds: Time-to-live in seconds for the nonce

        Returns:
            True if nonce was already used, False if it was newly marked
        """
        ...


class InMemoryNonceStore:
    """In-memory nonce store with TTL-based expiration.

    This implementation uses a dictionary to store nonces with their
    expiration times. Expired nonces are lazily cleaned up on access.

    Attributes:
        _store: Dictionary mapping nonce to expiration timestamp
        _lock: Thread lock for thread-safe operations
    """

    def __init__(self) -> None:
        """Initialize in-memory nonce store."""
        self._store: dict[str, float] = {}
        self._lock = threading.RLock()

    def _cleanup_expired(self) -> None:
        """Remove expired nonces from the store.

        This is called lazily during access operations to keep the store
        from growing unbounded.
        """
        now = time.time()
        expired = [nonce for nonce, expiry in self._store.items() if expiry < now]
        for nonce in expired:
            self._store.pop(nonce, None)

    def is_used(self, nonce: str) -> bool:
        """Check if a nonce has been used.

        Args:
            nonce: The nonce value to check

        Returns:
            True if the nonce has been used and not expired, False otherwise
        """
        with self._lock:
            self._cleanup_expired()
            if nonce not in self._store:
                return False
            expiry = self._store[nonce]
            return expiry >= time.time()

    def mark_used(self, nonce: str, ttl_seconds: int) -> None:
        """Mark a nonce as used with a TTL.

        Args:
            nonce: The nonce value to mark as used
            ttl_seconds: Time-to-live in seconds for the nonce
        """
        with self._lock:
            self._cleanup_expired()
            expiry = time.time() + ttl_seconds
            self._store[nonce] = expiry

    def check_and_mark(self, nonce: str, ttl_seconds: int) -> bool:
        """Atomically check if nonce is used and mark it if not.

        This method performs both check and mark operations atomically to
        prevent race conditions between concurrent requests with the same nonce.

        Args:
            nonce: The nonce value to check and mark
            ttl_seconds: Time-to-live in seconds for the nonce

        Returns:
            True if nonce was already used, False if it was newly marked
        """
        with self._lock:
            self._cleanup_expired()
            if nonce in self._store and self._store[nonce] >= time.time():
                return True  # Already used
            self._store[nonce] = time.time() + ttl_seconds
            return False  # Newly marked


def validate_envelope_nonce(envelope: Envelope, nonce_store: NonceStore | None) -> None:
    """Validate envelope nonce to prevent duplicate message replay.

    If the envelope has a nonce in its extensions, checks that it hasn't
    been used before. If no nonce is present, validation passes (nonce
    is optional). If a nonce_store is not provided, validation is skipped.

    Args:
        envelope: The envelope to validate
        nonce_store: Optional nonce store for duplicate detection

    Raises:
        InvalidNonceError: If the nonce has been used before

    Example:
        >>> from asap.models.envelope import Envelope
        >>> from asap.transport.validators import (
        ...     validate_envelope_nonce,
        ...     InMemoryNonceStore
        ... )
        >>>
        >>> store = InMemoryNonceStore()
        >>>
        >>> # Envelope without nonce passes
        >>> envelope1 = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:test",
        ...     recipient="urn:asap:agent:test",
        ...     payload_type="TaskRequest",
        ...     payload={}
        ... )
        >>> validate_envelope_nonce(envelope1, store)  # No exception
        >>>
        >>> # First use of nonce passes
        >>> envelope2 = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:test",
        ...     recipient="urn:asap:agent:test",
        ...     payload_type="TaskRequest",
        ...     payload={},
        ...     extensions={"nonce": "unique-nonce-123"}
        ... )
        >>> validate_envelope_nonce(envelope2, store)  # No exception
        >>>
        >>> # Duplicate nonce raises error
        >>> envelope3 = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:test",
        ...     recipient="urn:asap:agent:test",
        ...     payload_type="TaskRequest",
        ...     payload={},
        ...     extensions={"nonce": "unique-nonce-123"}
        ... )
        >>> validate_envelope_nonce(envelope3, store)  # Raises InvalidNonceError
    """
    # Skip validation if no nonce store provided
    if nonce_store is None:
        return

    # Skip validation if no nonce in extensions
    if not envelope.extensions or "nonce" not in envelope.extensions:
        return

    nonce = envelope.extensions["nonce"]

    if not isinstance(nonce, str) or not nonce:
        raise InvalidNonceError(
            nonce=str(nonce),
            message=(
                f"Nonce must be a non-empty string, got "
                f"{type(nonce).__name__ if not isinstance(nonce, str) else 'empty string'}"
            ),
            details={"envelope_id": envelope.id},
        )

    # Atomically check and mark nonce as used to prevent race conditions
    if nonce_store.check_and_mark(nonce, ttl_seconds=NONCE_TTL_SECONDS):
        raise InvalidNonceError(
            nonce=nonce,
            message=f"Duplicate nonce detected: {nonce}",
            details={"envelope_id": envelope.id},
        )


__all__ = [
    "NonceStore",
    "InMemoryNonceStore",
    "validate_envelope_timestamp",
    "validate_envelope_nonce",
]
