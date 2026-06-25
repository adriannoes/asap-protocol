"""Shared helpers for MCP auth adapter tests."""

from __future__ import annotations

from typing import Any

from asap.mcp.auth.config import MCPAuthConfig
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from tests.adapters.mcp.conftest import MCP_TEST_AUDIENCE


def tool_call_params(
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


def build_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    *,
    public_tools: frozenset[str] = frozenset(),
    enforce_grants: bool = False,
    **kwargs: object,
) -> MCPAuthConfig:
    """MCP auth config for middleware tests."""
    return MCPAuthConfig(
        host_store=host_store,
        agent_store=agent_store,
        capability_registry=capability_registry,
        public_tools=public_tools,
        enforce_grants=enforce_grants,
        expected_audience=MCP_TEST_AUDIENCE,
        **kwargs,
    )


def build_grant_auth_config(
    host_store: InMemoryHostStore,
    agent_store: InMemoryAgentStore,
    capability_registry: CapabilityRegistry,
    **kwargs: object,
) -> MCPAuthConfig:
    """MCP auth config with grant enforcement enabled."""
    return build_auth_config(
        host_store,
        agent_store,
        capability_registry,
        enforce_grants=True,
        **kwargs,
    )


def error_text(result: dict[str, Any]) -> str:
    """Extract error text from a ``CallToolResult`` dict."""
    assert result["isError"] is True
    return str(result["content"][0]["text"])


def tamper_jwt(token: str) -> str:
    """Flip the last character so signature verification fails."""
    suffix = "a" if token[-1] != "a" else "b"
    return token[:-1] + suffix
