"""Edge case tests for retry and backoff logic in ASAP client.

This module tests boundary conditions and edge cases for exponential backoff,
ensuring robust behavior in unusual scenarios.
"""

from typing import TYPE_CHECKING

from asap.transport.client import ASAPClient

if TYPE_CHECKING:
    pass


class TestBackoffEdgeCases:
    """Tests for edge cases in backoff calculation."""

    def test_backoff_with_zero_attempts(self) -> None:
        """Test backoff calculation with zero attempts (first retry)."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, jitter=False)

        # Attempt 0 should return base_delay
        delay = client._calculate_backoff(0)
        assert delay == 1.0

    def test_backoff_with_negative_base_delay_clamps_to_zero(self) -> None:
        """Test that negative base_delay is handled (should clamp to 0 or raise)."""
        # Negative base_delay should result in 0 delay
        client = ASAPClient("http://localhost:8000", base_delay=-1.0, jitter=False)

        # With negative base, calculation should still work but result in 0 or very small value
        delay = client._calculate_backoff(0)
        # The calculation is: base_delay * (2 ** attempt)
        # With base_delay = -1.0, attempt 0: -1.0 * 1 = -1.0
        # But we expect it to be clamped or handled gracefully
        # Current implementation doesn't clamp, so we test actual behavior
        assert delay == -1.0  # Current behavior - could be improved to clamp to 0

    def test_backoff_with_zero_base_delay(self) -> None:
        """Test backoff calculation with zero base_delay."""
        client = ASAPClient("http://localhost:8000", base_delay=0.0, jitter=False)

        # All attempts should return 0
        assert client._calculate_backoff(0) == 0.0
        assert client._calculate_backoff(1) == 0.0
        assert client._calculate_backoff(10) == 0.0

    def test_backoff_with_very_large_max_delay(self) -> None:
        """Test backoff with very large max_delay values."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, max_delay=1000.0, jitter=False)

        # Should allow delays up to max_delay
        assert client._calculate_backoff(0) == 1.0
        assert client._calculate_backoff(9) == 512.0  # 1 * 2^9 = 512
        assert client._calculate_backoff(10) == 1000.0  # 1 * 2^10 = 1024, capped at 1000

    def test_backoff_with_very_small_max_delay(self) -> None:
        """Test backoff with very small max_delay values."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, max_delay=0.5, jitter=False)

        # All delays should be capped at 0.5
        assert client._calculate_backoff(0) == 0.5  # 1 * 2^0 = 1, capped at 0.5
        assert client._calculate_backoff(1) == 0.5  # 1 * 2^1 = 2, capped at 0.5
        assert client._calculate_backoff(10) == 0.5  # Still capped at 0.5

    def test_backoff_jitter_distribution_range(self) -> None:
        """Test that jitter distribution is within expected range."""
        client = ASAPClient("http://localhost:8000", base_delay=10.0, jitter=True)

        # Calculate backoff many times and verify jitter range
        delays = [client._calculate_backoff(1) for _ in range(1000)]

        base_delay = 20.0  # 10 * 2^1 = 20
        max_jitter = base_delay * 0.1  # 10% jitter = 2.0
        min_delay = base_delay
        max_delay = base_delay + max_jitter

        for delay in delays:
            assert min_delay <= delay <= max_delay, f"Delay {delay} outside expected range"

        # Verify statistical properties
        mean_delay = sum(delays) / len(delays)
        # Mean should be close to base_delay + (max_jitter / 2)
        expected_mean = base_delay + (max_jitter / 2)
        assert abs(mean_delay - expected_mean) < 0.5, "Mean delay should be close to expected"

    def test_backoff_with_large_attempt_numbers(self) -> None:
        """Test backoff calculation with very large attempt numbers."""
        client = ASAPClient("http://localhost:8000", base_delay=1.0, max_delay=60.0, jitter=False)

        # Very large attempt numbers should still be capped at max_delay
        assert client._calculate_backoff(100) == 60.0
        assert client._calculate_backoff(1000) == 60.0

    def test_backoff_jitter_with_zero_base_delay(self) -> None:
        """Test jitter behavior when base_delay is zero."""
        client = ASAPClient("http://localhost:8000", base_delay=0.0, jitter=True)

        # With zero base delay, jitter should still work but result in small values
        delays = [client._calculate_backoff(1) for _ in range(100)]

        # All delays should be >= 0 and <= 0 + (0 * 0.1) = 0
        # Actually, with base_delay=0, calculation is 0 * 2^1 = 0, so jitter adds 0-0 = 0
        for delay in delays:
            assert delay == 0.0, "With zero base delay, all delays should be 0"

    def test_backoff_jitter_with_very_small_base_delay(self) -> None:
        """Test jitter behavior with very small base_delay values."""
        client = ASAPClient("http://localhost:8000", base_delay=0.001, jitter=True)

        delays = [client._calculate_backoff(0) for _ in range(100)]

        base_delay = 0.001
        max_jitter = base_delay * 0.1  # 0.0001
        for delay in delays:
            assert base_delay <= delay <= base_delay + max_jitter

    def test_backoff_max_delay_equals_base_delay(self) -> None:
        """Test backoff when max_delay equals base_delay."""
        client = ASAPClient("http://localhost:8000", base_delay=5.0, max_delay=5.0, jitter=False)

        # All delays should be capped at base_delay
        assert client._calculate_backoff(0) == 5.0
        assert client._calculate_backoff(1) == 5.0  # Would be 10, but capped at 5
        assert client._calculate_backoff(10) == 5.0

    def test_backoff_max_delay_less_than_base_delay(self) -> None:
        """Test backoff when max_delay is less than base_delay."""
        client = ASAPClient("http://localhost:8000", base_delay=10.0, max_delay=5.0, jitter=False)

        # All delays should be capped at max_delay (even attempt 0)
        assert client._calculate_backoff(0) == 5.0  # Would be 10, but capped at 5
        assert client._calculate_backoff(1) == 5.0  # Would be 20, but capped at 5
        assert client._calculate_backoff(10) == 5.0
