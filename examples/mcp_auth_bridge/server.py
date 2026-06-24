"""MCP Auth Bridge reference example (v2.5.0).

Protected MCP server with a public ``echo`` tool and a gated ``secure_action`` tool.
Demonstrates ``protect_server``, in-memory identity stores, capability grants, and
Agent JWT extraction from ``tools/call`` ``_meta.asap_agent_jwt``.

Run:
    uv run python examples/mcp_auth_bridge/server.py
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from asap.adapters.mcp import MCPAuthConfig, protect_server
from asap.auth.agent_jwt import create_agent_jwt
from asap.auth.capabilities import CapabilityDefinition, CapabilityRegistry
from asap.auth.identity import (
    AgentSession,
    HostIdentity,
    InMemoryAgentStore,
    InMemoryHostStore,
    jwk_thumbprint_sha256,
)
from asap.mcp.server import MCPServer
from asap.adapters.mcp.config import MCP_COMPLIANCE_ENV_VAR as COMPLIANCE_ENV_VAR

DEMO_HOST_ID = "mcp-auth-bridge-host"
DEMO_AGENT_ID = "urn:asap:agent:mcp-auth-bridge-demo"
DEMO_AUDIENCE = "urn:asap:agent:mcp-auth-bridge"
_COMPLIANCE_FORBIDDEN_ACTION = "forbidden-action"

_ECHO_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"message": {"type": "string"}},
    "additionalProperties": False,
}

_SECURE_ACTION_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"action": {"type": "string"}},
    "additionalProperties": False,
}


def _ed25519_public_jwk(private_key: Ed25519PrivateKey) -> dict[str, str]:
    """Derive a public JWK (OKP / Ed25519) from an Ed25519 private key."""
    raw = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    x = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return {"kty": "OKP", "crv": "Ed25519", "x": x}


@dataclass(frozen=True)
class DemoIdentity:
    """Runtime-generated host/agent keys and minted demo JWT."""

    host_sk: Ed25519PrivateKey
    agent_sk: Ed25519PrivateKey
    host_identity: HostIdentity
    agent_session: AgentSession
    demo_jwt: str


async def _seed_identity(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
) -> DemoIdentity:
    """Register host/agent identities, capability defs, and an active grant."""
    host_sk = Ed25519PrivateKey.generate()
    agent_sk = Ed25519PrivateKey.generate()
    now = datetime.now(timezone.utc)

    host_identity = HostIdentity(
        host_id=DEMO_HOST_ID,
        public_key=_ed25519_public_jwk(host_sk),
        status="active",
        created_at=now,
        updated_at=now,
    )
    await host_store.save(host_identity)

    agent_session = AgentSession(
        agent_id=DEMO_AGENT_ID,
        host_id=host_identity.host_id,
        public_key=_ed25519_public_jwk(agent_sk),
        mode="delegated",
        status="active",
        created_at=now,
        activated_at=now,
    )
    await agent_store.save(agent_session)

    capability_registry.register(
        CapabilityDefinition(
            name="secure_action",
            description="Execute a protected MCP action",
        )
    )
    compliance_mode = os.environ.get(COMPLIANCE_ENV_VAR) == "1"
    if compliance_mode:
        capability_registry.grant(
            DEMO_AGENT_ID,
            "secure_action",
            constraints={"action": {"not_in": [_COMPLIANCE_FORBIDDEN_ACTION]}},
        )
    else:
        capability_registry.grant(DEMO_AGENT_ID, "secure_action")

    host_thumbprint = jwk_thumbprint_sha256(host_identity.public_key)
    demo_jwt = create_agent_jwt(
        agent_sk,
        host_thumbprint=host_thumbprint,
        agent_id=DEMO_AGENT_ID,
        aud=DEMO_AUDIENCE,
        capabilities=["secure_action"],
    )

    return DemoIdentity(
        host_sk=host_sk,
        agent_sk=agent_sk,
        host_identity=host_identity,
        agent_session=agent_session,
        demo_jwt=demo_jwt,
    )


async def build_protected_server() -> tuple[MCPServer, DemoIdentity]:
    """Wire in-memory stores, tools, and ``protect_server`` for the demo."""
    agent_store = InMemoryAgentStore()
    host_store = InMemoryHostStore(agent_store=agent_store)
    capability_registry = CapabilityRegistry()
    identity = await _seed_identity(host_store, agent_store, capability_registry)

    base = MCPServer(
        name="mcp-auth-bridge",
        version="0.1.0",
        description="ASAP MCP Auth Bridge reference example",
    )
    base.register_tool(
        "echo",
        lambda message="": message,
        _ECHO_INPUT_SCHEMA,
        description="Public echo tool (no JWT required)",
    )
    base.register_tool(
        "secure_action",
        lambda action="": f"executed: {action}",
        _SECURE_ACTION_INPUT_SCHEMA,
        description="Protected action (requires Agent JWT + grant)",
        capability="secure_action",
    )

    config = MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        public_tools=frozenset({"echo"}),
        enforce_grants=True,
        allow_env_jwt_fallback=True,
        expected_audience=DEMO_AUDIENCE,
    )
    protected = protect_server(base, config)
    return protected, identity


def _print_startup_instructions(identity: DemoIdentity) -> None:
    """Print reviewer-facing JWT and ``tools/call`` guidance on stderr."""
    lines = [
        "",
        "=== MCP Auth Bridge example ===",
        f"Agent ID: {identity.agent_session.agent_id}",
        f"Audience: {DEMO_AUDIENCE}",
        "",
        "Public tool: echo (no JWT)",
        "Protected tool: secure_action (JWT + active grant required)",
        "",
        "Minted demo Agent JWT (60s TTL, capabilities=['secure_action']):",
        identity.demo_jwt,
        "",
        "Pass JWT on tools/call:",
        '  params._meta.asap_agent_jwt = "<token>"',
        "",
        "Dev-only env fallback (allow_env_jwt_fallback=True):",
        "  export ASAP_AGENT_JWT='<token>'",
        "",
        "Listening on stdio (JSON-RPC, one message per line).",
        "",
    ]
    print("\n".join(lines), file=sys.stderr, flush=True)
    if os.environ.get(COMPLIANCE_ENV_VAR) == "1":
        host_thumbprint = jwk_thumbprint_sha256(identity.host_identity.public_key)
        wrong_jwt = create_agent_jwt(
            identity.agent_sk,
            host_thumbprint=host_thumbprint,
            agent_id=DEMO_AGENT_ID,
            aud=DEMO_AUDIENCE,
            capabilities=["unrelated_capability"],
        )
        payload = {
            "profile": "mcp-auth-bridge",
            "valid_jwt": identity.demo_jwt,
            "wrong_capability_jwt": wrong_jwt,
            "constraint_violation_action": _COMPLIANCE_FORBIDDEN_ACTION,
        }
        print(f"ASAP_COMPLIANCE_JSON:{json.dumps(payload)}", file=sys.stderr, flush=True)


async def _run_stdio() -> None:
    server, identity = await build_protected_server()
    _print_startup_instructions(identity)
    await server.run_stdio()


def main() -> None:
    """Parse CLI args and start the protected MCP server over stdio."""
    parser = argparse.ArgumentParser(
        description="MCP Auth Bridge reference server (public echo + protected secure_action)",
    )
    parser.parse_args()
    asyncio.run(_run_stdio())


if __name__ == "__main__":
    main()
