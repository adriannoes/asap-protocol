"""Mock agents and request/response recording for ASAP tests.

This module provides MockAgent: a configurable mock agent that can
pre-set responses and record incoming requests for assertions.

Features:
    - Pre-set responses per skill or per envelope pattern.
    - Request recording (incoming envelopes) for later assertion.
    - Configurable delay or failure for error-path tests.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from asap.models.envelope import Envelope
from asap.models.ids import generate_id


class MockAgent:
    """Configurable mock agent for testing ASAP integrations.

    Simulates an agent without a real server. Supports pre-set responses
    per skill, request recording, optional delay, and simulated failures
    for error-path tests.

    Attributes:
        agent_id: URN identifying this mock agent (e.g. urn:asap:agent:test-echo).
        requests: List of all envelopes received by handle() (read-only).
    """

    def __init__(self, agent_id: str = "urn:asap:agent:mock") -> None:
        """Initialize the mock agent.

        Args:
            agent_id: URN for this mock agent.
        """
        self.agent_id = agent_id
        self._responses: dict[str, dict[str, Any]] = {}
        self._default_response: dict[str, Any] | None = None
        self._delay_seconds: float = 0.0
        self._failure: BaseException | None = None
        self.requests: list[Envelope] = []

    def set_response(self, skill_id: str, payload: dict[str, Any]) -> None:
        """Pre-set the response payload for a skill.

        Args:
            skill_id: Skill id (e.g. 'echo').
            payload: Response payload (e.g. TaskResponse.model_dump()).
        """
        self._responses[skill_id] = payload

    def set_default_response(self, payload: dict[str, Any]) -> None:
        """Pre-set a response used when no skill-specific response is set.

        Args:
            payload: Response payload (e.g. TaskResponse.model_dump()).
        """
        self._default_response = payload

    def set_delay(self, seconds: float) -> None:
        """Set a delay (sleep) before returning the response. Useful for timeout tests.

        Args:
            seconds: Delay in seconds (0 to disable).
        """
        self._delay_seconds = max(0.0, seconds)

    def set_failure(self, exception: BaseException | None) -> None:
        """Set a failure to raise when handle() is called. Clears after raise.

        Args:
            exception: Exception to raise (None to disable).
        """
        self._failure = exception

    def requests_for_skill(self, skill_id: str) -> list[Envelope]:
        """Return envelopes that requested this skill."""
        return [e for e in self.requests if e.payload_dict.get("skill_id") == skill_id]

    def handle(self, envelope: Envelope) -> Envelope | None:
        """Handle an incoming envelope and return a response envelope.

        Records the request. Optionally sleeps (set_delay), raises (set_failure),
        or returns an envelope built from the pre-set response for the
        envelope's skill_id or default response.

        Args:
            envelope: Incoming ASAP envelope.

        Returns:
            Response envelope or None if no response configured.

        Raises:
            BaseException: If set_failure() was called with an exception.
        """
        self.requests.append(envelope)

        if self._failure is not None:
            exc = self._failure
            self._failure = None
            raise exc

        skill_id = envelope.payload_dict.get("skill_id")
        payload = (self._responses.get(skill_id) if skill_id else None) or self._default_response
        if payload is None:
            return None

        if self._delay_seconds > 0:
            time.sleep(self._delay_seconds)

        return Envelope(
            id=generate_id(),
            asap_version=envelope.asap_version,
            timestamp=datetime.now(timezone.utc),
            sender=self.agent_id,
            recipient=envelope.sender,
            payload_type="TaskResponse",
            payload=payload,
            correlation_id=envelope.id,
            trace_id=envelope.trace_id,
        )

    def clear(self) -> None:
        """Clear recorded requests, pre-set responses, delay, and failure."""
        self.requests.clear()
        self._responses.clear()
        self._default_response = None
        self._delay_seconds = 0.0
        self._failure = None

    def reset(self) -> None:
        """Reset internal state. Equivalent to clear()."""
        self.clear()


__all__ = ["MockAgent"]
