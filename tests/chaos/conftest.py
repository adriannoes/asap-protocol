"""Shared fixtures for chaos engineering tests.

This module provides reusable fixtures and helpers for tests in tests/chaos/:
- sample_request_envelope: Canonical request envelope for chaos scenarios
- sample_response_envelope: Response envelope correlated with request
- create_mock_response: Helper to build httpx responses from envelopes
"""

import httpx
import pytest

from asap.models.envelope import Envelope
from asap.models.enums import TaskStatus
from asap.models.payloads import TaskRequest, TaskResponse


def create_mock_response(envelope: Envelope, request_id: str | int = "req-1") -> httpx.Response:
    """Create a mock HTTP response with JSON-RPC wrapped envelope.

    Args:
        envelope: ASAP envelope to wrap in JSON-RPC result
        request_id: JSON-RPC request id for correlation

    Returns:
        httpx.Response with status 200 and JSON-RPC formatted body
    """
    json_rpc_response = {
        "jsonrpc": "2.0",
        "result": {"envelope": envelope.model_dump(mode="json")},
        "id": request_id,
    }
    return httpx.Response(
        status_code=200,
        json=json_rpc_response,
    )


@pytest.fixture
def sample_request_envelope() -> Envelope:
    """Create a canonical request envelope for chaos testing.

    Returns:
        Envelope with task.request payload for echo skill
    """
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:server",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv_chaos_001",
            skill_id="echo",
            input={"message": "Chaos test"},
        ).model_dump(),
    )


@pytest.fixture
def sample_response_envelope(sample_request_envelope: Envelope) -> Envelope:
    """Create a response envelope correlated with sample_request_envelope.

    Args:
        sample_request_envelope: Request envelope to correlate with

    Returns:
        Envelope with task.response payload
    """
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:server",
        recipient="urn:asap:agent:client",
        payload_type="task.response",
        payload=TaskResponse(
            task_id="task_chaos_001",
            status=TaskStatus.COMPLETED,
            result={"echoed": {"message": "Chaos test"}},
        ).model_dump(),
        correlation_id=sample_request_envelope.id,
    )
