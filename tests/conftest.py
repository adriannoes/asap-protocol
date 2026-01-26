"""Shared pytest fixtures for ASAP protocol tests.

This module provides common fixtures used across multiple test modules,
reducing duplication and ensuring consistency in test data.
"""

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_manifest() -> Manifest:
    """Create a sample manifest for testing.

    Returns:
        A Manifest instance with common test values
    """
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server for unit tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="echo",
                    description="Echo input as output",
                )
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def sample_task_request() -> TaskRequest:
    """Create a sample TaskRequest payload for testing.

    Returns:
        A TaskRequest instance with common test values
    """
    return TaskRequest(
        conversation_id="conv_test_123",
        skill_id="echo",
        input={"message": "test"},
    )


@pytest.fixture
def sample_envelope(sample_task_request: TaskRequest) -> Envelope:
    """Create a sample Envelope for testing.

    Args:
        sample_task_request: TaskRequest payload fixture

    Returns:
        An Envelope instance with common test values
    """
    return Envelope(
        asap_version="0.1",
        timestamp=datetime.now(timezone.utc),
        sender="urn:asap:agent:coordinator",
        recipient="urn:asap:agent:test-server",
        payload_type="TaskRequest",
        payload=sample_task_request,
    )
