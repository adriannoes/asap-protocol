"""Unit tests for protect_server stub (S0)."""

from __future__ import annotations

import pytest

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, protect_server
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.mcp.server import MCPServer


def test_protect_server_raises_not_implemented() -> None:
    """protect_server stub raises NotImplementedError until S1."""
    agents = InMemoryAgentStore()
    server = MCPServer(name="test")
    config = MCPAuthConfig(
        host_store=InMemoryHostStore(agent_store=agents),
        agent_store=agents,
        capability_registry=CapabilityRegistry(),
    )
    with pytest.raises(NotImplementedError, match="sprint S1"):
        protect_server(server, config)
