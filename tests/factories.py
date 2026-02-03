"""Shared test data factories for ASAP protocol tests.

This module provides common factory functions for manifests and envelopes
used across integration tests, reducing duplication and ensuring consistent
test data structures.
"""

from __future__ import annotations

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest


def create_test_manifest(agent_id: str = "urn:asap:agent:test-server") -> Manifest:
    """Create a test manifest for ASAP server (no auth).

    Args:
        agent_id: Agent URN.

    Returns:
        A Manifest with echo and uppercase skills, no authentication.
    """
    return Manifest(
        id=agent_id,
        name="Test ASAP Server",
        version="1.0.0",
        description="Test server for MCP integration",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(id="echo", description="Echo skill"),
                Skill(id="uppercase", description="Convert to uppercase"),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


def create_auth_manifest(agent_id: str = "urn:asap:agent:auth-server") -> Manifest:
    """Create a manifest with bearer authentication enabled.

    Args:
        agent_id: Agent URN.

    Returns:
        A Manifest with echo and slow skills and bearer auth scheme.
    """
    return Manifest(
        id=agent_id,
        name="Auth Test Server",
        version="1.0.0",
        description="Test server with authentication",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(id="echo", description="Echo skill"),
                Skill(id="slow", description="Slow skill for pooling tests"),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        auth=AuthScheme(schemes=["bearer"]),
    )


def create_envelope(
    sender: str = "urn:asap:agent:client",
    recipient: str = "urn:asap:agent:auth-server",
    skill_id: str = "echo",
    message: str = "test",
    conversation_id: str = "conv-123",
) -> Envelope:
    """Create a test envelope with TaskRequest payload.

    Args:
        sender: Sender agent URN.
        recipient: Recipient agent URN.
        skill_id: Skill identifier.
        message: Input message for the payload.
        conversation_id: Conversation identifier.

    Returns:
        An Envelope with task.request payload.
    """
    return Envelope(
        asap_version="0.1",
        sender=sender,
        recipient=recipient,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id=conversation_id,
            skill_id=skill_id,
            input={"message": message},
        ).model_dump(),
    )
