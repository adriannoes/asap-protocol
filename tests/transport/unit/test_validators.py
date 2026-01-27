"""Unit tests for ASAP protocol envelope validators.

This module tests timestamp and nonce validation functions in isolation,
without HTTP dependencies or rate limiting.
"""

from datetime import datetime, timezone, timedelta

import pytest

from asap.errors import InvalidNonceError, InvalidTimestampError
from asap.models.envelope import Envelope
from asap.transport.validators import (
    InMemoryNonceStore,
    validate_envelope_nonce,
    validate_envelope_timestamp,
)


class TestTimestampValidation:
    """Tests for envelope timestamp validation."""

    def test_recent_timestamp_accepted(self) -> None:
        """Test that recent timestamps are accepted."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            timestamp=datetime.now(timezone.utc),
        )

        # Should not raise
        validate_envelope_timestamp(envelope)

    def test_old_timestamp_rejected(self) -> None:
        """Test that timestamps older than 5 minutes are rejected."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        with pytest.raises(InvalidTimestampError) as exc_info:
            validate_envelope_timestamp(envelope)

        assert "too old" in exc_info.value.message.lower()
        assert exc_info.value.age_seconds is not None
        assert exc_info.value.age_seconds > 300  # More than 5 minutes

    def test_future_timestamp_rejected(self) -> None:
        """Test that timestamps more than 30 seconds in the future are rejected."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            timestamp=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        with pytest.raises(InvalidTimestampError) as exc_info:
            validate_envelope_timestamp(envelope)

        assert "too far in the future" in exc_info.value.message.lower()
        assert exc_info.value.future_offset_seconds is not None
        assert exc_info.value.future_offset_seconds > 30

    def test_timestamps_within_tolerance_accepted(self) -> None:
        """Test that timestamps within tolerance windows are accepted."""
        # Test timestamp 4 minutes old (within 5 minute window)
        envelope_old = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=4),
        )
        validate_envelope_timestamp(envelope_old)  # Should not raise

        # Test timestamp 20 seconds in the future (within 30 second tolerance)
        envelope_future = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            timestamp=datetime.now(timezone.utc) + timedelta(seconds=20),
        )
        validate_envelope_timestamp(envelope_future)  # Should not raise

    def test_auto_generated_timestamp_accepted(self) -> None:
        """Test that envelopes with auto-generated timestamps are accepted."""
        # Create envelope without explicit timestamp (will auto-generate)
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
        )

        # Auto-generated timestamp should be recent and pass validation
        assert envelope.timestamp is not None
        validate_envelope_timestamp(envelope)  # Should not raise


class TestNonceValidation:
    """Tests for envelope nonce validation."""

    def test_no_nonce_passes(self) -> None:
        """Test that envelopes without nonce pass validation."""
        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
        )

        # Should not raise
        validate_envelope_nonce(envelope, store)

    def test_no_nonce_store_passes(self) -> None:
        """Test that validation passes when no nonce store is provided."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": "test-nonce-123"},
        )

        # Should not raise when nonce_store is None
        validate_envelope_nonce(envelope, None)

    def test_first_nonce_use_passes(self) -> None:
        """Test that first use of a nonce passes and marks it as used."""
        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": "unique-nonce-123"},
        )

        # First use should pass
        validate_envelope_nonce(envelope, store)

        # Verify nonce is marked as used
        assert store.is_used("unique-nonce-123")

    def test_duplicate_nonce_rejected(self) -> None:
        """Test that duplicate nonces are rejected."""
        store = InMemoryNonceStore()
        envelope1 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": "duplicate-nonce-456"},
        )

        envelope2 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": "duplicate-nonce-456"},
        )

        # First use should pass
        validate_envelope_nonce(envelope1, store)

        # Second use should raise error
        with pytest.raises(InvalidNonceError) as exc_info:
            validate_envelope_nonce(envelope2, store)

        assert "duplicate nonce" in exc_info.value.message.lower()
        assert exc_info.value.nonce == "duplicate-nonce-456"

    def test_expired_nonce_allowed_again(self) -> None:
        """Test that expired nonces are allowed again after TTL expires."""
        import time

        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": "expiring-nonce-789"},
        )

        # First use should pass
        validate_envelope_nonce(envelope, store)

        # Mark with very short TTL (1 second)
        store.mark_used("expiring-nonce-789", ttl_seconds=1)

        # Wait for expiration
        time.sleep(1.1)

        # After expiration, should be allowed again
        validate_envelope_nonce(envelope, store)

    def test_invalid_nonce_type_raises_error(self) -> None:
        """Test that non-string nonces raise error."""
        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:test",
            payload_type="TaskRequest",
            payload={},
            extensions={"nonce": 12345},  # Invalid: nonce should be string
        )

        with pytest.raises(InvalidNonceError) as exc_info:
            validate_envelope_nonce(envelope, store)

        assert "must be a string" in exc_info.value.message.lower()
