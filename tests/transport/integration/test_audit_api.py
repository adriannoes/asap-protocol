"""Integration tests for the /audit API contract."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from asap.economics.audit import AuditEntry, InMemoryAuditStore
from asap.models.entities import Manifest
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT

if TYPE_CHECKING:
    from asap.transport.rate_limit import ASAPRateLimiter


@pytest.fixture
def audit_store() -> InMemoryAuditStore:
    """Provide an isolated in-memory audit store."""
    return InMemoryAuditStore()


@pytest.fixture
def audit_app(
    sample_manifest: Manifest,
    disable_rate_limiting: "ASAPRateLimiter",
    audit_store: InMemoryAuditStore,
) -> FastAPI:
    """Create an app with audit API enabled and limiter isolation."""
    app = create_app(
        sample_manifest,
        rate_limit=TEST_RATE_LIMIT_DEFAULT,
        audit_store=audit_store,
    )
    app.state.limiter = disable_rate_limiting
    return app


class TestAuditApiValidation(NoRateLimitTestBase):
    """Validation-focused tests for GET /audit query parameters."""

    @pytest.mark.parametrize(
        ("query", "expected_detail"),
        [
            ("limit=-1", "limit and offset must be non-negative"),
            ("offset=-1", "limit and offset must be non-negative"),
        ],
    )
    async def test_rejects_negative_pagination_params(
        self,
        audit_app: FastAPI,
        query: str,
        expected_detail: str,
    ) -> None:
        """Negative limit/offset must return HTTP 400."""
        async with AsyncClient(transport=ASGITransport(app=audit_app), base_url="http://test") as client:
            response = await client.get(f"/audit?{query}")

        assert response.status_code == 400
        assert response.json() == {"detail": expected_detail}

    @pytest.mark.parametrize("query", ["start=not-a-date", "end=still-not-a-date"])
    async def test_rejects_invalid_iso8601_dates(
        self,
        audit_app: FastAPI,
        query: str,
    ) -> None:
        """Non-ISO start/end date values must return HTTP 400."""
        async with AsyncClient(transport=ASGITransport(app=audit_app), base_url="http://test") as client:
            response = await client.get(f"/audit?{query}")

        assert response.status_code == 400
        assert response.json() == {
            "detail": "Invalid date format. Use ISO 8601 (e.g. 2026-01-01T00:00:00)"
        }

    async def test_caps_limit_to_1000_entries(
        self,
        audit_app: FastAPI,
        audit_store: InMemoryAuditStore,
    ) -> None:
        """Large requested limit must be capped to 1000 at the HTTP layer."""
        now = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for index in range(1005):
            await audit_store.append(
                AuditEntry(
                    timestamp=now + timedelta(seconds=index),
                    operation="task.request",
                    agent_urn="urn:asap:agent:test-server",
                    details={"index": index},
                )
            )

        async with AsyncClient(transport=ASGITransport(app=audit_app), base_url="http://test") as client:
            response = await client.get("/audit?limit=5000")

        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 1000
        assert len(payload["entries"]) == 1000
        assert payload["entries"][0]["details"]["index"] == 0
        assert payload["entries"][-1]["details"]["index"] == 999
