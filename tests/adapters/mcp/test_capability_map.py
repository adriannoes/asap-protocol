"""Unit tests for resolve_capability (MCP-MAP-001)."""

from __future__ import annotations

from asap.adapters.mcp.auth_middleware import MCPAuthConfig
from asap.adapters.mcp.capability_map import resolve_capability
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore


def _minimal_config(**kwargs: object) -> MCPAuthConfig:
    agents = InMemoryAgentStore()
    return MCPAuthConfig(
        host_store=InMemoryHostStore(agent_store=agents),
        agent_store=agents,
        capability_registry=CapabilityRegistry(),
        **kwargs,
    )


def test_resolve_capability_default_identity() -> None:
    """Tool not in map resolves to the tool name (identity default)."""
    config = _minimal_config()
    assert resolve_capability("echo", config) == "echo"


def test_resolve_capability_explicit_map_override() -> None:
    """Explicit tool_capability_map entry overrides identity default."""
    config = _minimal_config(tool_capability_map={"search": "web_search"})
    assert resolve_capability("search", config) == "web_search"
    assert resolve_capability("other", config) == "other"


def test_resolve_capability_empty_map_uses_identity() -> None:
    """Empty tool_capability_map still uses identity default."""
    config = _minimal_config(tool_capability_map={})
    assert resolve_capability("read_file", config) == "read_file"


# --- S2 bridge registry precedence (MCP-MAP-002); Agent D: green when 1.2 impl lands ---


def test_resolve_capability_uses_bridge_registry_when_config_map_empty() -> None:
    """Register-time bridge metadata resolves when config map has no entry."""
    config = _minimal_config()
    # Agent D: ``from_server`` populates bridge metadata on config after MCP-MAP-002.
    object.__setattr__(
        config,
        "bridge_tool_capability_map",
        {"search": "web_search"},
    )
    assert resolve_capability("search", config) == "web_search"


def test_resolve_capability_config_map_overrides_bridge_registry() -> None:
    """Explicit ``tool_capability_map`` wins over register-time bridge metadata."""
    config = _minimal_config(tool_capability_map={"search": "custom_search"})
    object.__setattr__(
        config,
        "bridge_tool_capability_map",
        {"search": "web_search"},
    )
    assert resolve_capability("search", config) == "custom_search"
