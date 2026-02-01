"""Tests for ULID-based ID generation."""

import asyncio
from datetime import datetime, timezone

import pytest

from asap.models.ids import extract_timestamp, generate_id


class TestGenerateId:
    """Test suite for generate_id() function."""

    def test_returns_valid_ulid_string(self):
        """Test that generate_id() returns a valid ULID string of 26 characters."""
        ulid = generate_id()

        assert isinstance(ulid, str), "ULID should be a string"
        assert len(ulid) == 26, "ULID should be exactly 26 characters"
        # ULID uses Crockford's base32 alphabet (0-9, A-Z excluding I, L, O, U)
        valid_chars = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
        assert all(c in valid_chars for c in ulid), "ULID contains invalid characters"

    def test_uniqueness_across_multiple_calls(self):
        """Test that multiple calls to generate_id() produce unique IDs."""
        # Generate 1000 IDs to test uniqueness
        ids = [generate_id() for _ in range(1000)]

        # All IDs should be unique
        assert len(ids) == len(set(ids)), "Generated IDs should be unique"

    async def test_ids_are_sortable_when_timestamps_differ(self):
        """Test that IDs generated in different milliseconds are lexicographically ordered.

        ULID guarantees lexicographic order by creation time only when timestamps
        (millisecond precision) differ. Within the same millisecond, the random
        component can break order. We enforce a 2ms gap so timestamps differ.
        """
        id_before = generate_id()
        await asyncio.sleep(0.002)  # Ensure different millisecond
        id_after = generate_id()

        assert id_before < id_after, (
            "ULIDs with different timestamps should be lexicographically ordered"
        )
        ts_before = extract_timestamp(id_before)
        ts_after = extract_timestamp(id_after)
        assert ts_before <= ts_after, "Extracted timestamps should reflect generation order"


class TestExtractTimestamp:
    """Test suite for extract_timestamp() function."""

    def test_extracts_timestamp_from_ulid(self):
        """Test that extract_timestamp() correctly extracts the timestamp from a ULID."""
        # Generate a ULID
        ulid = generate_id()

        # Extract timestamp
        timestamp = extract_timestamp(ulid)

        # Should be a datetime object
        assert isinstance(timestamp, datetime), "Extracted timestamp should be a datetime"

        # Should be timezone-aware (UTC)
        assert timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
        assert timestamp.tzinfo == timezone.utc, "Timestamp should be in UTC"

        # Should be close to current time (within 1 second)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - timestamp).total_seconds())
        assert time_diff < 1.0, "Extracted timestamp should be close to current time"

    def test_timestamp_consistency(self):
        """Test that the timestamp extracted matches the generation time."""
        before = datetime.now(timezone.utc)
        ulid = generate_id()
        after = datetime.now(timezone.utc)

        timestamp = extract_timestamp(ulid)

        # ULID timestamps have millisecond precision, so we need a small tolerance
        # The timestamp should be within 1ms of the generation window
        tolerance_ms = 1  # millisecond
        assert (before - timestamp).total_seconds() * 1000 <= tolerance_ms, (
            "Timestamp should not be before the generation window (accounting for ms precision)"
        )
        assert (timestamp - after).total_seconds() * 1000 <= tolerance_ms, (
            "Timestamp should not be after the generation window (accounting for ms precision)"
        )

    def test_invalid_ulid_raises_error(self):
        """Test that extract_timestamp() raises an error for invalid ULIDs."""
        with pytest.raises((ValueError, AttributeError)):
            extract_timestamp("invalid-ulid")

        with pytest.raises((ValueError, AttributeError)):
            extract_timestamp("TOO_SHORT")

        with pytest.raises((ValueError, AttributeError)):
            extract_timestamp("THIS_IS_WAY_TOO_LONG_FOR_A_ULID")
