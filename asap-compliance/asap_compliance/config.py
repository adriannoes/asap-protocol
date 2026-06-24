"""Configuration for ASAP compliance harness."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from pydantic import BaseModel, Field

MCP_AUTH_BRIDGE_PROFILE = "mcp-auth-bridge"
COMPLIANCE_ENV_VAR = "ASAP_MCP_COMPLIANCE"


def find_repo_root() -> Path:
    """Locate the asap-protocol repository root from this package."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "examples" / "mcp_auth_bridge" / "server.py").is_file():
            return parent
    raise FileNotFoundError(
        "Could not locate asap-protocol repo root (expected examples/mcp_auth_bridge/server.py)"
    )


def default_mcp_auth_server_command() -> list[str]:
    """Default stdio subprocess command for the MCP Auth Bridge example."""
    override = os.environ.get("ASAP_MCP_SERVER_COMMAND")
    if override:
        return override.split()
    script = find_repo_root() / "examples" / "mcp_auth_bridge" / "server.py"
    return ["uv", "run", "python", str(script)]


def default_mcp_auth_manifest_fixture() -> Path:
    """Default manifest fixture JSON for MCP-DISC-003 alignment checks."""
    return (
        find_repo_root()
        / "asap-compliance"
        / "tests"
        / "fixtures"
        / "mcp_auth_bridge_manifest.json"
    )


class McpAuthComplianceConfig(BaseModel):
    """Configuration for the ``mcp-auth-bridge`` stdio MCP compliance profile."""

    profile: str = Field(
        default=MCP_AUTH_BRIDGE_PROFILE,
        description="Compliance profile name (release gate for stdio MCP)",
    )
    server_command: list[str] = Field(
        default_factory=default_mcp_auth_server_command,
        description="Subprocess command for the MCP server under test (stdio JSON-RPC)",
    )
    timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        description="Per-request timeout when driving the MCP subprocess",
    )
    protected_tool: str = Field(
        default="secure_action",
        description="Protected MCP tool name (requires Agent JWT)",
    )
    public_tool: str = Field(
        default="echo",
        description="Public MCP tool name (no JWT required)",
    )
    manifest_fixture_path: Path | None = Field(
        default_factory=default_mcp_auth_manifest_fixture,
        description="Fixture manifest JSON when manifest_url is unavailable",
    )
    manifest_url: str | None = Field(
        default=None,
        description="Optional live manifest URL for MCP-DISC-003 alignment",
    )
    skip_checks: list[str] = Field(
        default_factory=list,
        description="Check names to skip (e.g. 'manifest_alignment')",
    )
    compliance_env: bool = Field(
        default=True,
        description="Set ASAP_MCP_COMPLIANCE=1 on subprocess for probe JWT emission",
    )
    allowed_binaries: frozenset[str] | None = Field(
        default_factory=lambda: frozenset({"uv", "python", Path(sys.executable).name}),
        description="Allowed server_command binaries for MCPClient validation",
    )


class ComplianceConfig(BaseModel):
    agent_url: str = Field(..., description="Base URL of the agent under test")
    timeout_seconds: float = Field(default=30.0, gt=0, description="HTTP timeout in seconds")
    test_categories: list[str] = Field(
        default=["handshake", "schema", "state"],
        description="Test categories to run",
    )
    sla_skill_id: str = Field(
        default="echo",
        description="Skill ID for SLA and state validation (agent must implement this skill)",
    )
    skip_checks: list[str] = Field(
        default_factory=list,
        description="Check names to skip (e.g. 'sla' to skip SLA timeout check)",
    )
