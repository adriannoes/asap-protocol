"""Direct unit tests for the shared integration base (`asap.integrations._base`).

The four framework wrappers (langchain/crewai/llamaindex/smolagents) and the
function-based integrations (pydanticai/openclaw/vercel_ai) exercise this module
indirectly, but the misleading-error-string fix (S2 Task 5.0) and the
loop-detection / cache invariants deserve explicit regression assertions so a
future change cannot silently re-collapse the distinct error messages or regress
the re-entrant-resolve guard.
"""

from __future__ import annotations

import pytest

from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.integrations._base import (
    build_task_payload,
    default_input_schema,
    format_invoke_error,
    json_schema_to_pydantic,
    sanitize_tool_name,
)


class TestFormatInvokeError:
    """``format_invoke_error`` must emit a distinct, truthful prefix per type.

    Regression for the S2 Task 5.0 bug: the shared ``"Agent revoked or invalid
    input"`` string fired for plain ``ValueError`` as well as genuine
    revocations, hiding the real cause from callers.
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


def instance_input(model: type) -> dict[str, object]:
    """Instantiate a default-input model and return its ``input`` field value."""
    return model(input={"sentinel": True}).input
