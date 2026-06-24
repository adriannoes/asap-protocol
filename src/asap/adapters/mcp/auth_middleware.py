"""MCP Auth Bridge configuration and middleware entry points (v2.5.0)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from asap.adapters.mcp.jwt_extractor import default_jwt_extractor
from asap.auth.agent_jwt import JtiReplayCache
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import AgentStore, HostStore
from asap.mcp.protocol import CallToolRequestParams
from asap.mcp.server import MCPServer


@dataclass
class MCPAuthConfig:
    """Configuration for ASAP auth on a native MCP server.

    JWT extraction: S1 middleware MUST call :func:`resolve_jwt_extractor` (or
    equivalent ``config.jwt_extractor or`` closure over
    :func:`default_jwt_extractor` with ``allow_env_fallback=config.allow_env_jwt_fallback``).
    Do not invoke a ``None`` extractor.

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
    bridge_tool_capability_map: dict[str, str] = field(default_factory=dict)
    public_tools: frozenset[str] = frozenset()
    enforce_grants: bool = True
    # MCP-MAP-004 (MAY): deferred — stdio tools/list has no standard JWT carriage (design-lock §6).
    hide_unauthorized_tools: bool = False
    validate_tools_at_startup: bool = False
    jwt_extractor: Callable[[CallToolRequestParams], str | None] | None = None
    allow_env_jwt_fallback: bool = False
    jti_replay_cache: JtiReplayCache | None = None
    expected_audience: str | list[str] | None = None
    manifest_url: str | None = None


def resolve_jwt_extractor(config: MCPAuthConfig) -> Callable[[CallToolRequestParams], str | None]:
    """Return the JWT extractor for middleware (custom or default with config flags).

    Args:
        config: MCP auth configuration.

    Returns:
        Callable that extracts an Agent JWT from ``tools/call`` params.
    """
    if config.jwt_extractor is not None:
        return config.jwt_extractor

    allow_env = config.allow_env_jwt_fallback

    def extract(params: CallToolRequestParams) -> str | None:
        return default_jwt_extractor(params, allow_env_fallback=allow_env)

    return extract


def protect_server(server: MCPServer, config: MCPAuthConfig) -> MCPServer:
    """Return an MCP server with JWT verification on ``tools/call`` (S1).

    S1 enforces Agent JWT extraction/verification and the ``public_tools``
    allowlist. Capability grant checks via ``enforce_grants`` land in S2.

    See PRD v2.5.0 MCP Auth Bridge (``product/prd/prd-v2.5.0-mcp-auth-bridge.md``)
    and design lock ADR (``engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md``).

    Args:
        server: Native MCP server with registered tools.
        config: Auth configuration (identity stores, capability registry, extractors).

    Returns:
        Protected server instance; unprotected ``MCPServer`` usage remains valid when
        this function is not called.
    """
    # Lazy import: protected_server imports MCPAuthConfig from this module.
    from asap.adapters.mcp.protected_server import ProtectedMCPServer

    return ProtectedMCPServer.from_server(server, config)
