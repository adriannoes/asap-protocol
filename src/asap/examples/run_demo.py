"""Run the ASAP two-agent demo.

This script starts the echo agent as a subprocess, then demonstrates
communication by sending a task request from the coordinator logic.
"""

from __future__ import annotations

import asyncio
import signal
import subprocess  # nosec B404
import sys
import time
from typing import Sequence

import httpx

from asap.examples.coordinator import dispatch_task
from asap.observability import get_logger

ECHO_MANIFEST_URL = "http://127.0.0.1:8001/.well-known/asap/manifest.json"
ECHO_BASE_URL = "http://127.0.0.1:8001"
READY_TIMEOUT_SECONDS = 10.0
READY_POLL_INTERVAL_SECONDS = 0.5

ECHO_AGENT_MODULE = "asap.examples.echo_agent"

logger = get_logger(__name__)


def start_process(command: Sequence[str]) -> subprocess.Popen[str]:
    """Start a subprocess and return its handle.

    Args:
        command: Command to execute as a sequence.

    Returns:
        Started subprocess handle.

    Note:
        This is example/demo code that only executes trusted commands
        (sys.executable with known modules). The command is controlled
        and not user input.
    """
    # nosec B404, B603: This is example code executing trusted commands only
    # (sys.executable with known Python modules, not user input)
    return subprocess.Popen(command, text=True)  # nosec B404, B603


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
    """Start echo agent and demonstrate communication via coordinator logic."""
    echo_command = [sys.executable, "-m", ECHO_AGENT_MODULE]
    echo_process = None

    def handle_signal(signum: int, _frame: object) -> None:
        """Handle shutdown signals by terminating child processes."""
        signal_name = signal.Signals(signum).name
        raise RuntimeError(f"Shutdown requested ({signal_name})")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        echo_process = start_process(echo_command)
        wait_for_ready(ECHO_MANIFEST_URL, READY_TIMEOUT_SECONDS)
        logger.info("asap.demo.echo_ready", url=ECHO_MANIFEST_URL)

        logger.info("asap.demo.starting_communication")
        try:
            response = asyncio.run(
                dispatch_task(
                    payload={"message": "Hello from demo runner!"},
                    echo_base_url=ECHO_BASE_URL,
                )
            )
            logger.info(
                "asap.demo.communication_success",
                request_id=response.correlation_id,
                response_id=response.id,
                payload_type=response.payload_type,
            )
            print(f"\n✅ Demo successful! Response: {response.payload}\n")
        except Exception as e:
            logger.exception("asap.demo.communication_failed", error=str(e))
            print(f"\n❌ Demo failed: {e}\n")
            raise

    finally:
        _terminate_process(echo_process)


if __name__ == "__main__":
    main()
