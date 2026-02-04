"""Shared pytest fixtures for ASAP protocol tests.

This module provides common fixtures used across multiple test modules,
reducing duplication and ensuring consistency in test data.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from slowapi import Limiter

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest

# Load asap.testing fixtures (mock_agent, mock_client, mock_snapshot_store)
pytest_plugins = ["asap.testing.fixtures"]


@pytest.fixture(autouse=True)
def _isolate_rate_limiter(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Isolate rate limiter for all tests (very high limits, both modules patched).

    Skipped for tests/transport/integration/test_rate_limiting.py (they use their own).
    """
    # Skip isolation for rate limiting integration tests (they manage their own limiter)
    if "test_rate_limiting" in str(request.fspath):
        return

    from slowapi import Limiter
    from slowapi.util import get_remote_address

    isolated_limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=f"memory://isolated-{uuid.uuid4().hex}",
        default_limits=["999999/minute"],
    )

    # Replace globally in both modules
    import asap.transport.middleware as middleware_module
    import asap.transport.server as server_module

    monkeypatch.setattr(middleware_module, "limiter", isolated_limiter)
    monkeypatch.setattr(server_module, "limiter", isolated_limiter)

    request.node._isolated_limiter = isolated_limiter  # type: ignore[attr-defined]


@pytest.fixture
def isolated_rate_limiter(
    request: pytest.FixtureRequest,
    _isolate_rate_limiter: None,
) -> Limiter | None:
    """Return the isolated rate limiter from _isolate_rate_limiter, or None if skipped."""
    return getattr(request.node, "_isolated_limiter", None)


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
