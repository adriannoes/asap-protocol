"""Benchmark fixtures and configuration."""

import uuid
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
        payload_type="task.request",
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
        "method": "asap.send",
        "params": {"envelope": sample_envelope.model_dump(mode="json")},
        "id": "benchmark-request-001",
    }


@pytest.fixture
def handler_registry() -> HandlerRegistry:
    """Create default handler registry for benchmarks."""
    return create_default_registry()


@pytest.fixture
def benchmark_app(
    sample_manifest: Manifest,
    handler_registry: HandlerRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Create a test client for HTTP benchmarks (isolated rate limiter)."""
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    isolated_limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["999999/minute"],
        storage_uri=f"memory://{uuid.uuid4()}",
    )

    import asap.transport.middleware as middleware_module
    import asap.transport.server as server_module

    monkeypatch.setattr(middleware_module, "limiter", isolated_limiter)
    monkeypatch.setattr(server_module, "limiter", isolated_limiter)

    app = create_app(
        sample_manifest, handler_registry, rate_limit="999999/minute"
    )
    app.state.limiter = isolated_limiter

    return TestClient(app)
