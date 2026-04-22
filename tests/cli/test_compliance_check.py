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


@pytest.fixture(autouse=True)
def _stable_typer_rich_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin Typer/Rich formatting so ``--help`` / error output doesn't wrap on narrow CI.

    GitHub Actions terminals default to 80 columns which makes Rich wrap long options and
    error messages inside box-draw panels, breaking substring assertions. See the sibling
    fixture in ``tests/cli/test_audit_export.py`` for rationale.
    """
    import typer.rich_utils as tr

    monkeypatch.setenv("COLUMNS", "200")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setattr(tr, "MAX_WIDTH", 200)


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


def _serve_with_cooperative_shutdown(fastapi_app: FastAPI, port: int) -> Generator[str, None, None]:
    """Run ``fastapi_app`` on ``127.0.0.1:port`` and stop uvicorn on fixture teardown.

    The server's ``should_exit`` flag plus ``thread.join`` prevents the leaked-socket /
    leaked-coroutine pattern flagged in the PR-127 review (§2.5).
    """
    import asyncio

    import uvicorn

    config = uvicorn.Config(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    server_started = threading.Event()

    def run_server() -> None:
        server_started.set()
        asyncio.run(server.serve())

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    if not server_started.wait(timeout=5.0):
        pytest.fail("Uvicorn did not start in time")
    if not _wait_for_port("127.0.0.1", port, timeout=10.0):
        pytest.fail("Server port did not become reachable in time")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5.0)


@pytest.fixture
def compliance_base_url() -> Generator[str, None, None]:
    """Serve ``make_compliance_test_app()`` on loopback; yield HTTP base URL."""
    port = _free_port()
    fastapi_app = make_compliance_test_app()
    yield from _serve_with_cooperative_shutdown(fastapi_app, port)


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
    port = _free_port()
    fastapi_app = _minimal_non_asap_app()
    yield from _serve_with_cooperative_shutdown(fastapi_app, port)


class TestComplianceCheckCli:
    """Target: ``asap compliance-check --url <base> --output json`` (see sprint S2)."""

    def test_compliance_check_json_report_exit_zero(self, compliance_base_url: str) -> None:
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

    def test_invalid_output_format_rejected(self) -> None:
        """``--output yaml`` (unsupported) fails validation before any IO."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", "http://127.0.0.1:1", "--output", "yaml"],
        )
        assert result.exit_code != 0
        assert "must be 'text' or 'json'" in (result.stdout + result.stderr)

    def test_zero_or_negative_timeout_rejected(self) -> None:
        """``--timeout 0`` is rejected as BadParameter."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", "http://127.0.0.1:1", "--timeout", "0"],
        )
        assert result.exit_code != 0
        assert "must be positive" in (result.stdout + result.stderr)

    def test_format_alias_accepts_json(self, compliance_base_url: str) -> None:
        """``--format json`` is accepted as an alias for ``--output json``."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", compliance_base_url, "--format", "json"],
        )
        assert result.exit_code == 0, result.stdout + result.stderr
        data = json.loads(_strip_ansi(result.stdout.strip()))
        assert "score" in data

    def test_timeout_maps_to_exit_two(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``httpx.TimeoutException`` during the harness run exits 2 with a helpful message."""
        import httpx

        from asap.cli import compliance_check as mod

        async def _raise_timeout(*_args: object, **_kwargs: object) -> ComplianceReport:
            raise httpx.TimeoutException("simulated")

        monkeypatch.setattr(mod, "run_compliance_harness_v2_from_url", _raise_timeout)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", "http://127.0.0.1:1", "--output", "text"],
        )
        assert result.exit_code == 2, result.stdout + result.stderr
        assert "timed out" in _strip_ansi(result.stderr).lower()

    def test_asap_version_header_forwarded(
        self, monkeypatch: pytest.MonkeyPatch, compliance_base_url: str
    ) -> None:
        """``--asap-version`` is propagated as the default ``ASAP-Version`` header."""
        from asap.cli import compliance_check as mod

        seen: dict[str, object] = {}

        async def _spy(
            url: str,
            *,
            request_timeout: float,
            default_headers: dict[str, str] | None,
        ) -> ComplianceReport:
            seen["url"] = url
            seen["timeout"] = request_timeout
            seen["headers"] = default_headers
            from datetime import datetime, timezone

            return ComplianceReport(
                version="2.0",
                timestamp=datetime.now(timezone.utc),
                score=1.0,
                summary="ok",
                categories_run=[],
                checks=[],
            )

        monkeypatch.setattr(mod, "run_compliance_harness_v2_from_url", _spy)
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "compliance-check",
                "--url",
                compliance_base_url,
                "--output",
                "json",
                "--asap-version",
                "2.2",
            ],
        )
        assert result.exit_code == 0, result.stdout + result.stderr
        assert seen["headers"] == {"ASAP-Version": "2.2"}

    def test_generic_request_error_maps_to_exit_two(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Non-connect/timeout transport errors still exit 2 with a class-named message."""
        import httpx

        from asap.cli import compliance_check as mod

        async def _raise_req(*_args: object, **_kwargs: object) -> ComplianceReport:
            raise httpx.ReadError("simulated read error")

        monkeypatch.setattr(mod, "run_compliance_harness_v2_from_url", _raise_req)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", "http://127.0.0.1:1", "--output", "text"],
        )
        assert result.exit_code == 2, result.stdout + result.stderr
        assert "ReadError" in _strip_ansi(result.stderr)

    def test_text_output_renders_human_readable_report(self, compliance_base_url: str) -> None:
        """``--output text`` prints the harness header + per-check PASS/FAIL list."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", compliance_base_url, "--output", "text"],
        )
        assert result.exit_code == 0, result.stdout + result.stderr
        body = _strip_ansi(result.stdout)
        assert "Compliance Harness v2" in body
        assert "Score:" in body
        assert "[PASS]" in body or "[FAIL]" in body

    def test_os_error_maps_to_exit_two(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A raw OSError from the harness (e.g., DNS failure) surfaces as exit 2."""
        from asap.cli import compliance_check as mod

        async def _raise_os(*_args: object, **_kwargs: object) -> ComplianceReport:
            raise OSError("simulated dns failure")

        monkeypatch.setattr(mod, "run_compliance_harness_v2_from_url", _raise_os)
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["compliance-check", "--url", "http://127.0.0.1:1", "--output", "text"],
        )
        assert result.exit_code == 2, result.stdout + result.stderr
        assert "Transport error" in _strip_ansi(result.stderr)
