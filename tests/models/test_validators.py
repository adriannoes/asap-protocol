"""Unit tests for ``asap.models.validators`` helpers."""

from __future__ import annotations

import pytest

from asap.models.constants import MAX_URN_LENGTH
from asap.models.validators import validate_agent_urn, validate_percentage_format


def test_validate_percentage_format_accepts_common_forms() -> None:
    assert validate_percentage_format("99.5%") == "99.5%"
    assert validate_percentage_format(" 1% ") == "1%"
    assert validate_percentage_format("-0.5") == "-0.5"


def test_validate_percentage_format_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="Invalid percentage string"):
        validate_percentage_format("not a number")


def test_validate_agent_urn_rejects_excessive_length() -> None:
    prefix = "urn:asap:agent:"
    filler_len = MAX_URN_LENGTH - len(prefix) + 1
    too_long = prefix + ("x" * filler_len)
    assert len(too_long) > MAX_URN_LENGTH
    with pytest.raises(ValueError, match="at most"):
        validate_agent_urn(too_long)


def test_validate_agent_urn_rejects_bad_pattern() -> None:
    with pytest.raises(ValueError, match="Agent ID must follow URN format"):
        validate_agent_urn("https://example.invalid/agent")
