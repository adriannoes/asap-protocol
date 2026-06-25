"""Protected MCP server subclass for ASAP auth on ``tools/call`` (v2.5.0)."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from typing import Any

from asap.auth.agent_jwt import JwtVerifyResult, verify_agent_jwt
from asap.mcp.auth.capability_map import format_constraint_violations, resolve_capability
from asap.mcp.auth.config import MCPAuthConfig, resolve_jwt_extractor
from asap.mcp.auth.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
    INVALID_TOKEN,
    tool_error_result,
)
from asap.mcp.protocol import CallToolRequestParams
from asap.mcp.server import MCPServer
from asap.observability import get_logger

logger = get_logger(__name__)


class ProtectedMCPServer(MCPServer):
    """``MCPServer`` with JWT verification on ``tools/call`` before tool handlers run.

    ``tools/list`` is unchanged unless ``hide_unauthorized_tools`` is implemented;
    MCP-MAP-004 is deferred (design-lock §6 — no stdio JWT carriage on list).
    """

    def __init__(self, config: MCPAuthConfig) -> None:
        super().__init__()
        self._auth_config = config
        self._jwt_extractor = resolve_jwt_extractor(config)
        if config.hide_unauthorized_tools:
            # MCP-MAP-004 is deferred: tools/list still returns all tools; only
            # tools/call is gated. State this explicitly so operators do not assume
            # unauthorized tools are hidden from discovery (formal review M-3).
            logger.warning(
                "mcp.auth.hide_unauthorized_tools_noop",
                message=(
                    "hide_unauthorized_tools=True is a no-op: tools/list still "
                    "returns all tools; only tools/call is gated"
                ),
            )
        if config.allow_env_jwt_fallback:
            # Loud operator signal at construction so a process-wide JWT bypass
            # is not silently enabled in multi-tool production (formal review M-2).
            # Emitted via warnings.warn (stderr) instead of the structlog logger
            # (stdout) so it does not corrupt the JSON-RPC stream when the server
            # runs as a stdio subprocess — the same reason the Wave C attempt to
            # log this at MCPAuthConfig construction broke the MCPClient handshake.
            warnings.warn(
                "allow_env_jwt_fallback=True: tools/call with no in-band JWT "
                "authenticates as the ASAP_AGENT_JWT env holder — dev-only, "
                "unsafe for multi-tool production",
                stacklevel=2,
            )

    @classmethod
    def from_server(cls, server: MCPServer, config: MCPAuthConfig) -> ProtectedMCPServer:
        """Copy registration state from ``server`` without mutating the original."""
        protected = cls(config)
        protected._server_info = server._server_info
        protected._instructions = server._instructions
        protected._tools = dict(server._tools)

        if config.validate_tools_at_startup:
            _validate_tools_at_startup(protected)

        return protected

    def register_tool(
        self,
        name: str,
        func: Callable[..., Any],
        schema: dict[str, Any],
        *,
        description: str = "",
        title: str | None = None,
        capability: str | None = None,
    ) -> None:
        """Register a tool with optional ASAP capability metadata (MCP-MAP-002)."""
        super().register_tool(
            name,
            func,
            schema,
            description=description,
            title=title,
            capability=capability,
        )
        if self._auth_config.validate_tools_at_startup:
            _validate_tool_at_startup(self, name)

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Intercept ``tools/call`` for JWT extraction, verification, and grant checks."""
        try:
            parsed = CallToolRequestParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}") from e

        if parsed.name in self._auth_config.public_tools:
            if self._jwt_extractor(parsed):
                logger.warning("mcp.tool.public_jwt_ignored", tool_name=parsed.name)
            return await super()._handle_tools_call(params)

        token = self._jwt_extractor(parsed)
        if not token:
            return tool_error_result(AUTH_REQUIRED)

        verify_result = await verify_agent_jwt(
            token,
            self._auth_config.host_store,
            self._auth_config.agent_store,
            expected_audience=self._auth_config.expected_audience,
            jti_replay_cache=self._auth_config.jti_replay_cache,
        )
        if not verify_result.ok:
            return tool_error_result(INVALID_TOKEN, verify_result.error)

        if self._auth_config.enforce_grants:
            grant_error = self._check_capability_grant(parsed, verify_result)
            if grant_error is not None:
                return grant_error
        else:
            logger.debug("mcp.tool.grants_skipped", tool_name=parsed.name)

        agent = verify_result.agent
        if agent is not None:
            logger.info(
                "mcp.tool.authorized",
                agent_id=agent.agent_id,
                tool_name=parsed.name,
            )

        return await super()._handle_tools_call(params)

    def _check_capability_grant(
        self,
        parsed: CallToolRequestParams,
        verify_result: JwtVerifyResult,
    ) -> dict[str, Any] | None:
        """Return a ``tools/call`` error result when grant enforcement fails."""
        capability = resolve_capability(parsed.name, self._auth_config, server=self)
        if capability not in verify_result.capabilities:
            return tool_error_result(
                CAPABILITY_DENIED,
                f"JWT capabilities claim does not include {capability!r}",
            )

        agent = verify_result.agent
        if agent is None:
            return tool_error_result(CAPABILITY_DENIED, "missing agent identity for grant check")

        grant_result = self._auth_config.capability_registry.check_grant(
            agent.agent_id,
            capability,
            parsed.arguments or {},
        )
        if grant_result.allowed:
            return None

        if grant_result.violations:
            return tool_error_result(
                CONSTRAINT_VIOLATION,
                format_constraint_violations(grant_result.violations),
            )

        return tool_error_result(
            CAPABILITY_DENIED,
            f"no active grant for capability {capability!r}",
        )


def _validate_tool_at_startup(protected: ProtectedMCPServer, tool_name: str) -> None:
    """Ensure one tool resolves to a known capability (MCP-MAP-003)."""
    config = protected._auth_config
    registry = config.capability_registry
    capability = resolve_capability(tool_name, config, server=protected)
    if not capability or not capability.strip():
        raise ValueError(
            f"Tool {tool_name!r} resolves to empty capability name; "
            "set tool_capability_map or register-time capability metadata"
        )
    if registry.describe(capability) is None:
        raise ValueError(
            f"Tool {tool_name!r} resolves to unknown capability {capability!r} "
            f"(not registered; describe returned None)"
        )


def _validate_tools_at_startup(protected: ProtectedMCPServer) -> None:
    """Ensure every registered tool resolves to a known capability (MCP-MAP-003)."""
    for tool_name in protected._tools:
        _validate_tool_at_startup(protected, tool_name)
