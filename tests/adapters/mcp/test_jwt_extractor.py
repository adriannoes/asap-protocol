"""Unit tests for default_jwt_extractor and resolve_jwt_extractor."""

from __future__ import annotations

from pytest import MonkeyPatch

from asap.adapters.mcp.config import MCPAuthConfig, resolve_jwt_extractor
from asap.adapters.mcp.jwt_extractor import default_jwt_extractor
from asap.auth.capabilities import CapabilityRegistry
from asap.auth.identity import InMemoryAgentStore, InMemoryHostStore
from asap.mcp.protocol import CallToolRequestParams


def _minimal_config(*, allow_env_jwt_fallback: bool = False) -> MCPAuthConfig:
    agents = InMemoryAgentStore()
    return MCPAuthConfig(
        host_store=InMemoryHostStore(agent_store=agents),
        agent_store=agents,
        capability_registry=CapabilityRegistry(),
        allow_env_jwt_fallback=allow_env_jwt_fallback,
    )


def test_default_jwt_extractor_reads_meta() -> None:
    """Extractor returns asap_agent_jwt from _meta."""
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "arguments": {},
            "_meta": {"asap_agent_jwt": "agent-jwt-from-meta"},
        }
    )
    assert default_jwt_extractor(params) == "agent-jwt-from-meta"


def test_default_jwt_extractor_strips_whitespace() -> None:
    """Extractor strips leading and trailing whitespace from meta token."""
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": "  trimmed-token  "},
        }
    )
    assert default_jwt_extractor(params) == "trimmed-token"


def test_default_jwt_extractor_whitespace_only_meta_returns_none(
    monkeypatch: MonkeyPatch,
) -> None:
    """Whitespace-only meta token is ignored; env is not read without opt-in."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "env-token")
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": "   "},
        }
    )
    assert default_jwt_extractor(params) is None


def test_default_jwt_extractor_ignores_non_string_meta() -> None:
    """Extractor ignores non-string asap_agent_jwt values in meta."""
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": 12345},
        }
    )
    assert default_jwt_extractor(params) is None


def test_default_jwt_extractor_env_fallback_requires_opt_in(monkeypatch: MonkeyPatch) -> None:
    """ASAP_AGENT_JWT is ignored unless allow_env_fallback is True."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "dev-env-token")
    params = CallToolRequestParams(name="echo", arguments={})
    assert default_jwt_extractor(params) is None
    assert default_jwt_extractor(params, allow_env_fallback=True) == "dev-env-token"


def test_default_jwt_extractor_meta_precedence_over_env(monkeypatch: MonkeyPatch) -> None:
    """Meta token takes precedence over environment fallback."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "env-token")
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": "meta-token"},
        }
    )
    assert default_jwt_extractor(params, allow_env_fallback=True) == "meta-token"


def test_default_jwt_extractor_returns_none_when_missing() -> None:
    """Extractor returns None when meta and env are absent."""
    params = CallToolRequestParams(name="echo", arguments={})
    assert default_jwt_extractor(params) is None


def test_resolve_jwt_extractor_uses_default_with_env_flag(monkeypatch: MonkeyPatch) -> None:
    """resolve_jwt_extractor applies allow_env_jwt_fallback from config."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "resolved-env-token")
    params = CallToolRequestParams(name="echo", arguments={})
    blocked = resolve_jwt_extractor(_minimal_config())
    enabled = resolve_jwt_extractor(_minimal_config(allow_env_jwt_fallback=True))
    assert blocked(params) is None
    assert enabled(params) == "resolved-env-token"


def test_resolve_jwt_extractor_prefers_custom_callable() -> None:
    """resolve_jwt_extractor returns config.jwt_extractor when set."""
    params = CallToolRequestParams(name="echo", arguments={})
    config = _minimal_config()
    config.jwt_extractor = lambda _params: "custom-token"
    assert resolve_jwt_extractor(config)(params) == "custom-token"
