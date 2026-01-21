"""Run the ASAP two-agent demo.

This script starts the echo agent and coordinator agent as subprocesses.
It is the foundation for the full demo flow implemented in later tasks.
"""

import signal
import subprocess
import sys
import time
from typing import Sequence

import httpx

ECHO_MANIFEST_URL = "http://127.0.0.1:8001/.well-known/asap/manifest.json"
COORDINATOR_MANIFEST_URL = "http://127.0.0.1:8000/.well-known/asap/manifest.json"
READY_TIMEOUT_SECONDS = 10.0
READY_POLL_INTERVAL_SECONDS = 0.5

ECHO_AGENT_MODULE = "asap.examples.echo_agent"
COORDINATOR_MODULE = "asap.examples.coordinator"


def start_process(command: Sequence[str]) -> subprocess.Popen[str]:
    """Start a subprocess and return its handle.

    Args:
        command: Command to execute as a sequence.

    Returns:
        Started subprocess handle.
    """
    return subprocess.Popen(command, text=True)


def wait_for_ready(url: str, timeout_seconds: float) -> None:
    """Wait for the given URL to respond with HTTP 200.

    Args:
        url: The URL to poll for readiness.
        timeout_seconds: Maximum time to wait before failing.

    Raises:
        RuntimeError: If the service does not become ready in time.
    """
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(READY_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Service not ready after {timeout_seconds:.1f}s: {url}")


def _terminate_process(process: subprocess.Popen[str] | None) -> None:
    """Terminate a subprocess if it is still running."""
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


def main() -> None:
    """Start demo agent processes (echo + coordinator)."""
    echo_command = [sys.executable, "-m", ECHO_AGENT_MODULE]
    coordinator_command = [sys.executable, "-m", COORDINATOR_MODULE]

    echo_process = None
    coordinator_process = None

    def handle_signal(signum: int, _frame: object) -> None:
        """Handle shutdown signals by terminating child processes."""
        signal_name = signal.Signals(signum).name
        raise RuntimeError(f"Shutdown requested ({signal_name})")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        echo_process = start_process(echo_command)
        wait_for_ready(ECHO_MANIFEST_URL, READY_TIMEOUT_SECONDS)
        coordinator_process = start_process(coordinator_command)
        wait_for_ready(COORDINATOR_MANIFEST_URL, READY_TIMEOUT_SECONDS)
        echo_process.wait()
        coordinator_process.wait()
    finally:
        _terminate_process(coordinator_process)
        _terminate_process(echo_process)


if __name__ == "__main__":
    main()
