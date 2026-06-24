"""Smoke tests for examples/mcp_auth_bridge/server.py (S3).

Verifies the reference MCP Auth Bridge example loads, exposes CLI help,
and rejects protected tool calls without a JWT (in-process, no network).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pytest import MonkeyPatch

from asap.adapters.mcp.errors import AUTH_REQUIRED

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SERVER_SCRIPT = _REPO_ROOT / "examples" / "mcp_auth_bridge" / "server.py"


def _load_server_module() -> ModuleType:
    """Import the example server module from its file path."""
    spec = importlib.util.spec_from_file_location(
        "mcp_auth_bridge_server",
        _SERVER_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestMcpAuthBridgeExampleImport:
    """Import smoke for the standalone example server module."""

    def test_server_script_exists(self) -> None:
        """Example server file is present in the repo."""
        assert _SERVER_SCRIPT.is_file()

    def test_server_module_loads(self) -> None:
        """Server module imports and exposes build_protected_server and main."""
        module = _load_server_module()
        assert module.DEMO_HOST_ID == "mcp-auth-bridge-host"
        assert module.DEMO_AUDIENCE == "urn:asap:agent:mcp-auth-bridge"
        assert callable(module.build_protected_server)
        assert callable(module.main)


class TestMcpAuthBridgeExampleCli:
    """CLI smoke for the example entrypoint."""

    def test_help_exits_zero(self) -> None:
        """``--help`` exits 0 without starting stdio transport."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "examples/mcp_auth_bridge/server.py",
                "--help",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "MCP Auth Bridge" in result.stdout


class TestMcpAuthBridgeProtectedTool:
    """In-process auth path checks (no network)."""

    @pytest.mark.asyncio
    async def test_secure_action_without_jwt_returns_auth_required(self) -> None:
        """Protected ``secure_action`` without JWT returns ``asap:auth_required``."""
        module = _load_server_module()
        server, _identity = await module.build_protected_server()
        result = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "test"}},
        )
        assert result["isError"] is True
        assert AUTH_REQUIRED in str(result["content"][0]["text"])

    @pytest.mark.asyncio
    async def test_echo_without_jwt_succeeds(self) -> None:
        """Public ``echo`` tool runs without JWT."""
        module = _load_server_module()
        server, _identity = await module.build_protected_server()
        result = await server._handle_tools_call(
            {"name": "echo", "arguments": {"message": "hi"}},
        )
        assert result.get("isError") is not True
        assert "hi" in str(result["content"][0]["text"])

    @pytest.mark.asyncio
    async def test_secure_action_with_jwt_succeeds(self) -> None:
        """Protected ``secure_action`` succeeds with demo JWT in ``_meta``."""
        module = _load_server_module()
        server, identity = await module.build_protected_server()
        result = await server._handle_tools_call(
            {
                "name": "secure_action",
                "arguments": {"action": "test"},
                "_meta": {"asap_agent_jwt": identity.demo_jwt},
            },
        )
        assert result.get("isError") is not True
        assert "executed: test" in str(result["content"][0]["text"])

    @pytest.mark.asyncio
    async def test_secure_action_with_env_jwt_succeeds(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        """``ASAP_AGENT_JWT`` env fallback works when enabled in demo config."""
        module = _load_server_module()
        server, identity = await module.build_protected_server()
        monkeypatch.setenv("ASAP_AGENT_JWT", identity.demo_jwt)
        result = await server._handle_tools_call(
            {"name": "secure_action", "arguments": {"action": "env-demo"}},
        )
        assert result.get("isError") is not True
        assert "executed: env-demo" in str(result["content"][0]["text"])
