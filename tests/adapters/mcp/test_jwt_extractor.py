"""Unit tests for default_jwt_extractor."""

from __future__ import annotations

from pytest import MonkeyPatch

from asap.adapters.mcp.jwt_extractor import default_jwt_extractor
from asap.mcp.protocol import CallToolRequestParams


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


def test_default_jwt_extractor_ignores_non_string_meta() -> None:
    """Extractor ignores non-string asap_agent_jwt values in meta."""
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": 12345},
        }
    )
    assert default_jwt_extractor(params) is None


def test_default_jwt_extractor_env_fallback(monkeypatch: MonkeyPatch) -> None:
    """Extractor falls back to ASAP_AGENT_JWT when meta is absent (dev only)."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "dev-env-token")
    params = CallToolRequestParams(name="echo", arguments={})
    assert default_jwt_extractor(params) == "dev-env-token"


def test_default_jwt_extractor_meta_precedence_over_env(monkeypatch: MonkeyPatch) -> None:
    """Meta token takes precedence over environment fallback."""
    monkeypatch.setenv("ASAP_AGENT_JWT", "env-token")
    params = CallToolRequestParams.model_validate(
        {
            "name": "echo",
            "_meta": {"asap_agent_jwt": "meta-token"},
        }
    )
    assert default_jwt_extractor(params) == "meta-token"


def test_default_jwt_extractor_returns_none_when_missing() -> None:
    """Extractor returns None when meta and env are absent."""
    params = CallToolRequestParams(name="echo", arguments={})
    assert default_jwt_extractor(params) is None
