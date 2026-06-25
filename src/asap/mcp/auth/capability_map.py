"""Tool-to-capability resolution for MCP Auth Bridge (v2.5.0)."""

from __future__ import annotations

from asap.auth.capabilities import ConstraintViolation
from asap.mcp.auth.config import MCPAuthConfig
from asap.mcp.server import MCPServer


def resolve_capability(
    tool_name: str,
    config: MCPAuthConfig,
    *,
    server: MCPServer | None = None,
) -> str:
    """Resolve an MCP tool name to an ASAP capability name.

    Resolution order (MCP-MAP-001, MCP-MAP-002):

    1. ``config.tool_capability_map`` (explicit runtime override)
    2. ``server.get_tool_capability(tool_name)`` when register-time metadata is set
    3. Identity default: ``tool_name`` unchanged

    Args:
        tool_name: Registered MCP tool name from ``tools/call``.
        config: MCP auth configuration including capability maps.
        server: MCP server providing register-time capability metadata.

    Returns:
        ASAP capability name used for grant checks.

    Example:
        >>> from asap.mcp.auth.config import MCPAuthConfig
        >>> from asap.auth.capabilities import CapabilityRegistry
        >>> from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
        >>> from asap.mcp.server import MCPServer
        >>> agents = InMemoryAgentStore()
        >>> config = MCPAuthConfig(
        ...     host_store=InMemoryHostStore(agent_store=agents),
        ...     agent_store=agents,
        ...     capability_registry=CapabilityRegistry(),
        ...     tool_capability_map={"search": "web_search"},
        ... )
        >>> resolve_capability("search", config)
        'web_search'
        >>> resolve_capability("echo", config)
        'echo'
    """
    if tool_name in config.tool_capability_map:
        return config.tool_capability_map[tool_name]
    if server is not None:
        registered = server.get_tool_capability(tool_name)
        if registered is not None:
            return registered
    return tool_name


def format_constraint_violations(violations: list[ConstraintViolation]) -> str:
    """Format grant constraint violations for MCP ``tools/call`` error detail.

    Args:
        violations: Constraint failures from :meth:`CapabilityRegistry.check_grant`.

    Returns:
        Human-readable detail string joined with ``; ``.

    Example:
        >>> from asap.auth.capabilities import ConstraintViolation
        >>> format_constraint_violations([
        ...     ConstraintViolation("tokens", "max", 100, 150, "tokens: 150 exceeds maximum 100"),
        ... ])
        'tokens: 150 exceeds maximum 100'
    """
    return "; ".join(v.message for v in violations)
