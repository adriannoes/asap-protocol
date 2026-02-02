"""Integration test for OpenTelemetry tracing with Jaeger.

Verifies that when OTEL_TRACES_EXPORTER=otlp and OTEL_EXPORTER_OTLP_ENDPOINT
point to a running Jaeger, spans from ASAP server (handler, request) appear
in Jaeger. Requires Docker to run Jaeger all-in-one.

Run with: pytest tests/observability/test_jaeger_tracing.py -v
Skip if Docker is not available: test is skipped when docker or Jaeger cannot be started.
"""

import os
import subprocess
import sys
import time
from urllib.parse import quote_plus

import httpx
import pytest

# Default manifest id used when running uvicorn asap.transport.server:app
DEFAULT_SERVICE_NAME = "urn:asap:agent:default-server"
JAEGER_UI_PORT = 16686
JAEGER_OTLP_GRPC_PORT = 4317
ASAP_SERVER_PORT = 8765
CONTAINER_NAME = "asap-jaeger-tracing-test"


def _docker_available() -> bool:
    """Return True if Docker is available and we can run containers."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _jaeger_container_running() -> bool:
    """Return True if our test Jaeger container is already running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={CONTAINER_NAME}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return CONTAINER_NAME in (result.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _start_jaeger() -> bool:
    """Start Jaeger all-in-one in Docker. Return True if started or already running."""
    if _jaeger_container_running():
        return True
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                "-p",
                f"{JAEGER_UI_PORT}:16686",
                "-p",
                f"{JAEGER_OTLP_GRPC_PORT}:4317",
                "jaegertracing/all-in-one:1.53",
            ],
            capture_output=True,
            timeout=60,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_jaeger_ui(timeout_seconds: int = 30) -> bool:
    """Wait until Jaeger UI responds. Return True if ready."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{JAEGER_UI_PORT}", timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1.0)
    return False


def _wait_for_asap_server(timeout_seconds: int = 15) -> bool:
    """Wait until ASAP server health endpoint responds. Return True if ready."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            r = httpx.get(f"http://127.0.0.1:{ASAP_SERVER_PORT}/health", timeout=2.0)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _send_asap_request() -> bool:
    """Send a single POST /asap request (task.request) to trigger tracing. Return True if 200."""
    envelope = {
        "asap_version": "0.1",
        "sender": "urn:asap:agent:client",
        "recipient": "urn:asap:agent:default-server",
        "payload_type": "task.request",
        "payload": {
            "conversation_id": "conv-jaeger-test",
            "skill_id": "echo",
            "input": {"message": "jaeger test"},
        },
    }
    body = {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": envelope},
        "id": "jaeger-test-1",
    }
    try:
        r = httpx.post(
            f"http://127.0.0.1:{ASAP_SERVER_PORT}/asap",
            json=body,
            timeout=5.0,
        )
        return r.status_code == 200
    except Exception:
        return False


def _query_jaeger_traces(service: str) -> list[dict]:
    """Query Jaeger API for traces of the given service. Return list of trace objects."""
    try:
        url = f"http://127.0.0.1:{JAEGER_UI_PORT}/api/traces?service={quote_plus(service)}"
        r = httpx.get(url, timeout=5.0)
        if r.status_code != 200:
            return []
        data = r.json()
        return data.get("data") or []
    except Exception:
        return []


def _wait_for_jaeger_traces(service: str, timeout_seconds: int = 15) -> list[dict]:
    """Poll Jaeger API until at least one trace appears or timeout. Return list of traces."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        traces = _query_jaeger_traces(service)
        if len(traces) >= 1:
            return traces
        time.sleep(1.0)
    return []


def _stop_jaeger() -> None:
    """Stop and remove the test Jaeger container."""
    try:
        subprocess.run(
            ["docker", "stop", CONTAINER_NAME],
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["docker", "rm", "-f", CONTAINER_NAME],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass


@pytest.mark.skipif(not _docker_available(), reason="Docker not available")
def test_jaeger_receives_asap_traces() -> None:
    """Start Jaeger, run ASAP server with OTLP, send request, verify traces in Jaeger."""
    # Start Jaeger
    if not _start_jaeger():
        pytest.skip("Could not start Jaeger container")
    if not _wait_for_jaeger_ui():
        _stop_jaeger()
        pytest.skip("Jaeger UI did not become ready")

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    src_path = os.path.join(project_root, "src")
    env = os.environ.copy()
    env["OTEL_TRACES_EXPORTER"] = "otlp"
    env["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://localhost:4317"
    env["PYTHONPATH"] = src_path

    # Start ASAP server (uvicorn asap.transport.server:app) with same Python as pytest
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "asap.transport.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(ASAP_SERVER_PORT),
        ],
        env=env,
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        if not _wait_for_asap_server():
            pytest.skip("ASAP server did not become ready")
        if not _send_asap_request():
            pytest.skip("ASAP request failed")

        # OTLP uses batch export; poll until traces appear or timeout
        traces = _wait_for_jaeger_traces(DEFAULT_SERVICE_NAME, timeout_seconds=15)
        assert len(traces) >= 1, (
            f"Expected at least one trace for service {DEFAULT_SERVICE_NAME} in Jaeger; "
            f"got {len(traces)}. Check Jaeger UI at http://localhost:{JAEGER_UI_PORT}"
        )
        first_trace = traces[0]
        spans = first_trace.get("spans") or []
        span_names = {s.get("operationName") for s in spans}
        assert len(span_names) >= 1, "Trace should contain at least one span"
        # Verify expected ASAP custom span name (handler execution)
        assert "asap.handler.execute" in span_names, (
            f"Expected span asap.handler.execute in trace; got {span_names}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        _stop_jaeger()
