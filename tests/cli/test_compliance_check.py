"""Tests for `asap compliance-check` CLI (Sprint S2 — TDD)."""

from __future__ import annotations

import json
import re
import socket
import threading
from collections.abc import Generator

import pytest
from fastapi import FastAPI
from typer.testing import CliRunner

from asap.cli import app
from asap.testing.asgi_factory import make_compliance_test_app
from asap.testing.compliance import ComplianceReport

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", text)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> bool:
    import time as time_module

    deadline = time_module.monotonic() + timeout
    while time_module.monotonic() < deadline:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect((host, port))
            return True
        except OSError:
            time_module.sleep(0.05)
    return False


@pytest.fixture
def compliance_base_url() -> Generator[str, None, None]:
    """Serve ``make_compliance_test_app()`` on loopback; yield HTTP base URL."""
    import asyncio

    import uvicorn

    port = _free_port()
    fastapi_app = make_compliance_test_app()
    server_started = threading.Event()

    def run_server() -> None:
        config = uvicorn.Config(
            fastapi_app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        server_started.set()
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    if not server_started.wait(timeout=5.0):
        pytest.fail("Uvicorn did not start in time")
    if not _wait_for_port("127.0.0.1", port, timeout=10.0):
        pytest.fail("Server port did not become reachable in time")

    yield f"http://127.0.0.1:{port}"


def _minimal_non_asap_app() -> FastAPI:
    """HTTP app without ASAP endpoints so harness checks mostly fail."""

    mini = FastAPI()

    @mini.get("/ping")
    def _ping() -> dict[str, str]:
        return {"ok": "true"}

    return mini


@pytest.fixture
def failing_agent_base_url() -> Generator[str, None, None]:
    """Loopback server that is not an ASAP agent (low compliance score)."""
    import asyncio

    import uvicorn

    port = _free_port()
    fastapi_app = _minimal_non_asap_app()
    server_started = threading.Event()

    def run_server() -> None:
        config = uvicorn.Config(
            fastapi_app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
        server = uvicorn.Server(config)
        server_started.set()
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    if not server_started.wait(timeout=5.0):
        pytest.fail("Uvicorn did not start in time")
    if not _wait_for_port("127.0.0.1", port, timeout=10.0):
        pytest.fail("Server port did not become reachable in time")

    yield f"http://127.0.0.1:{port}"


class TestComplianceCheckCli:
    """Target: ``asap compliance-check --url <base> --output json`` (see sprint S2)."""

    def test_compliance_check_json_report_exit_zero(
        self, compliance_base_url: str
    ) -> None:
        """CLI hits a live ASAP app and prints a JSON ``ComplianceReport`` (score + checks)."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "compliance-check",
                "--url",
                compliance_base_url,
                "--output",
                "json",
            ],
        )

        assert result.exit_code == 0, result.stdout + result.stderr
        raw = _strip_ansi(result.stdout.strip())
        data = json.loads(raw)
        report = ComplianceReport.model_validate(data)
        assert report.version == "2.0"
        assert "score" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) > 0

    def test_exit_code_zero_with_exit_on_fail_when_all_checks_pass(
        self, compliance_base_url: str
    ) -> None:
        """Exit 0 when score is 1.0 even with ``--exit-on-fail``."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "compliance-check",
                "--url",
                compliance_base_url,
                "--output",
                "text",
                "--exit-on-fail",
            ],
        )
        assert result.exit_code == 0, result.stdout + result.stderr

    def test_exit_code_one_when_exit_on_fail_and_score_below_one(
        self, failing_agent_base_url: str
    ) -> None:
        """Exit 1 when ``--exit-on-fail`` and at least one harness check fails."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "compliance-check",
                "--url",
                failing_agent_base_url,
                "--output",
                "text",
                "--exit-on-fail",
            ],
        )
        assert result.exit_code == 1, result.stdout + result.stderr

    def test_exit_code_two_on_connection_refused(self) -> None:
        """Exit 2 when no server accepts connections at ``--url``."""
        dead_port = _free_port()
        dead_url = f"http://127.0.0.1:{dead_port}"
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", dead_url, "--output", "text"],
        )
        assert result.exit_code == 2, result.stdout + result.stderr
        err = _strip_ansi(result.stderr)
        assert "connect" in err.lower() or "Could not connect" in err
