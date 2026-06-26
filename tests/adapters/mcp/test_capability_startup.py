"""Unit tests for capability mapping and startup validation (S2)."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from asap.mcp.auth import protect_server
from asap.mcp.auth.capability_map import resolve_capability
from asap.mcp.auth.config import MCPAuthConfig
from asap.auth.capabilities import CapabilityDefinition, CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.mcp.server import MCPServer
from tests.adapters.mcp.conftest import MCP_TEST_AUDIENCE


def _mapping_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    **kwargs: object,
) -> MCPAuthConfig:
    """MCP auth config for mapping/validation tests (no grant enforcement)."""
    return MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        enforce_grants=False,
        expected_audience=MCP_TEST_AUDIENCE,
        **kwargs,
    )


def test_protect_server_honors_register_time_capability_metadata(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Register-time capability metadata is used when config map is empty."""
    register_capability("web_search", description="Web search capability")
    server = MCPServer(name="mapping-test", version="0.1.0")
    server.register_tool(
        "search",
        lambda query="": query,
        {"type": "object", "properties": {"query": {"type": "string"}}},
        capability="web_search",
    )
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(server, config)
    assert resolve_capability("search", config, server=protected) == "web_search"


def test_config_tool_capability_map_overrides_register_time_metadata(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Runtime ``tool_capability_map`` overrides register-time metadata."""
    register_capability("custom_search", description="Custom search capability")
    server = MCPServer(name="mapping-test", version="0.1.0")
    server.register_tool(
        "search",
        lambda query="": query,
        {"type": "object", "properties": {"query": {"type": "string"}}},
        capability="web_search",
    )
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        tool_capability_map={"search": "custom_search"},
        validate_tools_at_startup=True,
    )
    protected = protect_server(server, config)
    assert resolve_capability("search", config, server=protected) == "custom_search"


def test_protected_register_tool_stores_capability_metadata(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """``ProtectedMCPServer.register_tool(..., capability=...)`` records metadata."""
    register_capability("web_search", description="Web search capability")
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(MCPServer(name="register-test", version="0.1.0"), config)
    protected.register_tool(
        "search",
        lambda query="": query,
        {"type": "object", "properties": {"query": {"type": "string"}}},
        capability="web_search",
    )
    assert protected.get_tool_capability("search") == "web_search"
    assert resolve_capability("search", config, server=protected) == "web_search"


def test_validate_tools_at_startup_fails_on_empty_resolved_capability(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Startup validation rejects tools that resolve to an empty capability name."""
    register_capability("echo", description="Echo capability")
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        tool_capability_map={"echo": ""},
        validate_tools_at_startup=True,
    )
    with pytest.raises(ValueError, match="empty capability|capability"):
        protect_server(echo_mcp_server, config)


def test_validate_tools_at_startup_fails_on_unknown_capability(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> None:
    """Startup validation rejects tools whose resolved capability is not in the registry."""
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    assert capability_registry.describe("echo") is None
    with pytest.raises(ValueError, match="unknown capability|not registered|describe"):
        protect_server(echo_mcp_server, config)


def test_validate_tools_at_startup_succeeds_with_registered_capability(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Startup validation passes when every tool resolves to a known capability."""
    register_capability("echo", description="Echo tool capability")
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(echo_mcp_server, config)
    assert protected is not None


def test_validate_tools_at_startup_succeeds_with_explicit_capability_map(
    search_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Startup validation passes when mapped capability exists in the registry."""
    register_capability("web_search", description="Web search capability")
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        tool_capability_map={"search": "web_search"},
        validate_tools_at_startup=True,
    )
    protected = protect_server(search_mcp_server, config)
    assert protected is not None
    assert capability_registry.describe("web_search") is not None


def test_mcp_server_get_tool_capability() -> None:
    """``MCPServer.get_tool_capability`` returns register-time metadata."""
    server = MCPServer(name="tool-cap", version="0.1.0")
    server.register_tool(
        "echo",
        lambda message="": message,
        {"type": "object", "properties": {"message": {"type": "string"}}},
        capability="echo_cap",
    )
    assert server.get_tool_capability("echo") == "echo_cap"
    assert server.get_tool_capability("missing") is None


def test_register_tool_validates_incrementally_not_full_rescan(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Each ``register_tool`` validates only the new tool (O(1) per registration)."""
    register_capability("cap_a", description="Capability A")
    register_capability("cap_b", description="Capability B")
    config = _mapping_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(MCPServer(name="incremental", version="0.1.0"), config)
    protected.register_tool(
        "tool_a",
        lambda: "a",
        {"type": "object", "additionalProperties": False},
        capability="cap_a",
    )
    protected.register_tool(
        "tool_b",
        lambda: "b",
        {"type": "object", "additionalProperties": False},
        capability="cap_b",
    )
    assert protected.get_tool_capability("tool_a") == "cap_a"
    assert protected.get_tool_capability("tool_b") == "cap_b"
