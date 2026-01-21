"""Coordinator agent example for ASAP protocol.

This module defines a coordinator agent with a manifest and FastAPI app.
The coordinator will dispatch tasks to other agents in later steps.
"""

from typing import Any

from fastapi import FastAPI

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.observability import get_logger
from asap.observability.logging import bind_context, clear_context
from asap.transport.client import ASAPClient
from asap.transport.server import create_app

DEFAULT_AGENT_ID = "urn:asap:agent:coordinator"
DEFAULT_AGENT_NAME = "Coordinator Agent"
DEFAULT_AGENT_VERSION = "0.1.0"
DEFAULT_AGENT_DESCRIPTION = "Coordinates tasks across agents"
DEFAULT_ASAP_ENDPOINT = "http://localhost:8000/asap"
DEFAULT_ECHO_AGENT_ID = "urn:asap:agent:echo-agent"
DEFAULT_ECHO_BASE_URL = "http://127.0.0.1:8001"

logger = get_logger(__name__)


def build_manifest(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> Manifest:
    """Build the manifest for the coordinator agent.

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Manifest describing the coordinator agent's capabilities and endpoints.
    """
    return Manifest(
        id=DEFAULT_AGENT_ID,
        name=DEFAULT_AGENT_NAME,
        version=DEFAULT_AGENT_VERSION,
        description=DEFAULT_AGENT_DESCRIPTION,
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="coordinate", description="Dispatch tasks to agents")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
    )


def create_coordinator_app(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> FastAPI:
    """Create the FastAPI app for the coordinator agent.

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Configured FastAPI app.
    """
    manifest = build_manifest(asap_endpoint)
    return create_app(manifest)


app = create_coordinator_app()


def build_task_request(payload: dict[str, Any]) -> TaskRequest:
    """Build a TaskRequest payload for the echo agent.

    Args:
        payload: Input data to echo.

    Returns:
        TaskRequest payload ready for dispatch.
    """
    return TaskRequest(
        conversation_id=generate_id(),
        skill_id="echo",
        input=payload,
    )


def build_task_envelope(payload: dict[str, Any]) -> Envelope:
    """Build a TaskRequest envelope targeting the echo agent.

    Args:
        payload: Input data to echo.

    Returns:
        TaskRequest envelope for transmission.
    """
    task_request = build_task_request(payload)
    return Envelope(
        asap_version="0.1",
        sender=DEFAULT_AGENT_ID,
        recipient=DEFAULT_ECHO_AGENT_ID,
        payload_type="task.request",
        payload=task_request.model_dump(),
        trace_id=generate_id(),
    )


async def dispatch_task(
    payload: dict[str, Any],
    echo_base_url: str = DEFAULT_ECHO_BASE_URL,
) -> Envelope:
    """Dispatch a task to the echo agent using ASAPClient.

    Args:
        payload: Input data to echo.
        echo_base_url: Base URL for the echo agent (no trailing /asap).

    Returns:
        Response envelope from the echo agent.
    """
    envelope = build_task_envelope(payload)
    bind_context(trace_id=envelope.trace_id, correlation_id=envelope.id)
    try:
        logger.info(
            "asap.coordinator.request_sent",
            request_id=envelope.id,
            payload_type=envelope.payload_type,
            payload=envelope.payload,
        )
    finally:
        clear_context()
    async with ASAPClient(echo_base_url) as client:
        response = await client.send(envelope)

    bind_context(
        trace_id=envelope.trace_id,
        correlation_id=response.correlation_id,
    )
    try:
        logger.info(
            "asap.coordinator.response_received",
            request_id=envelope.id,
            response_id=response.id,
            payload_type=response.payload_type,
            result=response.payload,
        )
    finally:
        clear_context()
    return response
