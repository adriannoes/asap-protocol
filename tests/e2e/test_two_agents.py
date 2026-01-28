"""End-to-end tests for the two-agent demo flow."""

from typing import Any

import httpx
import pytest

from asap.examples.coordinator import build_task_envelope, create_coordinator_app
from asap.examples.echo_agent import create_echo_app
from asap.transport.client import ASAPClient


@pytest.mark.asyncio()
async def test_two_agents_echo_flow() -> None:
    """Send a TaskRequest from coordinator to echo agent."""
    payload: dict[str, Any] = {"message": "hello"}
    envelope = build_task_envelope(payload)

    coordinator_app = create_coordinator_app("http://coordinator/asap")
    echo_app = create_echo_app("http://echo-agent/asap")

    coordinator_transport = httpx.ASGITransport(app=coordinator_app)
    async with httpx.AsyncClient(
        transport=coordinator_transport,
        base_url="http://coordinator",
    ) as coordinator_client:
        manifest_response = await coordinator_client.get(
            "/.well-known/asap/manifest.json",
        )
    assert manifest_response.status_code == 200

    transport = httpx.ASGITransport(app=echo_app)

    # Note: require_https=False is allowed here because we're using a mock transport
    # (ASGITransport) for in-memory testing. Production code must use HTTPS.
    async with ASAPClient("http://echo-agent", transport=transport, require_https=False) as client:
        response = await client.send(envelope)

    assert response.payload_type == "task.response"
    assert response.payload["status"] == "completed"
    assert response.payload["result"]["echoed"] == payload
    assert response.trace_id == envelope.trace_id
    assert response.correlation_id == envelope.id
