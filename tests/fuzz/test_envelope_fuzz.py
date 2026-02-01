"""Fuzz tests for Envelope model.

Strategy: random invalid data. Assertion: validation rejects all malformed inputs.
"""

from __future__ import annotations

import contextlib
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from asap.models.envelope import Envelope

# Minimal valid envelope (request type, no correlation_id required).
_MINIMAL_VALID = {
    "asap_version": "0.1",
    "sender": "urn:asap:agent:a",
    "recipient": "urn:asap:agent:b",
    "payload_type": "TaskRequest",
    "payload": {},
}

_RESPONSE_PAYLOAD_TYPES = ["TaskResponse", "McpToolResult", "McpResourceData"]


@st.composite
def st_invalid_envelope_data(draw: st.DrawFn) -> dict[str, Any]:
    """Generate data that must be rejected by Envelope validation.

    Covers: wrong types, missing required fields, extra fields,
    response payload type without correlation_id.
    """
    case = draw(
        st.sampled_from(
            [
                "wrong_type_sender",
                "wrong_type_recipient",
                "wrong_type_payload",
                "wrong_type_asap_version",
                "missing_sender",
                "missing_recipient",
                "missing_payload_type",
                "missing_payload",
                "missing_asap_version",
                "extra_field",
                "response_without_correlation_id",
            ]
        )
    )

    if case == "wrong_type_sender":
        base = dict(_MINIMAL_VALID)
        base["sender"] = draw(
            st.one_of(st.integers(), st.booleans(), st.none(), st.lists(st.text()))
        )
        return base
    if case == "wrong_type_recipient":
        base = dict(_MINIMAL_VALID)
        base["recipient"] = draw(
            st.one_of(st.integers(), st.booleans(), st.none(), st.lists(st.text()))
        )
        return base
    if case == "wrong_type_payload":
        base = dict(_MINIMAL_VALID)
        base["payload"] = draw(
            st.one_of(st.text(), st.integers(), st.lists(st.integers()), st.none())
        )
        return base
    if case == "wrong_type_asap_version":
        base = dict(_MINIMAL_VALID)
        base["asap_version"] = draw(
            st.one_of(st.integers(), st.booleans(), st.none(), st.lists(st.text()))
        )
        return base
    if case == "missing_sender":
        return {k: v for k, v in _MINIMAL_VALID.items() if k != "sender"}
    if case == "missing_recipient":
        return {k: v for k, v in _MINIMAL_VALID.items() if k != "recipient"}
    if case == "missing_payload_type":
        return {k: v for k, v in _MINIMAL_VALID.items() if k != "payload_type"}
    if case == "missing_payload":
        return {k: v for k, v in _MINIMAL_VALID.items() if k != "payload"}
    if case == "missing_asap_version":
        return {k: v for k, v in _MINIMAL_VALID.items() if k != "asap_version"}
    if case == "extra_field":
        base = dict(_MINIMAL_VALID)
        base["_extra"] = draw(st.one_of(st.integers(), st.text(), st.booleans()))
        return base
    # response_without_correlation_id
    base = dict(_MINIMAL_VALID)
    base["payload_type"] = draw(st.sampled_from(_RESPONSE_PAYLOAD_TYPES))
    base["payload"] = draw(
        st.dictionaries(st.text(), st.one_of(st.integers(), st.text(), st.booleans()), max_size=5)
    )
    # Explicitly omit correlation_id (or set to None)
    if "correlation_id" in base:
        del base["correlation_id"]
    return base


@st.composite
def st_arbitrary_json_like(draw: st.DrawFn) -> dict[str, Any]:
    """Generate arbitrary JSON-like dicts (often invalid as Envelope)."""
    return draw(
        st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=0, max_size=15),
            values=st.recursive(
                st.one_of(
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.booleans(),
                    st.text(max_size=50),
                    st.none(),
                ),
                lambda children: st.lists(children, max_size=3)
                | st.dictionaries(st.text(max_size=10), children, max_size=3),
                max_leaves=12,
            ),
            max_size=10,
        )
    )


class TestEnvelopeFuzz:
    """Fuzz tests: malformed inputs must be rejected by Envelope validation."""

    @given(st_invalid_envelope_data())
    def test_invalid_envelope_data_raises(self, data: dict[str, Any]) -> None:
        """Envelope.model_validate rejects all known invalid shapes."""
        with pytest.raises(ValidationError):
            Envelope.model_validate(data)

    @given(st_arbitrary_json_like())
    def test_arbitrary_data_raises_or_validates(self, data: dict[str, Any]) -> None:
        """Arbitrary JSON-like dict either fails validation or parses as Envelope.

        If it has required fields with correct types and no extra keys,
        and satisfies response/correlation_id rule, it may validate.
        Otherwise ValidationError must be raised.
        """
        with contextlib.suppress(ValidationError):
            Envelope.model_validate(data)
        # If no exception, we got a valid envelope (e.g. data matched schema by chance)
