"""Smoke tests for examples/nemo_agent_toolkit_asap/ (S1c Path A).

ASAP-side checks always run (no nvidia-nat). Optional NAT import is skipped
when the optional extra is absent so main CI stays green.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType

import pytest
from pytest import MonkeyPatch

from asap.mcp.auth.errors import AUTH_REQUIRED

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_DIR = _REPO_ROOT / "examples" / "nemo_agent_toolkit_asap"
_SERVER_SCRIPT = _EXAMPLE_DIR / "asap_mcp_server.py"
_SMOKE_SCRIPT = _EXAMPLE_DIR / "smoke_asap_side.py"
_CONFIG_YAML = _EXAMPLE_DIR / "configs" / "config-mcp-client-stdio.yml"
_ENV_JWT_KEY = "ASAP_AGENT_JWT"


@pytest.fixture(autouse=True)
def _isolate_asap_agent_jwt_env() -> Iterator[None]:
    """Keep ``ASAP_AGENT_JWT`` from leaking across example tests.

    Provenance (S1c C.7 / T3 / PR #289): ``inject_demo_jwt_env`` writes
    ``os.environ`` directly. ``monkeypatch.delenv`` alone is insufficient when the
    key was already absent — pytest records no undo, so a later ``os.environ``
    set survives teardown and contaminates ``test_mcp_auth_bridge_example.py``.
    """
    previous = os.environ.pop(_ENV_JWT_KEY, None)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_ENV_JWT_KEY, None)
        else:
            os.environ[_ENV_JWT_KEY] = previous


def _load_asap_mcp_server() -> ModuleType:
    """Import the Path A ASAP MCP server module from its file path."""
    spec = importlib.util.spec_from_file_location(
        "nemo_agent_toolkit_asap_mcp_server",
        _SERVER_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestNemoAsapExampleLayout:
    """Filesystem / DX checks for the Path A example folder."""

    def test_example_files_exist(self) -> None:
        """Required Path A files are present."""
        assert _SERVER_SCRIPT.is_file()
        assert _SMOKE_SCRIPT.is_file()
        assert _CONFIG_YAML.is_file()
        assert (_EXAMPLE_DIR / "README.md").is_file()
        assert (_EXAMPLE_DIR / ".env.example").is_file()
        assert (_EXAMPLE_DIR / "requirements.txt").is_file()
        assert (_EXAMPLE_DIR / "run_demo.sh").is_file()

    def test_requirements_pin_mentions_nat_mcp(self) -> None:
        """Optional requirements pin nvidia-nat[mcp]==1.8.0."""
        text = (_EXAMPLE_DIR / "requirements.txt").read_text(encoding="utf-8")
        assert "nvidia-nat[mcp]==1.8.0" in text

    def test_yaml_is_stdio_mcp_client(self) -> None:
        """NAT config uses mcp_client stdio pointing at asap_mcp_server."""
        text = _CONFIG_YAML.read_text(encoding="utf-8")
        assert "_type: mcp_client" in text
        assert "transport: stdio" in text
        assert "asap_mcp_server.py" in text
        # No Keycloak / OAuth wiring in live config keys (comments may mention them)
        live_lines = [
            line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")
        ]
        live = "\n".join(live_lines).lower()
        assert "auth_provider" not in live
        assert "keycloak" not in live
        assert "mcp_oauth2" not in live


class TestNemoAsapMcpServer:
    """In-process ASAP Auth Bridge path for NAT Path A."""

    def test_server_help_exits_zero(self) -> None:
        """``--help`` exits 0 without starting stdio."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(_SERVER_SCRIPT.relative_to(_REPO_ROOT)),
                "--help",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "Path A" in result.stdout or "mcp_client" in result.stdout

    @pytest.mark.asyncio
    async def test_secure_action_without_jwt_auth_required(self) -> None:
        """Protected tool without JWT returns ``asap:auth_required``."""
        module = _load_asap_mcp_server()
        server, _identity = await module.build_and_prepare_server(
            inject_env_jwt=False,
        )
        result = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "test"}},
        )
        assert result["isError"] is True
        assert AUTH_REQUIRED in str(result["content"][0]["text"])

    @pytest.mark.asyncio
    async def test_echo_and_env_jwt_happy_path(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Public echo works; env JWT unlocks secure_action (NAT carriage)."""
        module = _load_asap_mcp_server()
        # Track JWT via monkeypatch (not raw os.environ) so teardown is reliable.
        server, identity = await module.build_and_prepare_server(
            inject_env_jwt=False,
        )
        monkeypatch.setenv(_ENV_JWT_KEY, identity.demo_jwt)
        assert os.environ.get(_ENV_JWT_KEY) == identity.demo_jwt

        echo = await server._handle_tools_call(
            {"name": "echo", "arguments": {"message": "path-a"}},
        )
        assert echo.get("isError") is not True
        assert "path-a" in str(echo["content"][0]["text"])

        secure = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "granted"}},
        )
        assert secure.get("isError") is not True
        assert "executed: granted" in str(secure["content"][0]["text"])

    @pytest.mark.asyncio
    async def test_inject_env_jwt_true_sets_env_without_printing_token(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``inject_env_jwt=True`` uses ``inject_demo_jwt_env``; no JWT on stderr.

        Provenance (PR #289): covers the inject path in-process (smoke covers
        subprocess). ``print_instructions`` defaults False so CI logs stay clean.
        """
        module = _load_asap_mcp_server()
        server, identity = await module.build_and_prepare_server(
            inject_env_jwt=True,
            print_instructions=False,
        )
        assert os.environ.get(_ENV_JWT_KEY) == identity.demo_jwt

        secure = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "inject-path"}},
        )
        assert secure.get("isError") is not True
        assert "executed: inject-path" in str(secure["content"][0]["text"])

        captured = capsys.readouterr()
        assert identity.demo_jwt not in captured.err
        assert identity.demo_jwt not in captured.out
        assert "eyJ" not in captured.err
        assert "eyJ" not in captured.out

    @pytest.mark.asyncio
    async def test_without_env_jwt_meta_still_works(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """Without env JWT, secure_action needs ``_meta.asap_agent_jwt``."""
        module = _load_asap_mcp_server()
        monkeypatch.delenv(_ENV_JWT_KEY, raising=False)
        server, identity = await module.build_and_prepare_server(
            inject_env_jwt=False,
        )
        denied = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "x"}},
        )
        assert denied["isError"] is True
        assert AUTH_REQUIRED in str(denied["content"][0]["text"])

        ok = await server._handle_tools_call(
            {
                "name": "secure_action",
                "arguments": {"action": "meta"},
                "_meta": {"asap_agent_jwt": identity.demo_jwt},
            },
        )
        assert ok.get("isError") is not True
        assert "executed: meta" in str(ok["content"][0]["text"])


class TestNemoAsapSmokeScript:
    """Maintainer smoke script entrypoint."""

    def test_smoke_asap_side_exits_zero(self) -> None:
        """``smoke_asap_side.py`` passes without nvidia-nat."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(_SMOKE_SCRIPT.relative_to(_REPO_ROOT)),
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "ASAP-side Path A smoke passed" in result.stdout

    def test_smoke_asap_side_stdio_exits_zero(self) -> None:
        """Stdio smoke: env JWT + stderr logging does not corrupt JSON-RPC."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                str(_SMOKE_SCRIPT.relative_to(_REPO_ROOT)),
                "--stdio",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert "stdio secure_action via server-injected ASAP_AGENT_JWT" in result.stdout


class TestNemoAsapOptionalNat:
    """NAT import is optional — skip when nvidia-nat is not installed.

    Main CI must not require ``nvidia-nat``; ASAP-side tests above always run.
    """

    def test_nat_optional_import_skips_cleanly(self) -> None:
        """Absent ``nat`` → skip (expected in main CI); present → import ok."""
        if importlib.util.find_spec("nat") is None:
            pytest.skip("nvidia-nat optional — not installed (expected in main CI)")
        nat = importlib.import_module("nat")
        assert nat is not None
