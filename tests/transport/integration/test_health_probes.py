"""Integration tests for health probe endpoints.

Asserts that GET /health and GET /ready return 200 when the app is created
via create_app with compression and size-limit middleware enabled (full stack).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.entities import Manifest
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase


@pytest.fixture
def app_with_full_middleware(no_auth_manifest: Manifest) -> FastAPI:
    """Create app with compression handling and size-limit middleware enabled."""
    return create_app(
        no_auth_manifest,
        max_request_size=1024 * 1024,  # 1MB
    )


@pytest.fixture
def client(app_with_full_middleware: FastAPI) -> TestClient:
    """Create test client for health probe requests."""
    return TestClient(app_with_full_middleware)


class TestHealthProbesIntegration(NoRateLimitTestBase):
    """Integration tests for /health and /ready under full middleware stack."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """GET /health returns 200 when app has compression and size-limit middleware."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ready_returns_200(self, client: TestClient) -> None:
        """GET /ready returns 200 when app has compression and size-limit middleware."""
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
