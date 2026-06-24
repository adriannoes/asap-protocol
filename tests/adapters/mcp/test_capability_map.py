"""Unit tests for MCP Auth Bridge capability resolution (MCP-MAP-001/002)."""

from __future__ import annotations

from asap.adapters.mcp.capability_map import resolve_capability
from asap.adapters.mcp.config import MCPAuthConfig
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.mcp.server import MCPServer


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


def test_resolve_capability_uses_register_time_metadata() -> None:
    """Register-time capability metadata resolves when config map has no entry."""
    config = _minimal_config()
    server = MCPServer(name="cap-map-test", version="0.1.0")
    server.register_tool(
        "search",
        lambda query="": query,
        {"type": "object", "properties": {"query": {"type": "string"}}},
        capability="web_search",
    )
    assert resolve_capability("search", config, server=server) == "web_search"


def test_resolve_capability_config_map_overrides_register_metadata() -> None:
    """Runtime tool_capability_map overrides register-time metadata."""
    config = _minimal_config(tool_capability_map={"search": "custom_search"})
    server = MCPServer(name="cap-map-test", version="0.1.0")
    server.register_tool(
        "search",
        lambda query="": query,
        {"type": "object", "properties": {"query": {"type": "string"}}},
        capability="web_search",
    )
    assert resolve_capability("search", config, server=server) == "custom_search"
