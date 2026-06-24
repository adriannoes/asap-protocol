"""Unit tests for protect_server auth middleware (S1)."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest

from asap.adapters.mcp.auth_middleware import MCPAuthConfig, protect_server
from asap.adapters.mcp.capability_map import resolve_capability
from asap.adapters.mcp.errors import (
    AUTH_REQUIRED,
    CAPABILITY_DENIED,
    CONSTRAINT_VIOLATION,
    INVALID_TOKEN,
)
from asap.auth.capabilities import CapabilityDefinition, CapabilityGrant, CapabilityRegistry
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
)
from asap.mcp.server import MCPServer
from asap.mcp.protocol import JSONRPCRequest
from tests.adapters.mcp.conftest import MCP_TEST_AUDIENCE

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

pytestmark = pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")


def _tool_call_params(
    name: str,
    *,
    arguments: dict[str, Any] | None = None,
    jwt: str | None = None,
) -> dict[str, Any]:
    """Build ``tools/call`` params with optional Agent JWT in ``_meta``."""
    params: dict[str, Any] = {"name": name, "arguments": arguments or {}}
    if jwt is not None:
        params["_meta"] = {"asap_agent_jwt": jwt}
    return params


def _build_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    *,
    public_tools: frozenset[str] = frozenset(),
    enforce_grants: bool = False,
) -> MCPAuthConfig:
    """MCP auth config for middleware tests."""
    return MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        public_tools=public_tools,
        enforce_grants=enforce_grants,
        expected_audience=MCP_TEST_AUDIENCE,
    )


def _build_grant_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> MCPAuthConfig:
    """MCP auth config with grant enforcement enabled (S2)."""
    return _build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        enforce_grants=True,
    )


def _error_text(result: dict[str, Any]) -> str:
    """Extract error text from a ``CallToolResult`` dict."""
    assert result["isError"] is True
    return str(result["content"][0]["text"])


def _tamper_jwt(token: str) -> str:
    """Flip the last character so signature verification fails."""
    suffix = "a" if token[-1] != "a" else "b"
    return token[:-1] + suffix


# --- Failure paths (1.2a) ---


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
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"})
    )
    assert AUTH_REQUIRED in _error_text(result)


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

    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in _error_text(result)


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
    token = _tamper_jwt(mint_agent_jwt())
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in _error_text(result)


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
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert INVALID_TOKEN in _error_text(result)


# --- Success paths (1.2b) ---


@pytest.mark.asyncio
async def test_unprotected_server_works_without_jwt(echo_mcp_server: MCPServer) -> None:
    """Unwrapped ``MCPServer`` still invokes tools without JWT (opt-in protection)."""
    result = await echo_mcp_server._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "open"})
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
    config = _build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        public_tools=frozenset({"echo"}),
    )
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "public"})
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
    token = _tamper_jwt(mint_agent_jwt())
    config = _build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        public_tools=frozenset({"echo"}),
    )
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "ignored-jwt"}, jwt=token)
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "ignored-jwt"


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
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "secure"}, jwt=token)
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
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)

    with caplog.at_level(logging.INFO):
        result = await protected._handle_tools_call(
            _tool_call_params("echo", arguments={"message": "logged"}, jwt=token)
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
    config = _build_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    req = JSONRPCRequest(
        id=1,
        method="tools/call",
        params=_tool_call_params("echo", arguments={"message": "hi"}),
    )
    response_line = await protected._dispatch_request(req)
    assert response_line is not None
    data = json.loads(response_line)
    assert "result" in data
    assert data["result"]["isError"] is True
    assert AUTH_REQUIRED in data["result"]["content"][0]["text"]


# --- S2 capability mapping (1.2) & startup validation (1.3); Agent D: green when impl lands ---

_BRIDGE_TOOL_CAPABILITIES_ATTR = "_bridge_tool_capabilities"


def _s2_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    **kwargs: object,
) -> MCPAuthConfig:
    """MCP auth config for S2 mapping/validation tests (no grant enforcement)."""
    return MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        enforce_grants=False,
        expected_audience=MCP_TEST_AUDIENCE,
        **kwargs,
    )


def test_protect_server_honors_register_time_capability_metadata(
    search_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Bridge registry from register-time metadata is used when config map is empty."""
    # Agent D: green when 1.2 impl lands
    register_capability("web_search", description="Web search capability")
    setattr(
        search_mcp_server,
        _BRIDGE_TOOL_CAPABILITIES_ATTR,
        {"search": "web_search"},
    )
    config = _s2_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(search_mcp_server, config)
    assert getattr(protected, "_startup_tools_validated", False) is True
    assert resolve_capability("search", config) == "web_search"


