"""Tests for validators module edge cases to improve coverage.

These tests cover:
- Line 61: Envelope with None timestamp
- Line 72: Timezone conversion for naive timestamps
"""

from datetime import datetime, timezone

import pytest

from asap.errors import InvalidNonceError, InvalidTimestampError
from asap.models.envelope import Envelope
from asap.transport.validators import (
    InMemoryNonceStore,
    validate_envelope_nonce,
    validate_envelope_timestamp,
)


class TestTimestampValidationEdgeCases:
    """Tests for timestamp validation edge cases."""

    def test_envelope_without_timestamp_raises_error(self) -> None:
        """Line 61: None timestamp should raise InvalidTimestampError."""
        # Create envelope and manually set timestamp to None
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:target",
            payload_type="TaskRequest",
            payload={"skill_id": "test", "conversation_id": "conv_1", "input": {}},
        )
        # Force timestamp to None (normally auto-generated)
        object.__setattr__(envelope, "timestamp", None)

        with pytest.raises(InvalidTimestampError) as exc_info:
            validate_envelope_timestamp(envelope)

        assert "timestamp is required" in str(exc_info.value).lower()

    def test_naive_timestamp_treated_as_utc(self) -> None:
        """Line 72: Naive timestamps should be treated as UTC."""
        # Create envelope with naive (no timezone) timestamp that's recent in UTC
        # We create a naive timestamp by removing tzinfo from a UTC datetime
        naive_timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:target",
            payload_type="TaskRequest",
            payload={"skill_id": "test", "conversation_id": "conv_1", "input": {}},
            timestamp=naive_timestamp,
        )

        # Should not raise - naive timestamp treated as UTC
        validate_envelope_timestamp(envelope)

    def test_non_utc_timezone_converted(self) -> None:
        """Non-UTC timezone timestamps should be properly converted."""
        from datetime import timedelta

        # Create a timestamp in a different timezone (e.g., UTC+5)
        custom_tz = timezone(timedelta(hours=5))
        non_utc_timestamp = datetime.now(custom_tz)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:target",
            payload_type="TaskRequest",
            payload={"skill_id": "test", "conversation_id": "conv_1", "input": {}},
            timestamp=non_utc_timestamp,
        )

        # Should not raise - timezone is converted to UTC
        validate_envelope_timestamp(envelope)


class TestNonceValidationEdgeCases:
    """Tests for nonce validation edge cases."""

    def test_nonce_non_string_raises_error(self) -> None:
        """Non-string nonce values should raise InvalidNonceError."""
        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:target",
            payload_type="TaskRequest",
            payload={"skill_id": "test", "conversation_id": "conv_1", "input": {}},
            extensions={"nonce": 12345},  # Integer instead of string
        )

        with pytest.raises(InvalidNonceError) as exc_info:
            validate_envelope_nonce(envelope, store)

        assert "must be a non-empty string" in str(exc_info.value).lower()

    def test_nonce_none_value_raises_error(self) -> None:
        """None nonce value should raise InvalidNonceError."""
        store = InMemoryNonceStore()
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient="urn:asap:agent:target",
            payload_type="TaskRequest",
            payload={"skill_id": "test", "conversation_id": "conv_1", "input": {}},
            extensions={"nonce": None},
        )

        with pytest.raises(InvalidNonceError) as exc_info:
            validate_envelope_nonce(envelope, store)

        assert "must be a non-empty string" in str(exc_info.value).lower()
