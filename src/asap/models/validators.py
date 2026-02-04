"""Shared validators for ASAP protocol models."""

import re

from asap.models.constants import AGENT_URN_PATTERN, MAX_URN_LENGTH

_AGENT_URN_RE = re.compile(AGENT_URN_PATTERN)


def validate_agent_urn(v: str) -> str:
    """Validate agent URN format and length (pattern + max length)."""
    if len(v) > MAX_URN_LENGTH:
        raise ValueError(f"Agent URN must be at most {MAX_URN_LENGTH} characters, got {len(v)}")
    if not _AGENT_URN_RE.match(v):
        raise ValueError(f"Agent ID must follow URN format 'urn:asap:agent:{{name}}', got: {v}")
    return v

