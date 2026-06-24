"""Protected MCP server subclass for ASAP auth on ``tools/call`` (v2.5.0)."""

from __future__ import annotations

from typing import Any

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, resolve_jwt_extractor
from asap.adapters.mcp.errors import AUTH_REQUIRED, INVALID_TOKEN, tool_error_result
from asap.auth.agent_jwt import verify_agent_jwt
from asap.mcp.protocol import CallToolRequestParams
from asap.mcp.server import MCPServer
from asap.observability import get_logger

logger = get_logger(__name__)


class ProtectedMCPServer(MCPServer):
    """``MCPServer`` with JWT verification on ``tools/call`` before tool handlers run."""

    def __init__(self, config: MCPAuthConfig) -> None:
        super().__init__()
        self._auth_config = config
        self._jwt_extractor = resolve_jwt_extractor(config)

    @classmethod
    def from_server(cls, server: MCPServer, config: MCPAuthConfig) -> ProtectedMCPServer:
        """Copy registration state from ``server`` without mutating the original."""
        protected = cls(config)
        protected._server_info = server._server_info
        protected._instructions = server._instructions
        protected._tools = dict(server._tools)
        return protected

    async def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Intercept ``tools/call`` for JWT extraction and verification (S1)."""
        try:
            parsed = CallToolRequestParams(**params)
        except Exception as e:
            raise ValueError(f"Invalid params: {e}") from e

        if parsed.name in self._auth_config.public_tools:
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

        return await super()._handle_tools_call(params)
