"""ASGI test application factories for harnesses and CLI integration tests."""

from __future__ import annotations

from asap.economics.audit import InMemoryAuditStore
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.rate_limit import create_test_limiter
from asap.transport.server import create_app
from fastapi import FastAPI


def make_compliance_test_app() -> FastAPI:
    """Return a minimal ASAP FastAPI app expected to pass Compliance Harness v2."""
    manifest = Manifest(
        id="urn:asap:agent:compliance-cli-test",
        name="Compliance CLI Test Agent",
        version="1.0.0",
        description="In-process agent for compliance-check CLI tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://test/asap"),
    )
    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    audit = InMemoryAuditStore()
    fastapi_app = create_app(manifest, registry, audit_store=audit)
    fastapi_app.state.limiter = create_test_limiter()
    return fastapi_app
