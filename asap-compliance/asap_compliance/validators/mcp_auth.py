"""MCP Auth Bridge compliance validation (profile ``mcp-auth-bridge``)."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import httpx
from pydantic import ValidationError

from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
)
from asap.mcp.protocol import CallToolResult, TextContent

from asap_compliance.config import (
    COMPLIANCE_ENV_VAR,
    MCP_AUTH_BRIDGE_PROFILE,
    McpAuthComplianceConfig,
)
from asap_compliance.models.mcp_manifest import McpAuthManifest
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
        if isinstance(block, dict):
            if block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        elif isinstance(block, TextContent):
            parts.append(block.text)
        else:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(str(text))
    return "".join(parts)


def _load_manifest(config: McpAuthComplianceConfig) -> McpAuthManifest:
    if config.manifest_url:
        response = httpx.get(config.manifest_url, timeout=config.timeout_seconds)
        return McpAuthManifest.model_validate(response.json())

    fixture = config.manifest_fixture_path
    if fixture is None or not fixture.is_file():
        raise FileNotFoundError(
            f"Manifest fixture not found: {fixture}; set manifest_fixture_path or manifest_url"
        )
    return McpAuthManifest.model_validate_json(fixture.read_text(encoding="utf-8"))


def _check_manifest_alignment(
    config: McpAuthComplianceConfig,
    registered_tools: list[str],
) -> list[CheckResult]:
    results: list[CheckResult] = []
    if "manifest_alignment" in config.skip_checks:
        return results

    try:
        manifest = _load_manifest(config)
    except (httpx.HTTPError, OSError, ValidationError, FileNotFoundError) as exc:
        results.append(
            CheckResult(
                name="manifest_alignment_load",
                passed=False,
                message=f"Could not load manifest: {exc}",
            )
        )
        return results

    registered = set(registered_tools)
    capabilities = manifest.capabilities
    skill_ids = [skill.id for skill in capabilities.skills]

    unknown_tools = [
        tool_name for tool_name in capabilities.mcp_tools if tool_name not in registered
    ]
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


_CheckRunner = Callable[
    [McpAuthComplianceConfig, McpAuthTransport, McpAuthProbeTokens],
    Awaitable[CheckResult],
]

_PROFILE_CHECKS: list[tuple[str, _CheckRunner]] = [
    ("public_tool", lambda c, t, _tok: _check_public_tool(c, t)),
    ("auth_required", lambda c, t, _tok: _check_unauthenticated_protected_tool(c, t)),
    ("valid_jwt", lambda c, t, tok: _check_valid_jwt(c, t, tok)),
    ("wrong_capability", lambda c, t, tok: _check_wrong_capability(c, t, tok)),
    ("constraint_violation", lambda c, t, tok: _check_constraint_violation(c, t, tok)),
]


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
    check_results: dict[str, bool] = {}

    try:
        tokens = await session.connect()
        tool_names = await session.list_tool_names()

        for name, runner in _PROFILE_CHECKS:
            if name in config.skip_checks:
                check = CheckResult(name, True, "skipped")
            else:
                check = await runner(config, session, tokens)
            checks.append(check)
            check_results[name] = check.passed

        manifest_checks = _check_manifest_alignment(config, tool_names)
        checks.extend(manifest_checks)
        manifest_alignment_ok = all(c.passed for c in manifest_checks) if manifest_checks else True

    finally:
        if owns_transport:
            await session.disconnect()

    return McpAuthResult(
        profile=config.profile,
        auth_required_ok=check_results.get("auth_required", True),
        valid_jwt_ok=check_results.get("valid_jwt", True),
        wrong_capability_ok=check_results.get("wrong_capability", True),
        constraint_violation_ok=check_results.get("constraint_violation", True),
        manifest_alignment_ok=manifest_alignment_ok,
        public_tool_ok=check_results.get("public_tool", True),
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