def test_config_tool_capability_map_overrides_register_time_metadata(
    search_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Runtime ``tool_capability_map`` overrides register-time bridge metadata."""
    # Agent D: green when 1.2 impl lands
    register_capability("custom_search", description="Custom search capability")
    setattr(
        search_mcp_server,
        _BRIDGE_TOOL_CAPABILITIES_ATTR,
        {"search": "web_search"},
    )
    config = _s2_auth_config(
        host_store,
        agent_store,
        capability_registry,
        tool_capability_map={"search": "custom_search"},
        validate_tools_at_startup=True,
    )
    protected = protect_server(search_mcp_server, config)
    assert getattr(protected, "_startup_tools_validated", False) is True
    assert resolve_capability("search", config) == "custom_search"


def test_validate_tools_at_startup_fails_on_empty_resolved_capability(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Startup validation rejects tools that resolve to an empty capability name."""
    # Agent D: green when 1.3 impl lands
    register_capability("echo", description="Echo capability")
    config = _s2_auth_config(
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
    # Agent D: green when 1.3 impl lands
    config = _s2_auth_config(
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
    # Agent D: green when 1.3 impl lands
    register_capability("echo", description="Echo tool capability")
    config = _s2_auth_config(
        host_store,
        agent_store,
        capability_registry,
        validate_tools_at_startup=True,
    )
    protected = protect_server(echo_mcp_server, config)
    assert protected is not None
    assert getattr(protected, "_startup_tools_validated", False) is True


def test_validate_tools_at_startup_succeeds_with_explicit_capability_map(
    search_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Startup validation passes when mapped capability exists in the registry."""
    # Agent D: green when 1.3 impl lands
    register_capability("web_search", description="Web search capability")
    config = _s2_auth_config(
        host_store,
        agent_store,
        capability_registry,
        tool_capability_map={"search": "web_search"},
        validate_tools_at_startup=True,
    )
    protected = protect_server(search_mcp_server, config)
    assert protected is not None
    assert getattr(protected, "_startup_tools_validated", False) is True
    assert capability_registry.describe("web_search") is not None


# --- S2 grant enforcement (2.1, 2.2) ---


@pytest.mark.asyncio
async def test_denied_grant_returns_capability_denied(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
    register_capability: Callable[..., CapabilityDefinition],
) -> None:
    """Valid JWT without registry grant returns ``asap:capability_denied``."""
    register_capability("echo", description="Echo tool capability")
    token = mint_agent_jwt(capabilities=["echo"])
    config = _build_grant_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert CAPABILITY_DENIED in _error_text(result)


@pytest.mark.asyncio
async def test_jwt_capability_claim_mismatch_returns_capability_denied(
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
    """Active grant but JWT missing capability claim returns ``asap:capability_denied``."""
    register_capability("echo", description="Echo tool capability")
    grant_capability(agent_session.agent_id, "echo")
    token = mint_agent_jwt()
    config = _build_grant_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "hi"}, jwt=token)
    )
    assert CAPABILITY_DENIED in _error_text(result)


@pytest.mark.asyncio
async def test_grant_and_jwt_capability_succeeds(
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
    """Active grant and matching JWT capability claim invoke the handler."""
    register_capability("echo", description="Echo tool capability")
    grant_capability(agent_session.agent_id, "echo")
    token = mint_agent_jwt(capabilities=["echo"])
    config = _build_grant_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params("echo", arguments={"message": "granted"}, jwt=token)
    )
    assert result["isError"] is False
    assert result["content"][0]["text"] == "granted"


@pytest.mark.asyncio
async def test_constraint_violation_returns_constraint_violation(
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
    """Arguments exceeding grant ``max`` constraint return ``asap:constraint_violation``."""
    register_capability("echo", description="Echo tool capability")
    grant_capability(
        agent_session.agent_id,
        "echo",
        constraints={"tokens": {"max": 100}},
    )
    token = mint_agent_jwt(capabilities=["echo"])
    config = _build_grant_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(echo_mcp_server, config)
    result = await protected._handle_tools_call(
        _tool_call_params(
            "echo",
            arguments={"message": "hi", "tokens": 150},
            jwt=token,
        )
    )
    assert CONSTRAINT_VIOLATION in _error_text(result)


# --- S2 optional tools/list filtering (3.1) — MCP-MAP-004 deferred per design-lock §6 ---


def test_hide_unauthorized_tools_default_leaves_tools_list_unchanged(
    echo_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> None:
    """Default ``hide_unauthorized_tools=False`` lists all registered tools unchanged."""
    config = _build_auth_config(host_store, agent_store, capability_registry)
    assert config.hide_unauthorized_tools is False
    protected = protect_server(echo_mcp_server, config)
    result = protected._handle_tools_list(None)
    tool_names = {tool["name"] for tool in result["tools"]}
    assert tool_names == set(echo_mcp_server._tools.keys())


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
    """Document expected MCP-MAP-004 behavior if ``hide_unauthorized_tools`` is implemented.

    When stdio ``tools/list`` can carry an Agent JWT (transport TBD), enabling
    ``hide_unauthorized_tools`` should return only tools the caller may invoke:
    ``public_tools``, tools with an active grant, and a matching JWT
    ``capabilities`` claim. Unauthorized tools must be omitted from the list.
    """
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
    # Future: pass JWT via list-request context once stdio carriage is defined.
    _ = token
    result = protected._handle_tools_list(None)
    tool_names = {tool["name"] for tool in result["tools"]}
    assert tool_names == {"echo"}
