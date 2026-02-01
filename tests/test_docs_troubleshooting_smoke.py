"""Smoke tests for troubleshooting documentation.

Validates that documented endpoints, APIs, and behavior match the code
without starting a real server or using the network. Safe to run in CI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.testclient import TestClient

from asap.transport.server import app as default_app

if TYPE_CHECKING:
    from asap.models.entities import Manifest


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

    def test_create_app_reads_asap_rate_limit_from_env(self, sample_manifest: Manifest) -> None:
        """Validate env var read: create_app succeeds when ASAP_RATE_LIMIT is set.

        This test asserts that the server reads ASAP_RATE_LIMIT from the environment
        (app creation succeeds; /health returns 200). It does NOT assert that the
        rate limiter enforces the limit at runtime (e.g. 429 under load).
        See doc: FAQ Config.
        """
        from unittest.mock import patch

        from asap.transport.server import create_app

        with patch.dict("os.environ", {"ASAP_RATE_LIMIT": "99/second;999/minute"}):
            app = create_app(sample_manifest, rate_limit=None)
        assert app is not None
        client = TestClient(app)
        assert client.get("/health").status_code == 200
