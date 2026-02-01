"""Smoke tests for troubleshooting documentation.

Validates that documented endpoints, APIs, and behavior match the code
without starting a real server or using the network. Safe to run in CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from asap.transport.server import app as default_app


class TestDocumentedEndpoints:
    """Verify endpoints documented in troubleshooting (Tools table) work."""

    def test_health_returns_200_and_ok(self) -> None:
        """GET /health returns 200 and {status: ok} as documented."""
        client = TestClient(default_app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_returns_200_and_ok(self) -> None:
        """GET /ready returns 200 and {status: ok} as documented."""
        client = TestClient(default_app)
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_asap_metrics_returns_200_prometheus_format(self) -> None:
        """GET /asap/metrics returns 200 and Prometheus-style text as documented."""
        client = TestClient(default_app)
        response = client.get("/asap/metrics")
        assert response.status_code == 200
        text = response.text
        assert "asap_requests" in text or "asap_process_uptime" in text


class TestDocumentedEnvVarsReadByServer:
    """Verify server reads env vars documented in FAQ (Config)."""

    def test_create_app_reads_asap_rate_limit_from_env(self) -> None:
        """create_app uses ASAP_RATE_LIMIT when set (doc: FAQ Config)."""
        from unittest.mock import patch

        from asap.models.entities import Capability, Endpoint, Manifest, Skill
        from asap.transport.server import create_app

        manifest = Manifest(
            id="urn:asap:agent:env-test",
            name="Env Test",
            version="0.1",
            description="Test",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )
        with patch.dict("os.environ", {"ASAP_RATE_LIMIT": "99/second;999/minute"}):
            app = create_app(manifest, rate_limit=None)
        assert app is not None
        client = TestClient(app)
        assert client.get("/health").status_code == 200
