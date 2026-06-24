"""Shared fixtures for MCP auth middleware tests (S1).

Provides host/agent identity, JWT minting, and a minimal ``MCPServer`` with an
``echo`` tool so auth-path tests avoid duplicating crypto setup.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asap.auth.agent_jwt import create_agent_jwt
from asap.auth.capabilities import (
    CapabilityDefinition,
    CapabilityGrant,
    CapabilityRegistry,
    GrantStatus,
)
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
    jwk_thumbprint_sha256,
)
from asap.mcp.server import MCPServer
from tests.crypto.jwk_helpers import ed25519_public_jwk

pytestmark = pytest.mark.filterwarnings("ignore:EdDSA is deprecated:UserWarning")

MCP_TEST_AUDIENCE = "urn:asap:agent:mcp-test"

_ECHO_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "tokens": {"type": "integer"},
    },
    "additionalProperties": False,
}

_SEARCH_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"query": {"type": "string"}},
    "additionalProperties": False,
}


@pytest.fixture
def host_sk() -> Ed25519PrivateKey:
    """Ed25519 private key for the test host identity."""
    return Ed25519PrivateKey.generate()


@pytest.fixture
def agent_sk() -> Ed25519PrivateKey:
    """Ed25519 private key for the test agent session."""
    return Ed25519PrivateKey.generate()


@pytest.fixture
def agent_store() -> InMemoryAgentStore:
    """In-memory agent session store."""
    return InMemoryAgentStore()


@pytest.fixture
def host_store(agent_store: InMemoryAgentStore) -> InMemoryHostStore:
    """In-memory host store linked to ``agent_store``."""
    return InMemoryHostStore(agent_store=agent_store)


@pytest.fixture
async def host_identity(
    host_sk: Ed25519PrivateKey,
    host_store: InMemoryHostStore,
) -> HostIdentity:
    """Registered active host identity persisted in ``host_store``."""
    now = datetime.now(timezone.utc)
    identity = HostIdentity(
        host_id="mcp-test-host",
        public_key=ed25519_public_jwk(host_sk),
        status="active",
        created_at=now,
        updated_at=now,
    )
    await host_store.save(identity)
    return identity


@pytest.fixture
async def agent_session(
    agent_sk: Ed25519PrivateKey,
    host_identity: HostIdentity,
    agent_store: InMemoryAgentStore,
) -> AgentSession:
    """Registered active agent session persisted in ``agent_store``."""
    now = datetime.now(timezone.utc)
    session = AgentSession(
        agent_id="urn:asap:agent:mcp-test-agent",
        host_id=host_identity.host_id,
        public_key=ed25519_public_jwk(agent_sk),
        mode="delegated",
        status="active",
        created_at=now,
        activated_at=now,
    )
    await agent_store.save(session)
    return session


@pytest.fixture
def capability_registry() -> CapabilityRegistry:
    """Empty capability registry for MCP auth config wiring."""
    return CapabilityRegistry()


@pytest.fixture
def seed_capability_definition() -> Callable[..., CapabilityDefinition]:
    """Register a capability definition on a registry (S2 startup validation).

    Example:
        >>> cap = seed_capability_definition(registry, "echo", "Echo tool capability")
    """

    def _seed(
        registry: CapabilityRegistry,
        name: str,
        description: str | None = None,
    ) -> CapabilityDefinition:
        definition = CapabilityDefinition(
            name=name,
            description=description or f"Test capability {name}",
        )
        registry.register(definition)
        return definition

    return _seed


@pytest.fixture
def register_capability(
    capability_registry: CapabilityRegistry,
) -> Callable[..., CapabilityDefinition]:
    """Register a capability definition (``describe`` / startup validation).

    Example:
        >>> register_capability("echo", description="Echo tool capability")
    """

    def _register(
        name: str,
        *,
        description: str = "Test capability",
        input_schema: dict[str, Any] | None = None,
        output_schema: dict[str, Any] | None = None,
        location: str | None = None,
    ) -> CapabilityDefinition:
        definition = CapabilityDefinition(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            location=location,
        )
        capability_registry.register(definition)
        return definition

    return _register


@pytest.fixture
def grant_capability(
    capability_registry: CapabilityRegistry,
) -> Callable[..., CapabilityGrant]:
    """Seed an active grant for tests with ``enforce_grants=True``.

    Example:
        >>> grant_capability(agent_session.agent_id, "echo")
        >>> grant_capability(
        ...     agent_session.agent_id,
        ...     "echo",
        ...     constraints={"tokens": {"max": 100}},
        ... )
    """

    def _grant(
        agent_id: str,
        capability: str,
        *,
        constraints: dict[str, Any] | None = None,
        status: GrantStatus = "active",
        reason: str | None = None,
        granted_by: str | None = None,
    ) -> CapabilityGrant:
        return capability_registry.grant(
            agent_id,
            capability,
            constraints=constraints,
            status=status,
            reason=reason,
            granted_by=granted_by,
        )

    return _grant


@pytest.fixture
def mint_agent_jwt(
    host_sk: Ed25519PrivateKey,
    agent_sk: Ed25519PrivateKey,
    host_identity: HostIdentity,
    agent_session: AgentSession,
) -> Callable[..., str]:
    """Mint Agent JWTs for the test host/agent pair.

    Example:
        >>> token = mint_agent_jwt()
        >>> token = mint_agent_jwt(aud="custom-aud", capabilities=["echo"])
    """
    host_thumbprint = jwk_thumbprint_sha256(host_identity.public_key)

    def _mint(
        *,
        agent_id: str | None = None,
        aud: str | list[str] | None = None,
        capabilities: list[str] | None = None,
    ) -> str:
        return create_agent_jwt(
            agent_sk,
            host_thumbprint=host_thumbprint,
            agent_id=agent_id or agent_session.agent_id,
            aud=aud if aud is not None else MCP_TEST_AUDIENCE,
            capabilities=capabilities,
        )

    return _mint


@pytest.fixture
def echo_mcp_server() -> MCPServer:
    """Minimal MCP server with a single ``echo`` tool registered."""
    server = MCPServer(name="mcp-auth-test", version="0.1.0")
    server.register_tool(
        "echo",
        lambda message="", tokens=0: message,
        _ECHO_INPUT_SCHEMA,
        description="Echo input message",
    )
    return server


@pytest.fixture
def search_mcp_server() -> MCPServer:
    """Minimal MCP server with a ``search`` tool for capability-map tests."""
    server = MCPServer(name="mcp-auth-test", version="0.1.0")
    server.register_tool(
        "search",
        lambda query="": query,
        _SEARCH_INPUT_SCHEMA,
        description="Search the web",
    )
    return server
