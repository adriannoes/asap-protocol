"""Unit tests for MockAgent (asap.testing.mocks)."""

import pytest

from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing.mocks import MockAgent


class TestMockAgent:
    """Tests for MockAgent pre-set responses and request recording."""

    def test_set_response_and_handle_returns_envelope(self) -> None:
        """Handle returns envelope built from pre-set response for skill_id."""
        agent = MockAgent("urn:asap:agent:mock")
        resp_payload = TaskResponse(task_id="task_1", status="completed").model_dump()
        agent.set_response("echo", resp_payload)
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(
                conversation_id="c", skill_id="echo", input={"msg": "hi"}
            ).model_dump(),
        )
        out = agent.handle(req)
        assert out is not None
        assert out.payload_type == "TaskResponse"
        assert out.sender == agent.agent_id
        assert out.recipient == "urn:asap:agent:a"
        assert out.payload == resp_payload
        assert len(agent.requests) == 1
        assert agent.requests[0] is req

    def test_handle_without_response_returns_none(self) -> None:
        """Handle returns None when no response is set for skill_id."""
        agent = MockAgent()
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="unknown", input={}).model_dump(),
        )
        out = agent.handle(req)
        assert out is None
        assert len(agent.requests) == 1

    def test_set_default_response_used_when_no_skill_match(self) -> None:
        """Default response is used when skill_id has no specific response."""
        agent = MockAgent()
        default = TaskResponse(task_id="task_1", status="completed").model_dump()
        agent.set_default_response(default)
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="other", input={}).model_dump(),
        )
        out = agent.handle(req)
        assert out is not None
        assert out.payload == default

    def test_requests_for_skill_filters_recorded_requests(self) -> None:
        """requests_for_skill returns only envelopes requesting that skill."""
        agent = MockAgent()
        agent.set_response("echo", {"task_id": "1", "status": "completed"})
        agent.set_response("other", {"task_id": "2", "status": "completed"})
        req_echo = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c1", skill_id="echo", input={}).model_dump(),
        )
        req_other = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c2", skill_id="other", input={}).model_dump(),
        )
        agent.handle(req_echo)
        agent.handle(req_other)
        agent.handle(req_echo)
        assert len(agent.requests_for_skill("echo")) == 2
        assert len(agent.requests_for_skill("other")) == 1

    def test_set_failure_raises_on_handle(self) -> None:
        """When set_failure is set, handle raises after recording request."""
        agent = MockAgent()
        agent.set_response("echo", TaskResponse(task_id="1", status="completed").model_dump())
        agent.set_failure(ValueError("simulated failure"))
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
        )
        with pytest.raises(ValueError, match="simulated failure"):
            agent.handle(req)
        assert len(agent.requests) == 1
        # Second call should return response (failure cleared)
        out = agent.handle(req)
        assert out is not None

    def test_set_delay_sleeps_before_return(self) -> None:
        """set_delay causes handle to sleep before returning."""
        agent = MockAgent()
        agent.set_response("echo", TaskResponse(task_id="1", status="completed").model_dump())
        agent.set_delay(0.05)
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
        )
        import time

        t0 = time.monotonic()
        out = agent.handle(req)
        elapsed = time.monotonic() - t0
        assert out is not None
        assert elapsed >= 0.05

    def test_clear_resets_requests_and_responses(self) -> None:
        """clear() empties requests and pre-set responses."""
        agent = MockAgent()
        agent.set_response("echo", TaskResponse(task_id="1", status="completed").model_dump())
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
        )
        agent.handle(req)
        assert len(agent.requests) == 1
        agent.clear()
        assert len(agent.requests) == 0
        assert agent.handle(req) is None
