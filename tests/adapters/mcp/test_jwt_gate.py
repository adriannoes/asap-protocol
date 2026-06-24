"""Unit tests for JWT gate on protect_server (S1)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from asap.adapters.mcp import protect_server
from asap.adapters.mcp.errors import AUTH_REQUIRED, INVALID_TOKEN
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
)
from asap.mcp.protocol import JSONRPCRequest
from asap.mcp.server import MCPServer
from tests.adapters.mcp.helpers import (
    build_auth_config,
    error_text,
    tamper_jwt,
    tool_call_params,
)

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

pytestmark = pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")


@pytest.mark.asyncio
async def test_missing_jwt_returns_auth_required(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
) -> None:
    """Protected tool without JWT returns ``asap:auth_required``."""
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "hi"})
    )
    assert AUTH_REQUIRED in error_text(result)


@pytest.mark.asyncio
async def test_expired_jwt_returns_invalid_token(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expired Agent JWT returns ``asap:invalid_token``."""
    t0 = 1_700_000_000.0
    monkeypatch.setattr(time, "time", lambda: t0)
    token = mint_agent_jwt()
    monkeypatch.setattr(time, "time", lambda: t0 + 120.0)

    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in error_text(result)


@pytest.mark.asyncio
async def test_tampered_jwt_returns_invalid_token(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Tampered Agent JWT returns ``asap:invalid_token``."""
    token = tamper_jwt(mint_agent_jwt())
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in error_text(result)


@pytest.mark.asyncio
async def test_audience_mismatch_returns_invalid_token(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Valid signature with wrong ``aud`` returns ``asap:invalid_token``."""
    token = mint_agent_jwt(aud="urn:asap:agent:wrong-audience")
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in error_text(result)


@pytest.mark.asyncio
async def test_unprotected_server_works_without_jwt(echo_mcp_server: MCPServer) -> None:
    """Unwrapped ``MCPServer`` still invokes tools without JWT (opt-in protection)."""
    result = await echo_mcp_server._handle_tools_call(
        tool_call_params("echo", arguments={"message": "open"})
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "open"


@pytest.mark.asyncio
async def test_public_tool_succeeds_without_jwt(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
) -> None:
    """Tools in ``public_tools`` skip JWT and execute the handler."""
    config = build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        public_tools=frozenset({"echo"}),
    )
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "public"})
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "public"


@pytest.mark.asyncio
async def test_public_tool_ignores_invalid_jwt(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Public tools do not validate JWT; tampered token still succeeds."""
    token = tamper_jwt(mint_agent_jwt())
    config = build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        public_tools=frozenset({"echo"}),
    )
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "ignored-jwt"}, jwt=token)
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "ignored-jwt"


@pytest.mark.asyncio
async def test_public_tool_with_jwt_logs_warning(
    caplog: LogCaptureFixture,
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Public tools log a warning when a JWT is present but not verified."""
    token = mint_agent_jwt()
    config = build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        public_tools=frozenset({"echo"}),
    )
    protected = protect_server(echo_mcp_server, config)
    with caplog.at_level(logging.WARNING):
        result = await protected._handle_tools_call(
            tool_call_params("echo", arguments={"message": "warn"}, jwt=token)
        )
    assert result["isError"] is False
    assert "mcp.tool.public_jwt_ignored" in caplog.text


@pytest.mark.asyncio
async def test_valid_jwt_runs_handler(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Valid Agent JWT on a protected tool delegates to the handler."""
    token = mint_agent_jwt()
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        tool_call_params("echo", arguments={"message": "secure"}, jwt=token)
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "secure"


@pytest.mark.asyncio
async def test_successful_auth_logs_agent_id_not_jwt(
    caplog: LogCaptureFixture,
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
) -> None:
    """Authorized ``tools/call`` logs agent_id and tool_name without the JWT."""
    token = mint_agent_jwt()
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)

    with caplog.at_level(logging.INFO):
        result = await protected._handle_tools_call(
            tool_call_params("echo", arguments={"message": "logged"}, jwt=token)
        )

    assert result["isError"] is False
    assert "mcp.tool.authorized" in caplog.text
    assert agent_session.agent_id in caplog.text
    assert "echo" in caplog.text
    assert token not in caplog.text


@pytest.mark.asyncio
async def test_dispatch_tools_call_enforces_auth(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
) -> None:
    """JSON-RPC ``tools/call`` dispatch path enforces JWT on protected tools."""
    config = build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    req = JSONRPCRequest(
        id=1,
        method="tools/call",
        params=tool_call_params("echo", arguments={"message": "hi"}),
    )
    response_line = await protected._dispatch_request(req)
    assert response_line is not None
    data = json.loads(response_line)
    assert "result" in data
    assert data["result"]["isError"] is True
    assert AUTH_REQUIRED in data["result"]["content"][0]["text"]
