"""Shared fixtures for ASAP compliance harness tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import httpx
import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.server import create_app

from asap_compliance.config import ComplianceConfig

if TYPE_CHECKING:
    from fastapi import FastAPI

pytest_plugins = ["asap_compliance.pytest_plugin"]

TEST_RATE_LIMIT = "999999/minute"


@pytest.fixture
def sample_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:compliance-test",
        name="Compliance Test Agent",
        version="1.0.0",
        description="Agent for handshake compliance tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def good_agent_app(sample_manifest: Manifest) -> "FastAPI":
    return cast("FastAPI", create_app(sample_manifest, rate_limit=TEST_RATE_LIMIT))


@pytest.fixture
def compliance_config_with_transport(
    good_agent_app: "FastAPI",
) -> tuple[ComplianceConfig, httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=good_agent_app)
    client = httpx.AsyncClient(transport=transport, base_url="http://testserver")
    config = ComplianceConfig(
        agent_url="http://testserver",
        timeout_seconds=5.0,
        test_categories=["handshake"],
    )
    return config, client
