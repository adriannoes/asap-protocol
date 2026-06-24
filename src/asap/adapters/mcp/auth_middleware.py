"""MCP Auth Bridge configuration and middleware entry points (v2.5.0)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from asap.auth.agent_jwt import JtiReplayCache
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import AgentStore, HostStore
from asap.mcp.protocol import CallToolRequestParams
from asap.mcp.server import MCPServer


@dataclass
class MCPAuthConfig:
    """Configuration for ASAP auth on a native MCP server.

    Example:
        >>> config = MCPAuthConfig(
        ...     host_store=host_store,
        ...     agent_store=agent_store,
        ...     capability_registry=registry,
        ... )
    """

    host_store: HostStore
    agent_store: AgentStore
    capability_registry: CapabilityRegistry
    tool_capability_map: dict[str, str] = field(default_factory=dict)
    public_tools: frozenset[str] = frozenset()
    enforce_grants: bool = True
    hide_unauthorized_tools: bool = False
    validate_tools_at_startup: bool = False
    jwt_extractor: Callable[[CallToolRequestParams], str | None] | None = None
    jti_replay_cache: JtiReplayCache | None = None
    expected_audience: str | list[str] | None = None
    manifest_url: str | None = None


def protect_server(server: MCPServer, config: MCPAuthConfig) -> MCPServer:
    """Return an MCP server with ``tools/call`` wrapped by ASAP auth and grant checks.

    See PRD v2.5.0 MCP Auth Bridge (``product/prd/prd-v2.5.0-mcp-auth-bridge.md``)
    and design lock ADR (``engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md``).

    Args:
        server: Native MCP server with registered tools.
        config: Auth configuration (identity stores, capability registry, extractors).

    Returns:
        Protected server instance; unprotected ``MCPServer`` usage remains valid when
        this function is not called.

    Raises:
        NotImplementedError: Until S1 core middleware is implemented.
    """
    raise NotImplementedError("protect_server is implemented in sprint S1")
