"""Benchmark fixtures and configuration.

Provides shared fixtures for ASAP performance benchmarks.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.transport.handlers import HandlerRegistry, create_default_registry
from asap.transport.server import create_app


@pytest.fixture
def sample_manifest() -> Manifest:
    """Create a sample manifest for benchmarks."""
    return Manifest(
        id="urn:asap:agent:benchmark-agent",
        name="Benchmark Agent",
        version="1.0.0",
        description="Agent for performance benchmarks",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(id="echo", description="Echo skill"),
                Skill(id="benchmark", description="Benchmark skill"),
            ],
            state_persistence=False,
            streaming=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def sample_envelope() -> Envelope:
    """Create a sample envelope for benchmarks."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:benchmark-agent",
        payload_type="TaskRequest",
        payload={
            "conversation_id": "conv_benchmark_001",
            "skill_id": "echo",
            "input": {"message": "benchmark test message"},
        },
    )


@pytest.fixture
def sample_jsonrpc_request(sample_envelope: Envelope) -> dict[str, Any]:
    """Create a sample JSON-RPC request for benchmarks."""
    return {
        "jsonrpc": "2.0",
        "method": "asap.message",
        "params": sample_envelope.model_dump(mode="json"),
        "id": "benchmark-request-001",
    }


@pytest.fixture
def handler_registry() -> HandlerRegistry:
    """Create default handler registry for benchmarks."""
    return create_default_registry()


@pytest.fixture
def benchmark_app(sample_manifest: Manifest, handler_registry: HandlerRegistry) -> TestClient:
    """Create a test client for HTTP benchmarks."""
    app = create_app(sample_manifest, handler_registry)
    return TestClient(app)
