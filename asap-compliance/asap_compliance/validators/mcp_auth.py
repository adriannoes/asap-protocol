"""MCP Auth Bridge compliance validation (profile ``mcp-auth-bridge``)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, cast

import httpx

from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
)
from asap.mcp.protocol import CallToolResult

from asap_compliance.config import (
    COMPLIANCE_ENV_VAR,
    MCP_AUTH_BRIDGE_PROFILE,
    McpAuthComplianceConfig,
)
from asap_compliance.validators.handshake import CheckResult
from asap_compliance.validators.mcp_auth_transport import (
    McpAuthProbeTokens,
    McpAuthTransport,
    MockMcpTransport,
    SubprocessMcpTransport,
)

__all__ = [
    "McpAuthProbeTokens",
    "McpAuthResult",
    "McpAuthTransport",
    "MockMcpTransport",
    "SubprocessMcpTransport",
    "validate_mcp_auth",
    "validate_mcp_auth_async",
]


@dataclass
class McpAuthResult:
    """Summary for the ``mcp-auth-bridge`` compliance profile."""

    profile: str
    auth_required_ok: bool
    valid_jwt_ok: bool
    wrong_capability_ok: bool
    constraint_violation_ok: bool
    manifest_alignment_ok: bool
    public_tool_ok: bool
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (
            self.auth_required_ok
            and self.valid_jwt_ok
            and self.wrong_capability_ok
            and self.constraint_violation_ok
            and self.manifest_alignment_ok
            and self.public_tool_ok
        )


def _tool_error_text(result: CallToolResult) -> str:
    parts: list[str] = []
    for block in result.content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        else:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
    return "".join(parts)


def _load_manifest_data(config: McpAuthComplianceConfig) -> dict[str, Any]:
    if config.manifest_url:
        response = httpx.get(config.manifest_url, timeout=config.timeout_seconds)
        return cast(dict[str, Any], response.json())

    fixture = config.manifest_fixture_path
    if fixture is None or not fixture.is_file():
        raise FileNotFoundError(
            f"Manifest fixture not found: {fixture}; set manifest_fixture_path or manifest_url"
        )
    return cast(dict[str, Any], json.loads(fixture.read_text(encoding="utf-8")))


def _check_manifest_alignment(
    config: McpAuthComplianceConfig,
    registered_tools: list[str],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    if "manifest_alignment" in config.skip_checks:
        return results

    try:
        manifest = _load_manifest_data(config)
    except (httpx.HTTPError, OSError, json.JSONDecodeError, FileNotFoundError) as exc:
        results.append(
            CheckResult(
                name="manifest_alignment_load",
                passed=False,
                message=f"Could not load manifest: {exc}",
            )
        )
        return results

    capabilities = manifest.get("capabilities", {})
    if not isinstance(capabilities, dict):
        results.append(
            CheckResult(
                name="manifest_alignment_schema",
                passed=False,
                message="Manifest capabilities must be an object",
            )
        )
        return results

    mcp_tools = capabilities.get("mcp_tools", [])
    skills = capabilities.get("skills", [])
    skill_ids: list[str] = []
    if isinstance(skills, list):
        for skill in skills:
            if isinstance(skill, dict) and isinstance(skill.get("id"), str):
                skill_ids.append(skill["id"])

    registered = set(registered_tools)
    unknown_tools: list[str] = []
    if isinstance(mcp_tools, list):
        for tool_name in mcp_tools:
            if isinstance(tool_name, str) and tool_name not in registered:
                unknown_tools.append(tool_name)

    if unknown_tools:
        results.append(
            CheckResult(
                name="manifest_mcp_tools_subset",
                passed=False,
                message=(
                    f"Manifest mcp_tools not registered on server: {sorted(unknown_tools)}; "
                    f"registered={sorted(registered)}"
                ),
            )
        )
    else:
        results.append(
            CheckResult(
                name="manifest_mcp_tools_subset",
                passed=True,
                message="Manifest mcp_tools ⊆ registered MCP tools",
            )
        )

    unknown_skills = [skill_id for skill_id in skill_ids if skill_id not in registered]
    if unknown_skills:
        results.append(
            CheckResult(
                name="manifest_skills_subset",
                passed=False,
                message=(
                    f"Manifest skills[].id not registered as MCP tools/capabilities: "
                    f"{sorted(unknown_skills)}; registered={sorted(registered)}"
                ),
            )
        )
    else:
        results.append(
            CheckResult(
                name="manifest_skills_subset",
                passed=True,
                message="Manifest skills[].id ⊆ registered MCP tools / mapped capabilities",
            )
        )

    alignment_ok = all(r.passed for r in results)
    results.append(
        CheckResult(
            name="manifest_alignment",
            passed=alignment_ok,
            message="Manifest alignment (MCP-DISC-003) passed"
            if alignment_ok
            else "Manifest alignment (MCP-DISC-003) failed",
        )
    )
    return results


async def _check_public_tool(
    config: McpAuthComplianceConfig,
    transport: McpAuthTransport,
) -> CheckResult:
    result = await transport.call_tool(config.public_tool, {}, jwt=None)
    text = _tool_error_text(result)
    passed = result.is_error is not True
    return CheckResult(
        name="public_tool",
        passed=passed,
        message=(
            f"Public tool {config.public_tool!r} succeeded without JWT"
            if passed
            else f"Public tool call failed: {text!r}"
        ),
    )


async def _check_unauthenticated_protected_tool(
    config: McpAuthComplianceConfig,
    transport: McpAuthTransport,
) -> CheckResult:
    result = await transport.call_tool(
        config.protected_tool,
        {"action": "probe"},
        jwt=None,
    )
    text = _tool_error_text(result)
    passed = result.is_error is True and AUTH_REQUIRED in text
    return CheckResult(
        name="auth_required",
        passed=passed,
        message=(
            f"Unauthenticated {config.protected_tool!r} returned {AUTH_REQUIRED}"
            if passed
            else f"Expected {AUTH_REQUIRED} for unauthenticated protected tool, got: {text!r}"
        ),
    )


async def _check_valid_jwt(
    config: McpAuthComplianceConfig,
    transport: McpAuthTransport,
    tokens: McpAuthProbeTokens,
) -> CheckResult:
    result = await transport.call_tool(
        config.protected_tool,
        {"action": "compliance-ok"},
        jwt=tokens.valid_jwt,
    )
    text = _tool_error_text(result)
    passed = result.is_error is not True
    return CheckResult(
        name="valid_jwt",
        passed=passed,
        message=(
            f"Protected {config.protected_tool!r} succeeded with valid JWT"
            if passed
            else f"Valid JWT call failed: {text!r}"
        ),
    )


async def _check_wrong_capability(
    config: McpAuthComplianceConfig,
    transport: McpAuthTransport,
    tokens: McpAuthProbeTokens,
) -> CheckResult:
    if not tokens.wrong_capability_jwt:
        return CheckResult(
            name="wrong_capability",
            passed=False,
            message=(
                "Missing wrong_capability_jwt probe token; "
                f"enable {COMPLIANCE_ENV_VAR}=1 on the MCP server"
            ),
        )

    result = await transport.call_tool(
        config.protected_tool,
        {"action": "probe"},
        jwt=tokens.wrong_capability_jwt,
    )
    text = _tool_error_text(result)
    passed = result.is_error is True and CAPABILITY_DENIED in text
    return CheckResult(
        name="wrong_capability",
        passed=passed,
        message=(
            f"Wrong capability JWT returned {CAPABILITY_DENIED}"
            if passed
            else f"Expected {CAPABILITY_DENIED}, got: {text!r}"
        ),
    )


async def _check_constraint_violation(
    config: McpAuthComplianceConfig,
    transport: McpAuthTransport,
    tokens: McpAuthProbeTokens,
) -> CheckResult:
    result = await transport.call_tool(
        config.protected_tool,
        {"action": tokens.constraint_violation_action},
        jwt=tokens.valid_jwt,
    )
    text = _tool_error_text(result)
    passed = result.is_error is True and CONSTRAINT_VIOLATION in text
    return CheckResult(
        name="constraint_violation",
        passed=passed,
        message=(
            f"Constraint violation returned {CONSTRAINT_VIOLATION}"
            if passed
            else f"Expected {CONSTRAINT_VIOLATION}, got: {text!r}"
        ),
    )


async def validate_mcp_auth_async(
    config: McpAuthComplianceConfig,
    *,
    transport: McpAuthTransport | None = None,
) -> McpAuthResult:
    """Run the ``mcp-auth-bridge`` compliance profile against an MCP server.

    Args:
        config: MCP auth compliance configuration (stdio subprocess by default).
        transport: Optional transport override (mock/in-process) for unit tests.

    Returns:
        Aggregated pass/fail result with per-check ``CheckResult`` entries.
    """
    if config.profile != MCP_AUTH_BRIDGE_PROFILE:
        raise ValueError(f"Expected profile {MCP_AUTH_BRIDGE_PROFILE!r}, got {config.profile!r}")

    owns_transport = transport is None
    session: McpAuthTransport = transport or SubprocessMcpTransport(config)
    checks: list[CheckResult] = []

    try:
        tokens = await session.connect()
        tool_names = await session.list_tool_names()

        if "public_tool" not in config.skip_checks:
            public_check = await _check_public_tool(config, session)
            checks.append(public_check)
        else:
            public_check = CheckResult("public_tool", True, "skipped")

        if "auth_required" not in config.skip_checks:
            auth_check = await _check_unauthenticated_protected_tool(config, session)
            checks.append(auth_check)
        else:
            auth_check = CheckResult("auth_required", True, "skipped")

        if "valid_jwt" not in config.skip_checks:
            valid_check = await _check_valid_jwt(config, session, tokens)
            checks.append(valid_check)
        else:
            valid_check = CheckResult("valid_jwt", True, "skipped")

        if "wrong_capability" not in config.skip_checks:
            wrong_check = await _check_wrong_capability(config, session, tokens)
            checks.append(wrong_check)
        else:
            wrong_check = CheckResult("wrong_capability", True, "skipped")

        if "constraint_violation" not in config.skip_checks:
            constraint_check = await _check_constraint_violation(config, session, tokens)
            checks.append(constraint_check)
        else:
            constraint_check = CheckResult("constraint_violation", True, "skipped")

        manifest_checks = _check_manifest_alignment(config, tool_names)
        checks.extend(manifest_checks)
        manifest_alignment_ok = all(c.passed for c in manifest_checks) if manifest_checks else True

    finally:
        if owns_transport:
            await session.disconnect()

    return McpAuthResult(
        profile=config.profile,
        auth_required_ok=auth_check.passed,
        valid_jwt_ok=valid_check.passed,
        wrong_capability_ok=wrong_check.passed,
        constraint_violation_ok=constraint_check.passed,
        manifest_alignment_ok=manifest_alignment_ok,
        public_tool_ok=public_check.passed,
        checks=checks,
    )


def validate_mcp_auth(
    config: McpAuthComplianceConfig,
    *,
    transport: McpAuthTransport | None = None,
) -> McpAuthResult:
    """Sync wrapper for :func:`validate_mcp_auth_async`."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(validate_mcp_auth_async(config, transport=transport))
    raise RuntimeError(
        "Cannot call sync validate_mcp_auth from inside a running event loop. "
        "Use validate_mcp_auth_async."
    )
