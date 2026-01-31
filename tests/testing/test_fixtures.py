"""Tests for asap.testing fixtures and context managers."""

import pytest

from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.state.snapshot import InMemorySnapshotStore
from asap.testing.fixtures import (
    DEFAULT_TEST_BASE_URL,
    test_agent as agent_context,
    test_client as client_context,
)
from asap.testing.mocks import MockAgent


class TestMockAgentFixture:
    """Tests using mock_agent pytest fixture."""

    def test_mock_agent_fixture_returns_fresh_agent(self, mock_agent: MockAgent) -> None:
        """mock_agent fixture yields a MockAgent instance."""
        assert isinstance(mock_agent, MockAgent)
        assert mock_agent.agent_id == "urn:asap:agent:mock"
        mock_agent.set_response(
            "echo",
            TaskResponse(task_id="t1", status="completed").model_dump(),
        )
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient=mock_agent.agent_id,
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
        )
        out = mock_agent.handle(req)
        assert out is not None
        assert out.payload_type == "TaskResponse"


class TestMockSnapshotStoreFixture:
    """Tests using mock_snapshot_store pytest fixture."""

    def test_mock_snapshot_store_fixture_returns_store(
        self, mock_snapshot_store: InMemorySnapshotStore
    ) -> None:
        """mock_snapshot_store fixture yields an InMemorySnapshotStore."""
        assert isinstance(mock_snapshot_store, InMemorySnapshotStore)
        assert mock_snapshot_store.list_versions("task_1") == []


class TestTestAgentContextManager:
    """Tests for test_agent() context manager."""

    def test_test_agent_yields_agent_and_clears_on_exit(self) -> None:
        """test_agent() yields MockAgent and clears it on exit."""
        req = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:a",
            recipient="urn:asap:agent:custom",
            payload_type="TaskRequest",
            payload=TaskRequest(conversation_id="c", skill_id="echo", input={}).model_dump(),
        )
        with agent_context("urn:asap:agent:custom") as agent:
            assert agent.agent_id == "urn:asap:agent:custom"
            agent.set_response(
                "echo",
                TaskResponse(task_id="t1", status="completed").model_dump(),
            )
            out = agent.handle(req)
            assert out is not None
        # After exit, clear() ran: no pre-set response, so handle returns None
        assert agent.handle(req) is None


class TestTestClientContextManager:
    """Tests for test_client() async context manager."""

    @pytest.mark.asyncio
    async def test_test_client_yields_client(self) -> None:
        """test_client() yields an ASAPClient (entered)."""
        from asap.transport.client import ASAPClient

        async with client_context(DEFAULT_TEST_BASE_URL) as client:
            assert isinstance(client, ASAPClient)
            # Client is open; we don't call send() to avoid needing a server
