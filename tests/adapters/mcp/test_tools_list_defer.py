"""Tests for deferred MCP-MAP-004 tools/list filtering."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from asap.mcp.auth import protect_server
from asap.mcp.auth.config import MCPAuthConfig
from asap.auth.capabilities import CapabilityDefinition, CapabilityGrant, CapabilityRegistry
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
)
from asap.mcp.server import MCPServer
from tests.adapters.mcp.conftest import MCP_TEST_AUDIENCE
from tests.adapters.mcp.helpers import build_auth_config

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

pytestmark = pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")


def test_hide_unauthorized_tools_default_leaves_tools_list_unchanged(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> None:
    """Default ``hide_unauthorized_tools=False`` lists all registered tools unchanged."""
    config = build_auth_config(host_store, agent_store, capability_registry)
    assert config.hide_unauthorized_tools is False
    protected = protect_server(echo_mcp_server, config)
    result = protected._handle_tools_list(None)
    tool_names = {tool["name"] for tool in result["tools"]}
    assert tool_names == set(echo_mcp_server._tools.keys())


def test_hide_unauthorized_tools_true_logs_noop_warning(
    caplog: LogCaptureFixture,
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> None:
    """``hide_unauthorized_tools=True`` logs a warning because MCP-MAP-004 is deferred."""
    config = build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        hide_unauthorized_tools=True,
    )
    with caplog.at_level(logging.WARNING):
        protect_server(echo_mcp_server, config)
    assert "mcp.auth.hide_unauthorized_tools_noop" in caplog.text


@pytest.mark.skip(
    reason="MCP-MAP-004 deferred: stdio tools/list lacks JWT carriage — see design-lock §6"
)
@pytest.mark.asyncio
async def test_hide_unauthorized_tools_filters_unauthorized_when_enabled(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
    register_capability: Callable[..., CapabilityDefinition],
    grant_capability: Callable[..., CapabilityGrant],
) -> None:
    """Document expected MCP-MAP-004 behavior if ``hide_unauthorized_tools`` is implemented."""
    register_capability("echo", description="Echo tool capability")
    grant_capability(agent_session.agent_id, "echo")
    token = mint_agent_jwt(capabilities=["echo"])
    config = MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        enforce_grants=True,
        hide_unauthorized_tools=True,
        expected_audience=MCP_TEST_AUDIENCE,
    )
    protected = protect_server(echo_mcp_server, config)
    _ = token
    result = protected._handle_tools_list(None)
    tool_names = {tool["name"] for tool in result["tools"]}
    assert tool_names == {"echo"}
