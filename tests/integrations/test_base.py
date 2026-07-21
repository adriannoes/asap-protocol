"""Direct unit tests for the shared integration base (`asap.integrations._base`).

The four framework wrappers (langchain/crewai/llamaindex/smolagents) and the
function-based integrations (pydanticai/openclaw/vercel_ai) exercise this module
indirectly, but the misleading-error-string fix, the URN-scoped resolve cache,
the resolve-vs-run error split, and the loop-detection invariant deserve
explicit regression assertions so a future change cannot silently re-collapse
the distinct error messages, regress the re-entrant-resolve guard, or
re-introduce the URN-agnostic cache.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.integrations._base import (
    build_task_payload,
    default_input_schema,
    format_invoke_error,
    invoke_skill_async,
    json_schema_to_pydantic,
    resolve_and_cache_skill,
    sanitize_tool_name,
)


def _run(coro: Any) -> Any:
    """Run *coro* to completion synchronously (tests are sync; invoke is async)."""
    return asyncio.run(coro)


class TestFormatInvokeError:
    """``format_invoke_error`` must emit a distinct, truthful prefix per type.

    The shared ``"Agent revoked or invalid input"`` string previously fired for
    plain ``ValueError`` as well as genuine revocations, hiding the real cause
    from callers.
    """

    def test_agent_revoked_exception_gets_revoked_prefix(self) -> None:
        """AgentRevokedException reports the revocation, not a generic input error."""
        err = AgentRevokedException("urn:asap:agent:ghost")
        message = format_invoke_error(err)
        assert message.startswith("Error: Agent revoked:")
        assert "urn:asap:agent:ghost" in message
        assert "invalid input" not in message

    def test_signature_verification_error_gets_signature_prefix(self) -> None:
        """SignatureVerificationError reports a signature failure, not revocation."""
        err = SignatureVerificationError("invalid signature", {})
        message = format_invoke_error(err)
        assert message.startswith("Error: Agent signature verification failed:")
        assert "invalid signature" in message
        assert "revoked" not in message
        assert "invalid input" not in message

    def test_value_error_gets_invalid_input_prefix(self) -> None:
        """Plain ValueError reports an invalid input/task request, not revocation.

        This is the core of the regression: previously ValueError collapsed into
        the misleading 'Agent revoked or invalid input' string.
        """
        err = ValueError("missing skill_id")
        message = format_invoke_error(err)
        assert message.startswith("Error: Invalid skill input or task request:")
        assert "missing skill_id" in message
        assert "revoked" not in message

    def test_other_exception_gets_generic_invocation_prefix(self) -> None:
        """Any other exception type falls back to a generic invocation-failed prefix."""
        err = RuntimeError("upstream timeout")
        message = format_invoke_error(err)
        assert message.startswith("Error: ASAP invocation failed:")
        assert "upstream timeout" in message

    def test_all_prefixes_are_mutually_distinct(self) -> None:
        """No two exception types share a prefix (the bug was prefix collision)."""
        prefixes = {
            format_invoke_error(AgentRevokedException("urn:asap:agent:x")).split(":")[1].strip(),
            format_invoke_error(SignatureVerificationError("bad", {}))
            .split(":")[1]
            .strip()
            .removesuffix(" failed"),
            format_invoke_error(ValueError("bad"))
            .split(":")[1]
            .strip()
            .removesuffix(" or task request"),
            format_invoke_error(RuntimeError("bad")).split(":")[1].strip(),
        }
        assert len(prefixes) == 4, f"prefixes collided: {prefixes}"


class TestInvokeSkillResolveRunSplit:
    """Resolve-time vs run-time errors get distinct, truthful prefixes.

    Regression for the S2 PR-review "Should Fix": ``MarketClient.resolve`` raises
    ``ValueError`` for "agent not found", but the shared run-time
    ``format_invoke_error`` mapped all ``ValueError`` to "Invalid skill input or
    task request" — mislabeling a resolve failure. The resolve path now uses a
    resolve-scoped prefix naming the URN.
    """

    @staticmethod
    def _client_resolve_raises(exc: BaseException) -> _FakeMarketClient:
        client = _FakeMarketClient()
        client.resolve.side_effect = exc
        return client

    @staticmethod
    def _cache() -> Any:
        from unittest.mock import MagicMock

        cache = MagicMock()
        cache._resolved = None
        return cache

    def test_resolve_value_error_names_urn_not_skill_input(self) -> None:
        """A resolve ValueError reports 'Failed to resolve agent <urn>', not invalid input."""
        client = self._client_resolve_raises(ValueError("agent not found"))
        result = _run(invoke_skill_async(client, "urn:asap:agent:ghost", self._cache(), {"q": 1}))
        assert "Failed to resolve agent urn:asap:agent:ghost" in result
        assert "Invalid skill input" not in result

    def test_resolve_agent_revoked_keeps_revoked_prefix(self) -> None:
        """Resolve-time revocation still reports 'Agent revoked' (truthful per-type prefix)."""
        client = self._client_resolve_raises(AgentRevokedException("urn:asap:agent:ghost"))
        result = _run(invoke_skill_async(client, "urn:asap:agent:ghost", self._cache(), {}))
        assert result.startswith("Error: Agent revoked:")

    def test_run_value_error_keeps_skill_input_prefix(self) -> None:
        """A run-time ValueError (after successful resolve) keeps the skill-input prefix."""
        client = _FakeMarketClient()
        agent = MagicMock()
        agent.manifest.capabilities.skills = [MagicMock(id="skill-1")]
        client.resolve.side_effect = None

        async def _resolve(_urn: str) -> MagicMock:
            return agent

        client.resolve.side_effect = _resolve
        agent.run = AsyncMock(side_effect=ValueError("bad input"))
        result = _run(invoke_skill_async(client, "urn:asap:agent:x", self._cache(), {"q": 1}))
        assert "Invalid skill input or task request" in result
        assert "Failed to resolve" not in result


class TestJsonSchemaToPydantic:
    """``json_schema_to_pydantic`` converts a JSON Schema object to a pydantic model."""

    def test_object_schema_yields_fielded_model(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        }
        model = json_schema_to_pydantic(schema, model_name="SearchArgs")
        instance = model(query="hello", limit=5)
        assert instance.query == "hello"
        assert instance.limit == 5

    def test_non_object_schema_falls_back_to_default_input(self) -> None:
        """A non-object (or empty) schema falls back to the generic {input: dict} model."""
        model = json_schema_to_pydantic({}, default_name="FallbackInput")
        assert model.__name__ == "FallbackInput"
        instance = model(input={"k": "v"})
        assert instance.input == {"k": "v"}


class TestDefaultInputSchema:
    def test_default_input_schema_carries_input_field(self) -> None:
        model = default_input_schema("MyToolInput")
        assert model.__name__ == "MyToolInput"
        assert instance_input(model) == {"sentinel": True}


class TestBuildTaskPayload:
    def test_payload_has_conversation_skill_and_input(self) -> None:
        payload = build_task_payload("skill-1", {"q": "hi"})
        assert payload["skill_id"] == "skill-1"
        assert payload["input"] == {"q": "hi"}
        assert "conversation_id" in payload
        assert isinstance(payload["conversation_id"], str)


class TestSanitizeToolName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("My Agent!", "My_Agent"),
            ("123bot", "asap_123bot"),
            ("---", "asap_agent"),
            ("already_clean", "already_clean"),
        ],
    )
    def test_sanitization_rules(self, raw: str, expected: str) -> None:
        assert sanitize_tool_name(raw) == expected


class TestResolveAndCacheSkill:
    """URN-scoped resolve cache invariants.

    Regression for the S2 PR-review HIGH finding: the client-level cache was
    URN-agnostic, so a shared ``MarketClient`` used by two tools with different
    URNs routed the second tool to the first agent's resolution. The cache must
    be keyed by URN and each resolve must validate it returns the agent for the
    requested URN.
    """

    def test_two_urns_on_shared_client_resolve_distinct_agents(self) -> None:
        """A shared client resolving two URNs must cache and return each URN's agent."""
        resolved_by_urn: dict[str, object] = {}
        client = _FakeMarketClient.resolving(resolved_by_urn)

        agent_a, skill_a = resolve_and_cache_skill(client, "urn:asap:agent:a")
        agent_b, skill_b = resolve_and_cache_skill(client, "urn:asap:agent:b")

        assert agent_a.manifest.id == "urn:asap:agent:a"
        assert agent_b.manifest.id == "urn:asap:agent:b"
        assert agent_a is not agent_b
        assert skill_a == "skill-urn:asap:agent:a"
        assert skill_b == "skill-urn:asap:agent:b"

    def test_cache_hit_returns_same_instance_without_second_resolve(self) -> None:
        """A repeat resolve of the same URN reuses the cached agent (no second call)."""
        resolved_by_urn: dict[str, object] = {}
        client = _FakeMarketClient.resolving(resolved_by_urn)

        first, _ = resolve_and_cache_skill(client, "urn:asap:agent:solo")
        second, _ = resolve_and_cache_skill(client, "urn:asap:agent:solo")

        assert first is second
        assert client.resolve.await_count == 1

    def test_cache_is_keyed_by_urn_not_single_slot(self) -> None:
        """The cache lives under ``_asap_resolved_by_urn`` and holds both URNs."""
        resolved_by_urn: dict[str, object] = {}
        client = _FakeMarketClient.resolving(resolved_by_urn)

        resolve_and_cache_skill(client, "urn:asap:agent:a")
        resolve_and_cache_skill(client, "urn:asap:agent:b")

        cache = getattr(client, "_asap_resolved_by_urn", None)
        assert isinstance(cache, dict)
        assert set(cache) == {"urn:asap:agent:a", "urn:asap:agent:b"}
        # The legacy single-slot attrs must not exist (the old bug).
        assert not hasattr(client, "_asap_resolved")
        assert not hasattr(client, "_asap_skill_id")


class _FakeMarketClient:
    """Minimal MarketClient stand-in for cache tests.

    ``MarketClient`` is a regular class (no ``__slots__``); the resolve cache
    sets attributes on it via ``object.__setattr__``. This stand-in mirrors that
    contract without importing the real client (which pulls HTTP/registry deps).
    """

    def __init__(self) -> None:
        self.resolve = AsyncMock()

    @classmethod
    def resolving(cls, resolved_by_urn: dict[str, object]) -> _FakeMarketClient:
        """Build a client whose ``resolve`` returns a per-URN agent mock."""
        client = cls()

        async def _resolve(urn: str) -> MagicMock:
            agent = MagicMock(name=f"agent-{urn}")
            agent.manifest.id = urn
            skills = [MagicMock(id=f"skill-{urn}")]
            agent.manifest.capabilities.skills = skills
            resolved_by_urn[urn] = agent
            return agent

        client.resolve.side_effect = _resolve
        return client


def instance_input(model: type) -> dict[str, object]:
    """Instantiate a default-input model and return its ``input`` field value."""
    return model(input={"sentinel": True}).input
