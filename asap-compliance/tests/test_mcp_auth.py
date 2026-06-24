"""Tests for the ``mcp-auth-bridge`` compliance profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
)
from asap.mcp.protocol import CallToolResult

from asap_compliance.config import (
    MCP_AUTH_BRIDGE_PROFILE,
    McpAuthComplianceConfig,
    default_mcp_auth_manifest_fixture,
)
from asap_compliance.validators.mcp_auth import (
    McpAuthProbeTokens,
    McpAuthResult,
    MockMcpTransport,
    validate_mcp_auth,
    validate_mcp_auth_async,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_VALID_JWT = "valid-jwt-token"
_WRONG_JWT = "wrong-capability-jwt"


def _error_result(code: str, detail: str | None = None) -> CallToolResult:
    text = code if detail is None else f"{code}: {detail}"
    return CallToolResult(content=[{"type": "text", "text": text}], isError=True)


def _success_result(message: str) -> CallToolResult:
    return CallToolResult(content=[{"type": "text", "text": message}], isError=False)


def _build_mock_transport(
    responses: dict[tuple[str, str | None], CallToolResult],
) -> MockMcpTransport:
    tokens = McpAuthProbeTokens(
        valid_jwt=_VALID_JWT,
        wrong_capability_jwt=_WRONG_JWT,
        constraint_violation_action="forbidden-action",
    )
    all_responses = {("echo", None): _success_result("echo"), **responses}
    return MockMcpTransport(
        tool_names=["echo", "secure_action"],
        responses=all_responses,
        tokens=tokens,
    )


class _ArgumentAwareMockTransport(MockMcpTransport):
    """Mock transport that branches on tool arguments for constraint checks."""

    def __init__(
        self,
        responses: dict[tuple[str, str | None], CallToolResult],
        *,
        constraint_action: str = "forbidden-action",
    ) -> None:
        super().__init__(
            tool_names=["echo", "secure_action"],
            responses={("echo", None): _success_result("echo"), **responses},
            tokens=McpAuthProbeTokens(
                valid_jwt=_VALID_JWT,
                wrong_capability_jwt=_WRONG_JWT,
                constraint_violation_action=constraint_action,
            ),
        )
        self._constraint_action = constraint_action

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        jwt: str | None = None,
    ) -> CallToolResult:
        if (
            name == "secure_action"
            and jwt == _VALID_JWT
            and arguments
            and arguments.get("action") == self._constraint_action
        ):
            return _error_result(CONSTRAINT_VIOLATION, "action forbidden")
        return await super().call_tool(name, arguments, jwt=jwt)


class TestMcpAuthProfile:
    """Profile metadata and config defaults."""

    def test_profile_name_is_mcp_auth_bridge(self) -> None:
        """Release gate profile is ``mcp-auth-bridge`` (not ``mcp_auth``)."""
        config = McpAuthComplianceConfig()
        assert config.profile == MCP_AUTH_BRIDGE_PROFILE
        assert config.profile == "mcp-auth-bridge"

    def test_default_manifest_fixture_exists(self) -> None:
        """Default MCP-DISC-003 fixture is bundled with compliance tests."""
        path = default_mcp_auth_manifest_fixture()
        assert path.is_file()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert "capabilities" in data
        assert "secure_action" in data["capabilities"]["mcp_tools"]


class TestMcpAuthMockedChecks:
    """Unit tests with mocked MCP transport responses."""

    @pytest.mark.asyncio
    async def test_all_checks_pass_with_mock_transport(self) -> None:
        """Mocked server passes auth, JWT, capability, constraint, and manifest checks."""
        transport = _ArgumentAwareMockTransport(
            {
                ("secure_action", None): _error_result(AUTH_REQUIRED),
                ("secure_action", _VALID_JWT): _success_result("executed: ok"),
                ("secure_action", _WRONG_JWT): _error_result(CAPABILITY_DENIED),
            },
        )
        config = McpAuthComplianceConfig(
            manifest_fixture_path=_FIXTURES / "mcp_auth_bridge_manifest.json",
        )
        result = await validate_mcp_auth_async(config, transport=transport)
        assert result.passed, result.checks
        assert result.profile == "mcp-auth-bridge"

    @pytest.mark.asyncio
    async def test_auth_required_fails_when_mock_allows_unauthenticated(self) -> None:
        """Validator fails when unauthenticated protected call succeeds."""
        transport = _build_mock_transport(
            {
                ("secure_action", None): _success_result("should not succeed"),
                ("secure_action", _VALID_JWT): _success_result("executed: ok"),
                ("secure_action", _WRONG_JWT): _error_result(CAPABILITY_DENIED),
            },
        )
        config = McpAuthComplianceConfig(
            manifest_fixture_path=_FIXTURES / "mcp_auth_bridge_manifest.json",
        )
        result = await validate_mcp_auth_async(config, transport=transport)
        assert not result.passed
        assert not result.auth_required_ok

    @pytest.mark.asyncio
    async def test_manifest_alignment_fails_unknown_tool(self, tmp_path: Path) -> None:
        """Manifest alignment fails when manifest declares an unknown MCP tool."""
        bad_manifest = {
            "capabilities": {
                "mcp_tools": ["echo", "secure_action", "phantom_tool"],
                "skills": [{"id": "echo"}, {"id": "secure_action"}],
            }
        }
        manifest_path = tmp_path / "bad_manifest.json"
        manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")

        transport = _ArgumentAwareMockTransport(
            {
                ("secure_action", None): _error_result(AUTH_REQUIRED),
                ("secure_action", _VALID_JWT): _success_result("executed: ok"),
                ("secure_action", _WRONG_JWT): _error_result(CAPABILITY_DENIED),
            },
        )
        config = McpAuthComplianceConfig(manifest_fixture_path=manifest_path)
        result = await validate_mcp_auth_async(config, transport=transport)
        assert not result.manifest_alignment_ok
        subset_check = next(c for c in result.checks if c.name == "manifest_mcp_tools_subset")
        assert not subset_check.passed
        assert "phantom_tool" in subset_check.message


class TestMcpAuthResult:
    """McpAuthResult aggregate behavior."""

    def test_passed_requires_all_categories(self) -> None:
        """``passed`` is False when any auth category fails."""
        ok = McpAuthResult(
            profile="mcp-auth-bridge",
            auth_required_ok=True,
            valid_jwt_ok=True,
            wrong_capability_ok=True,
            constraint_violation_ok=True,
            manifest_alignment_ok=True,
            public_tool_ok=True,
        )
        assert ok.passed

        bad = McpAuthResult(
            profile="mcp-auth-bridge",
            auth_required_ok=True,
            valid_jwt_ok=False,
            wrong_capability_ok=True,
            constraint_violation_ok=True,
            manifest_alignment_ok=True,
            public_tool_ok=True,
        )
        assert not bad.passed


class TestMcpAuthSyncWrapper:
    """Sync API behavior."""

    def test_validate_mcp_auth_sync_with_mock(self) -> None:
        """Sync wrapper runs mocked validation outside a running loop."""
        transport = _ArgumentAwareMockTransport(
            {
                ("secure_action", None): _error_result(AUTH_REQUIRED),
                ("secure_action", _VALID_JWT): _success_result("executed: ok"),
                ("secure_action", _WRONG_JWT): _error_result(CAPABILITY_DENIED),
            },
        )
        config = McpAuthComplianceConfig(
            manifest_fixture_path=_FIXTURES / "mcp_auth_bridge_manifest.json",
        )
        result = validate_mcp_auth(config, transport=transport)
        assert result.valid_jwt_ok
        assert result.passed


@pytest.mark.asap_compliance
class TestMcpAuthSubprocessIntegration:
    """Subprocess integration against examples/mcp_auth_bridge/server.py."""

    @pytest.mark.asyncio
    async def test_subprocess_example_server_passes_profile(self) -> None:
        """Full ``mcp-auth-bridge`` profile passes against the S3 example server."""
        config = McpAuthComplianceConfig()
        result = await validate_mcp_auth_async(config)
        assert result.profile == "mcp-auth-bridge"
        assert result.passed, [c for c in result.checks if not c.passed]
