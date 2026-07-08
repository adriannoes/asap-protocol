"""MCP Auth Bridge configuration (v2.5.0)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from asap.auth.jti_replay_cache import JtiReplayCacheProtocol
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import AgentStore, HostStore
from asap.mcp.auth.jwt_extractor import default_jwt_extractor
from asap.mcp.protocol import CallToolRequestParams


MCP_COMPLIANCE_ENV_VAR = "ASAP_MCP_COMPLIANCE"


@dataclass
class MCPAuthConfig:
    """Configuration for ASAP auth on a native MCP server.

    JWT extraction: middleware MUST call :func:`resolve_jwt_extractor` (or
    equivalent ``config.jwt_extractor or`` closure over
    :func:`default_jwt_extractor` with ``allow_env_fallback=config.allow_env_jwt_fallback``).
    Do not invoke a ``None`` extractor.

    ``hide_unauthorized_tools`` is reserved for MCP-MAP-004 (deferred per design-lock §6);
    stdio ``tools/list`` has no standard JWT carriage in v2.5.0.

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
    allow_env_jwt_fallback: bool = False
    jti_replay_cache: JtiReplayCacheProtocol | None = None
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
