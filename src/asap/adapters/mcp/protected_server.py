"""Protected MCP server subclass for ASAP auth on ``tools/call`` (v2.5.0)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, resolve_jwt_extractor
from asap.adapters.mcp.capability_map import format_constraint_violations, resolve_capability
from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
    INVALID_TOKEN,
    tool_error_result,
)
from asap.auth.agent_jwt import CAPABILITIES_CLAIM, JwtVerifyResult, verify_agent_jwt
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
        self._bridge_tool_capabilities: dict[str, str] = {}
        self._startup_tools_validated = False

    @classmethod
    def from_server(cls, server: MCPServer, config: MCPAuthConfig) -> ProtectedMCPServer:
        """Copy registration state from ``server`` without mutating the original."""
        protected = cls(config)
        protected._server_info = server._server_info
        protected._instructions = server._instructions
        protected._tools = dict(server._tools)

        bridge_caps = getattr(server, "_bridge_tool_capabilities", None)
        if isinstance(bridge_caps, dict) and bridge_caps:
            protected._bridge_tool_capabilities = dict(bridge_caps)
            config.bridge_tool_capability_map.update(bridge_caps)

        if config.validate_tools_at_startup:
            _validate_tools_at_startup(protected)
            protected._startup_tools_validated = True

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
        )
        if capability is not None:
            self._bridge_tool_capabilities[name] = capability
            self._auth_config.bridge_tool_capability_map[name] = capability

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Intercept ``tools/call`` for JWT extraction, verification, and grant checks."""
        try:
            parsed = CallToolRequestParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}") from e

        if parsed.name in self._auth_config.public_tools:
            # Public tools skip JWT entirely; a present _meta.asap_agent_jwt is not verified.
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

        agent = verify_result.agent
        if agent is not None:
            logger.info(
                "mcp.tool.authorized",
                agent_id=agent.agent_id,
                tool_name=parsed.name,
            )

        if self._auth_config.enforce_grants:
            grant_error = self._check_capability_grant(parsed, verify_result)
            if grant_error is not None:
                return grant_error

        return await super()._handle_tools_call(params)

    def _check_capability_grant(
        self,
        parsed: CallToolRequestParams,
        verify_result: JwtVerifyResult,
    ) -> dict[str, Any] | None:
        """Return a ``tools/call`` error result when grant enforcement fails."""
        capability = resolve_capability(parsed.name, self._auth_config)
        claims = verify_result.claims or {}
        jwt_capabilities = claims.get(CAPABILITIES_CLAIM)
        if not isinstance(jwt_capabilities, list) or capability not in jwt_capabilities:
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


def _validate_tools_at_startup(protected: ProtectedMCPServer) -> None:
    """Ensure every registered tool resolves to a known capability (MCP-MAP-003)."""
    config = protected._auth_config
    registry = config.capability_registry
    for tool_name in protected._tools:
        capability = resolve_capability(tool_name, config)
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
