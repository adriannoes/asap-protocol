"""Integration tests for SLA REST API (GET /sla, /sla/history, /sla/breaches)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Coroutine, TypeVar

import pytest
from fastapi.testclient import TestClient

from asap.economics import InMemorySLAStorage, SLABreach, SLAMetrics
from asap.models.entities import Capability, Endpoint, Manifest, Skill, SLADefinition
from asap.transport.server import create_app


T = TypeVar("T")


def _run(coro: Coroutine[Any, Any, T]) -> T:
    """Run async coroutine from sync test (for storage setup)."""
    return asyncio.run(coro)


def _metrics(
    agent_id: str = "urn:asap:agent:test-server",
    period_start: datetime | None = None,
    period_end: datetime | None = None,
) -> SLAMetrics:
    start = period_start or datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
    end = period_end or datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)
    return SLAMetrics(
        agent_id=agent_id,
        period_start=start,
        period_end=end,
        uptime_percent=99.5,
        latency_p95_ms=120,
        error_rate_percent=0.5,
        tasks_completed=100,
        tasks_failed=1,
    )


def _breach(
    breach_id: str = "breach_01",
    agent_id: str = "urn:asap:agent:test-server",
    severity: str = "warning",
) -> SLABreach:
    return SLABreach(
        id=breach_id,
        agent_id=agent_id,
        breach_type="latency",
        threshold="500ms",
        actual="600ms",
        severity=severity,
        detected_at=datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sla_storage() -> InMemorySLAStorage:
    """Fresh InMemorySLAStorage for SLA API tests."""
    return InMemorySLAStorage()


@pytest.fixture
def sample_manifest() -> Manifest:
    """Sample manifest for create_app."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def manifest_with_sla() -> Manifest:
    """Manifest with SLA definition for compliance tests."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
        sla=SLADefinition(
            availability="99%",
            max_latency_p95_ms=500,
            max_error_rate="1%",
        ),
    )


class TestSLAAPIGetSla:
    """Test GET /sla endpoint (current status)."""

    def test_get_sla_returns_empty_when_no_data(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla returns empty data when storage is empty."""
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["data"] == []
        assert data["window"] == "24h"

    def test_get_sla_returns_metrics_when_data_exists(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla returns aggregated metrics when storage has data."""
        _run(sla_storage.record_metrics(_metrics()))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "urn:asap:agent:test-server"
        assert "metrics" in data["data"][0]
        assert data["data"][0]["metrics"]["uptime_percent"] == 99.5
        assert data["data"][0]["metrics"]["latency_p95_ms"] == 120

    def test_get_sla_with_agent_id_filter(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla?agent_id=... filters by agent."""
        _run(sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:a")))
        _run(sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:b")))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla", params={"agent_id": "urn:asap:agent:a"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "urn:asap:agent:a"

    def test_get_sla_with_window_param(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla?window=1h uses 1h rolling window."""
        _run(sla_storage.record_metrics(_metrics()))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla", params={"window": "1h"})
        assert resp.status_code == 200
        assert resp.json()["window"] == "1h"

    def test_get_sla_invalid_window_returns_400(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla?window=invalid returns 400."""
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla", params={"window": "invalid"})
        assert resp.status_code == 400

    def test_get_sla_compliance_when_manifest_has_sla(
        self,
        manifest_with_sla: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla returns compliance_percent when manifest has SLA and agent matches."""
        _run(sla_storage.record_metrics(_metrics(agent_id="urn:asap:agent:test-server")))
        app = create_app(
            manifest_with_sla,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla", params={"agent_id": "urn:asap:agent:test-server"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["compliance_percent"] == 100.0


class TestSLAAPIGetHistory:
    """Test GET /sla/history endpoint."""

    def test_get_sla_history_returns_empty_when_no_data(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/history returns empty when storage is empty."""
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["count"] == 0
        assert data["total"] == 0

    def test_get_sla_history_returns_recorded_metrics(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/history returns metrics from storage."""
        _run(sla_storage.record_metrics(_metrics()))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "urn:asap:agent:test-server"
        assert data["count"] == 1
        assert data["total"] == 1

    def test_get_sla_history_pagination(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/history respects limit and offset."""
        for i in range(5):
            _run(
                sla_storage.record_metrics(
                    _metrics(
                        period_start=datetime(2026, 2, 18, i, 0, 0, tzinfo=timezone.utc),
                        period_end=datetime(2026, 2, 18, i + 1, 0, 0, tzinfo=timezone.utc),
                    )
                )
            )
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/history", params={"limit": 2, "offset": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["count"] == 2
        assert data["total"] == 5
        assert data["offset"] == 1
        assert data["limit"] == 2


class TestSLAAPIGetBreaches:
    """Test GET /sla/breaches endpoint."""

    def test_get_sla_breaches_returns_empty_when_no_data(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/breaches returns empty when no breaches."""
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/breaches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["count"] == 0

    def test_get_sla_breaches_returns_recorded_breaches(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/breaches returns breaches from storage."""
        _run(sla_storage.record_breach(_breach()))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/breaches")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "breach_01"
        assert data["data"][0]["breach_type"] == "latency"
        assert data["data"][0]["severity"] == "warning"

    def test_get_sla_breaches_filter_by_agent(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/breaches?agent_id=... filters by agent."""
        _run(sla_storage.record_breach(_breach(agent_id="urn:asap:agent:a")))
        _run(sla_storage.record_breach(_breach(breach_id="b2", agent_id="urn:asap:agent:b")))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/breaches", params={"agent_id": "urn:asap:agent:a"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "urn:asap:agent:a"

    def test_get_sla_breaches_filter_by_severity(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/breaches?severity=critical filters by severity."""
        _run(sla_storage.record_breach(_breach(breach_id="b1", severity="warning")))
        _run(sla_storage.record_breach(_breach(breach_id="b2", severity="critical")))
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/breaches", params={"severity": "critical"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["severity"] == "critical"

    def test_get_sla_breaches_invalid_severity_returns_400(
        self,
        sample_manifest: Manifest,
        sla_storage: InMemorySLAStorage,
    ) -> None:
        """GET /sla/breaches?severity=invalid returns 400."""
        app = create_app(
            sample_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/sla/breaches", params={"severity": "invalid"})
        assert resp.status_code == 400


class TestSLAAPIMisc:
    """Misc SLA API tests."""

    def test_sla_api_returns_503_when_storage_missing(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """SLA endpoints return 503 if sla_storage is not configured on app state."""
        app = create_app(sample_manifest, rate_limit="999999/minute")
        from asap.transport.sla_api import create_sla_router

        app.include_router(create_sla_router())
        client = TestClient(app)
        resp = client.get("/sla")
        assert resp.status_code == 503
        assert "SLA API not configured" in resp.json()["detail"]

    def test_sla_api_route_not_registered_without_storage(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """GET /sla returns 404 when sla_storage not set (route not registered)."""
        app = create_app(sample_manifest, rate_limit="999999/minute")
        client = TestClient(app)
        resp = client.get("/sla")
        assert resp.status_code == 404
