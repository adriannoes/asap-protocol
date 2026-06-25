"""Per-tool capability URN isolation regression (S3 Wave C Task 4.1).

Mirrors the S2 #240 ``TestResolveAndCacheSkill`` guard: two tools with
DIFFERENT capability URNs registered on one shared ``MCPServer`` /
``ProtectedMCPServer`` must not inherit each other's capability grant on
``tools/call``. The ``ToolRegistration`` dataclass keeps capability metadata
per-tool-instance (attribute access, not a hoisted shared field) so a URN
registered for tool A can never satisfy the grant check for tool B.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from asap.mcp.auth import protect_server
from asap.mcp.auth.errors import CAPABILITY_DENIED
from asap.auth.capabilities import CapabilityDefinition, CapabilityGrant, CapabilityRegistry
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
)
from asap.mcp.server import MCPServer, ToolRegistration
from tests.adapters.mcp.helpers import (
    build_grant_auth_config,
    error_text,
    tool_call_params,
)

pytestmark = pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")

_CAP_A = "urn:asap:cap:alpha"
_CAP_B = "urn:asap:cap:beta"

_ALPHA_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "additionalProperties": False,
}
_BETA_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"value": {"type": "string"}},
    "additionalProperties": False,
}


@pytest.fixture
def two_urn_mcp_server() -> MCPServer:
    """One server with two tools carrying distinct per-tool capability URNs."""
    server = MCPServer(name="mcp-per-urn-test", version="0.1.0")
    server.register_tool(
        "alpha",
        lambda value="": value,
        _ALPHA_SCHEMA,
        description="Alpha tool",
        capability=_CAP_A,
    )
    server.register_tool(
        "beta",
        lambda value="": value,
        _BETA_SCHEMA,
        description="Beta tool",
        capability=_CAP_B,
    )
    return server


@pytest.mark.asyncio
async def test_tool_registration_keeps_per_urn_capability_metadata(
    two_urn_mcp_server: MCPServer,
) -> None:
    """Each ``ToolRegistration`` exposes its own capability URN by attribute access."""
    alpha = two_urn_mcp_server._tools["alpha"]
    beta = two_urn_mcp_server._tools["beta"]
    assert isinstance(alpha, ToolRegistration)
    assert isinstance(beta, ToolRegistration)
    assert alpha.capabilities == _CAP_A
    assert beta.capabilities == _CAP_B
    assert two_urn_mcp_server.get_tool_capability("alpha") == _CAP_A
    assert two_urn_mcp_server.get_tool_capability("beta") == _CAP_B


@pytest.mark.asyncio
async def test_tool_b_does_not_inherit_tool_a_capability_grant(
    two_urn_mcp_server: MCPServer,
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    host_identity: HostIdentity,
    agent_session: AgentSession,
    mint_agent_jwt: Callable[..., str],
    register_capability: Callable[..., CapabilityDefinition],
    grant_capability: Callable[..., CapabilityGrant],
) -> None:
    """``tools/call`` for tool B must be denied when only tool A's URN is granted.

    The agent holds an active grant AND a JWT ``capabilities`` claim for
    ``_CAP_A`` only. Calling ``beta`` (URN ``_CAP_B``) must return
    ``asap:capability_denied`` — proving the per-tool capability metadata on
    ``ToolRegistration`` is isolated and tool B did not inherit tool A's grant.
    """
    register_capability(_CAP_A, description="Alpha capability")
    grant_capability(agent_session.agent_id, _CAP_A)
    token = mint_agent_jwt(capabilities=[_CAP_A])
    config = build_grant_auth_config(host_store, agent_store, capability_registry)
    protected = protect_server(two_urn_mcp_server, config)

    alpha_result = await protected._handle_tools_call(
        tool_call_params("alpha", arguments={"value": "a-ok"}, jwt=token)
    )
    assert alpha_result["isError"] is False
    assert alpha_result["content"][0]["text"] == "a-ok"

    beta_result = await protected._handle_tools_call(
        tool_call_params("beta", arguments={"value": "b"}, jwt=token)
    )
    assert CAPABILITY_DENIED in error_text(beta_result)
    denied_text = error_text(beta_result)
    assert _CAP_B in denied_text
    assert _CAP_A not in denied_text
