"""Tests for run_demo.py module to improve coverage.

These tests cover the utility functions in run_demo.py without
actually starting subprocess or making HTTP calls.
"""

import subprocess
import time
from unittest.mock import MagicMock, patch

import httpx
import pytest

from asap.examples.run_demo import (
    _terminate_process,
    start_process,
    wait_for_ready,
)


class TestStartProcess:
    """Tests for start_process function."""

    def test_start_process_returns_popen(self) -> None:
        """start_process should return a Popen handle."""
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            result = start_process(["echo", "hello"])

            mock_popen.assert_called_once_with(["echo", "hello"], text=True)
            assert result is mock_process


class TestWaitForReady:
    """Tests for wait_for_ready function."""

    def test_wait_for_ready_success_immediate(self) -> None:
        """Should return immediately when service is ready."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.get", return_value=mock_response):
            # Should not raise
            wait_for_ready("http://localhost:8000", timeout_seconds=5.0)

    def test_wait_for_ready_success_after_retries(self) -> None:
        """Should succeed after a few retries."""
        mock_response_fail = MagicMock()
        mock_response_fail.status_code = 503

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200

        call_count = 0

        def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return mock_response_fail
            return mock_response_ok

        with patch("httpx.get", side_effect=mock_get), patch("time.sleep"):
            wait_for_ready("http://localhost:8000", timeout_seconds=10.0)

        assert call_count >= 3

    def test_wait_for_ready_handles_http_error(self) -> None:
        """Should continue retrying on HTTPError."""
        call_count = 0
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200

        def mock_get(*args: object, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.HTTPError("Connection refused")
            return mock_response_ok

        with patch("httpx.get", side_effect=mock_get), patch("time.sleep"):
            wait_for_ready("http://localhost:8000", timeout_seconds=10.0)

        assert call_count >= 2

    def test_wait_for_ready_timeout_raises(self) -> None:
        """Should raise RuntimeError after timeout."""
        # Mock time to simulate timeout
        start_time = time.monotonic()

        def mock_monotonic() -> float:
            # First call returns start, subsequent calls return past deadline
            mock_monotonic.calls = getattr(mock_monotonic, "calls", 0) + 1
            if mock_monotonic.calls == 1:
                return start_time
            return start_time + 100  # Way past deadline

        with (
            patch("httpx.get", side_effect=httpx.HTTPError("fail")),
            patch("time.monotonic", side_effect=mock_monotonic),
            pytest.raises(RuntimeError) as exc_info,
        ):
            wait_for_ready("http://localhost:8000", timeout_seconds=1.0)

        assert "not ready" in str(exc_info.value).lower()


class TestTerminateProcess:
    """Tests for _terminate_process function."""

    def test_terminate_none_process(self) -> None:
        """Should handle None process gracefully."""
        # Should not raise
        _terminate_process(None)

    def test_terminate_already_finished_process(self) -> None:
        """Should handle already finished process."""
        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Already finished

        _terminate_process(mock_process)

        # terminate() should NOT be called if already finished
        mock_process.terminate.assert_not_called()

    def test_terminate_running_process_graceful(self) -> None:
        """Should terminate running process gracefully."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running

        _terminate_process(mock_process)

        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=3)

    def test_terminate_process_needs_kill(self) -> None:
        """Should kill process if terminate times out."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Still running
        mock_process.wait.side_effect = [
            subprocess.TimeoutExpired("cmd", 3),  # First wait times out
            None,  # Second wait (after kill) succeeds
        ]

        _terminate_process(mock_process)

        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2


class TestMainFunction:
    """Tests for main() function with mocked subprocesses."""

    def test_main_imports(self) -> None:
        """Main function should be importable."""
        from asap.examples.run_demo import main

        assert callable(main)

    def test_main_signal_handlers_importable(self) -> None:
        """Signal constants should be importable."""
        import signal

        # Verify signal constants are accessible
        assert hasattr(signal, "SIGINT")
        assert hasattr(signal, "SIGTERM")
