"""Smoke tests for examples/mcp_auth_bridge (server + self-contained client).

Verifies the reference MCP Auth Bridge example loads, exposes CLI help,
rejects protected tool calls without a JWT (in-process), and that
``client.py`` succeeds by capturing the child server's JWT without an external JWT.
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
_EXAMPLE_DIR = _REPO_ROOT / "examples" / "mcp_auth_bridge"
_SERVER_SCRIPT = _EXAMPLE_DIR / "server.py"
_CLIENT_SCRIPT = _EXAMPLE_DIR / "client.py"
_ENV_JWT_KEY = "ASAP_AGENT_JWT"


@pytest.fixture(autouse=True)
def _isolate_asap_agent_jwt_env() -> Iterator[None]:
    """Keep ``ASAP_AGENT_JWT`` from leaking across example tests.

    Mirrors ``test_nemo_agent_toolkit_asap.py`` so reversed collection order
    cannot contaminate sibling example modules.
    """
    previous = os.environ.pop(_ENV_JWT_KEY, None)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(_ENV_JWT_KEY, None)
        else:
            os.environ[_ENV_JWT_KEY] = previous


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


def _load_client_module() -> ModuleType:
    """Import the example client module from its file path."""
    spec = importlib.util.spec_from_file_location(
        "mcp_auth_bridge_client",
        _CLIENT_SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_client_subprocess_ok(result: subprocess.CompletedProcess[str]) -> None:
    """Assert client subprocess success without dumping minted JWTs on failure."""
    client = _load_client_module()
    redacted_stderr = client.redact_jwt_from_text(result.stderr)
    assert result.returncode == 0, (
        f"returncode={result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr (redacted):\n{redacted_stderr}"
    )


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
        assert callable(module.route_observability_logs_to_stderr)


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
            timeout=30,
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


class TestParseDemoJwtFromStderr:
    """Unit checks for client-side stderr JWT capture."""

    def test_parse_demo_jwt_from_banner(self) -> None:
        """Parser reads the compact JWT after the minted-banner marker."""
        client = _load_client_module()
        token = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZW1vIn0.signature"
        stderr = (
            "=== MCP Auth Bridge example ===\n"
            "Minted demo Agent JWT (60s TTL, capabilities=['secure_action']):\n"
            f"{token}\n"
            "Pass JWT on tools/call:\n"
        )
        assert client.parse_demo_jwt_from_stderr(stderr) == token

    def test_parse_ignores_jwt_before_marker(self) -> None:
        """Global ``eyJ`` lines before the mint marker are ignored."""
        client = _load_client_module()
        decoy = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZWNveSJ9.signature"
        real = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZW1vIn0.signature"
        stderr = f"{decoy}\nMinted demo Agent JWT (60s TTL):\n{real}\n"
        assert client.parse_demo_jwt_from_stderr(stderr) == real

    def test_parse_demo_jwt_missing_raises_without_leaking_token(self) -> None:
        """Parser raises when stderr has no post-marker JWT; preview is redacted."""
        client = _load_client_module()
        token = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZW1vIn0.signature"
        with pytest.raises(RuntimeError, match="did not include a demo Agent JWT") as exc:
            client.parse_demo_jwt_from_stderr(f"noise\n{token}\n")
        assert token not in str(exc.value)
        assert "[REDACTED_JWT]" in str(exc.value) or "eyJ" not in str(exc.value)

    def test_redact_jwt_from_text(self) -> None:
        """Redactor replaces compact JWT lines for safe failure messages."""
        client = _load_client_module()
        token = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJkZW1vIn0.signature"
        assert token not in client.redact_jwt_from_text(f"before\n{token}\nafter")

    def test_redact_before_truncate_does_not_leak_jwt_prefix(self) -> None:
        """Truncating a long JWT before redact must not leave an ``eyJ`` prefix.

        ``redact_jwt_from_text(text[:500])`` can cut the compact token so the
        remainder no longer matches the regex.
        """
        client = _load_client_module()
        # Compact JWT longer than the 500-char preview window.
        payload = "a" * 520
        token = f"eyJhbGciOiJFZERTQSJ9.{payload}.signature"
        stderr = f"noise\n{token}\nmore"
        # Correct order: redact full stream, then truncate.
        preview = client.redact_jwt_from_text(stderr)[:500]
        assert "eyJ" not in preview
        assert token[:40] not in preview
        assert "[REDACTED_JWT]" in preview or "signature" not in preview
        # Wrong order (truncate first) would leak — document the regression shape.
        wrong = client.redact_jwt_from_text(stderr[:500])
        assert "eyJ" in wrong, "sanity: truncate-before-redact leaves a JWT prefix"


class TestMcpAuthBridgeClientSubprocess:
    """Subprocess smoke for the self-contained example client."""

    def test_client_subprocess_without_external_jwt_succeeds(self) -> None:
        """``client.py`` without JWT args captures child JWT and passes tools.

        Cross-process pasted JWTs fail signature checks; the supported path is
        auto-capture from the spawned child stderr.
        """
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "examples/mcp_auth_bridge/client.py",
            ],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        _assert_client_subprocess_ok(result)
        assert "echo:" in result.stdout
        assert "secure_action:" in result.stdout
        assert "executed: demo" in result.stdout
        assert "eyJ" not in result.stdout
        assert "eyJ" not in result.stderr

    def test_client_ignores_stale_asap_agent_jwt_env(self) -> None:
        """Stale ``ASAP_AGENT_JWT`` must not skip stderr capture."""
        env = os.environ.copy()
        env[_ENV_JWT_KEY] = "eyJhbGciOiJFZERTQSJ9.eyJzdWIiOiJzdGFsZSJ9.signature"
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "examples/mcp_auth_bridge/client.py",
            ],
            cwd=_REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        _assert_client_subprocess_ok(result)
        assert "secure_action:" in result.stdout
        assert "executed: demo" in result.stdout

    def test_client_subprocess_from_example_dir_without_jwt(self) -> None:
        """``client.py`` resolves ``server.py`` relative to its file (any cwd)."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "client.py",
            ],
            cwd=_EXAMPLE_DIR,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        _assert_client_subprocess_ok(result)
        assert "echo:" in result.stdout
        assert "secure_action:" in result.stdout

    def test_client_invalid_jwt_override_fails_secure_action(self) -> None:
        """``--invalid-jwt`` exercises the negative ``secure_action`` path."""
        result = subprocess.run(
            [
                "uv",
                "run",
                "python",
                "client.py",
                "--invalid-jwt",
            ],
            cwd=_EXAMPLE_DIR,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        assert "echo:" in result.stdout
        assert "secure_action failed" in result.stderr
        assert result.returncode == 1
        assert "eyJ" not in result.stdout
        assert "eyJ" not in result.stderr
