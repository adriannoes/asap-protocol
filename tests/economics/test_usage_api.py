"""Integration tests for usage metering REST API (GET /usage, etc.)."""

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from asap.economics import InMemoryMeteringStorage, UsageMetrics
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.server import create_app


def _run(coro):
    """Run async coroutine from sync test (for storage setup)."""
    return asyncio.run(coro)


@pytest.fixture
def metering_storage() -> InMemoryMeteringStorage:
    """Fresh InMemoryMeteringStorage for usage API tests."""
    return InMemoryMeteringStorage()


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
def app_with_usage_api(
    sample_manifest: Manifest,
    metering_storage: InMemoryMeteringStorage,
) -> tuple[Manifest, InMemoryMeteringStorage]:
    """Create app with metering_storage (usage API enabled)."""
    return sample_manifest, metering_storage


class TestUsageAPIGetUsage:
    """Test GET /usage endpoint."""

    def test_get_usage_returns_empty_when_no_data(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage returns empty data when storage is empty."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert data["data"] == []
        assert data["count"] == 0

    def test_get_usage_returns_recorded_events(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage returns events recorded via POST or handlers."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["task_id"] == "t1"
        assert data["data"][0]["tokens_in"] == 10
        assert data["data"][0]["tokens_out"] == 20

    def test_get_usage_with_filters(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage?agent_id=... filters by agent."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a2",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage", params={"agent_id": "a1"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["agent_id"] == "a1"

    def test_get_usage_with_task_id_filter(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage?task_id=... filters by task."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage", params={"task_id": "t1"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 1
        assert resp.json()["data"][0]["task_id"] == "t1"


class TestUsageAPIGetAggregate:
    """Test GET /usage/aggregate endpoint."""

    def test_aggregate_by_agent(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/aggregate?group_by=agent returns aggregates."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=5,
                    tokens_out=5,
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/aggregate", params={"group_by": "agent"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["group_by"] == "agent"
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "a1"
        assert data["data"][0]["total_tokens"] == 40
        assert data["data"][0]["total_tasks"] == 2

    def test_aggregate_with_start_end_filters_by_time_range(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/aggregate?group_by=agent&start=...&end=... filters by time range."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=5,
                    tokens_out=5,
                    timestamp=datetime(2026, 2, 19, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get(
            "/usage/aggregate",
            params={
                "group_by": "agent",
                "start": "2026-02-17T00:00:00+00:00",
                "end": "2026-02-18T00:00:00+00:00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "a1"
        assert data["data"][0]["total_tokens"] == 30
        assert data["data"][0]["total_tasks"] == 1

    def test_aggregate_invalid_group_by_returns_400(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/aggregate?group_by=invalid returns 400."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/aggregate", params={"group_by": "invalid"})
        assert resp.status_code == 400


class TestUsageAPIGetSummary:
    """Test GET /usage/summary endpoint."""

    def test_summary_returns_empty_when_no_data(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/summary returns zeros when storage is empty."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 0
        assert data["total_tokens"] == 0
        assert data["total_duration_ms"] == 0
        assert data["unique_agents"] == 0
        assert data["unique_consumers"] == 0
        assert data["total_api_calls"] == 0

    def test_summary_returns_totals(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/summary returns total_tasks, total_tokens, etc."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    duration_ms=100,
                    api_calls=1,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a2",
                    consumer_id="c1",
                    tokens_in=5,
                    tokens_out=15,
                    duration_ms=200,
                    api_calls=2,
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 2
        assert data["total_tokens"] == 50
        assert data["total_duration_ms"] == 300
        assert data["unique_agents"] == 2
        assert data["unique_consumers"] == 1
        assert data["total_api_calls"] == 3

    def test_summary_with_start_end_filters_by_period(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/summary?start=...&end=... filters by time range."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    duration_ms=100,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=5,
                    tokens_out=5,
                    duration_ms=50,
                    timestamp=datetime(2026, 2, 19, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get(
            "/usage/summary",
            params={
                "start": "2026-02-17T00:00:00+00:00",
                "end": "2026-02-18T00:00:00+00:00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 1
        assert data["total_tokens"] == 30
        assert data["total_duration_ms"] == 100
        assert data["unique_agents"] == 1
        assert data["unique_consumers"] == 1


class TestUsageAPIPostUsage:
    """Test POST /usage endpoint (agent self-report)."""

    def test_post_usage_records_metrics(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage with valid body records metrics."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        body = {
            "task_id": "t1",
            "agent_id": "a1",
            "consumer_id": "c1",
            "tokens_in": 100,
            "tokens_out": 200,
            "duration_ms": 500,
            "api_calls": 2,
            "timestamp": "2026-02-17T12:00:00+00:00",
        }
        resp = client.post("/usage", json=body)
        assert resp.status_code == 201
        assert resp.json()["status"] == "recorded"
        assert resp.json()["task_id"] == "t1"

        get_resp = client.get("/usage")
        assert get_resp.status_code == 200
        assert len(get_resp.json()["data"]) == 1
        assert get_resp.json()["data"][0]["tokens_in"] == 100


class TestUsageAPIPostBatch:
    """Test POST /usage/batch endpoint."""

    def test_batch_records_multiple_events(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage/batch records all events."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        body = {
            "events": [
                {
                    "task_id": "t1",
                    "agent_id": "a1",
                    "consumer_id": "c1",
                    "timestamp": "2026-02-17T12:00:00+00:00",
                },
                {
                    "task_id": "t2",
                    "agent_id": "a1",
                    "consumer_id": "c1",
                    "timestamp": "2026-02-17T13:00:00+00:00",
                },
            ]
        }
        resp = client.post("/usage/batch", json=body)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "recorded"
        assert data["count"] == 2
        assert data["task_ids"] == ["t1", "t2"]

        get_resp = client.get("/usage")
        assert get_resp.status_code == 200
        assert len(get_resp.json()["data"]) == 2

    def test_batch_invalid_payload_returns_400(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage/batch with invalid payload returns 400."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.post("/usage/batch", json={"events": [{"invalid": "data"}]})
        assert resp.status_code == 400

    def test_batch_empty_events_returns_400(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage/batch with empty events returns 400."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.post("/usage/batch", json={"events": []})
        assert resp.status_code == 400


class TestUsageAPIGetAgents:
    """Test GET /usage/agents endpoint."""

    def test_agents_returns_distinct_with_usage(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/agents returns agent aggregates."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a2",
                    consumer_id="c1",
                    tokens_in=5,
                    tokens_out=5,
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        agent_ids = {a["agent_id"] for a in data["data"]}
        assert agent_ids == {"a1", "a2"}


class TestUsageAPIGetConsumers:
    """Test GET /usage/consumers endpoint."""

    def test_consumers_returns_distinct_with_usage(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/consumers returns consumer aggregates."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t2",
                    agent_id="a1",
                    consumer_id="c2",
                    timestamp=datetime(2026, 2, 17, 13, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/consumers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        consumer_ids = {c["consumer_id"] for c in data["data"]}
        assert consumer_ids == {"c1", "c2"}


class TestUsageAPIGetStats:
    """Test GET /usage/stats endpoint."""

    def test_stats_returns_storage_info(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/stats returns total_events, oldest_timestamp."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_events"] == 1
        assert "oldest_timestamp" in data

    def test_stats_empty_returns_zeros(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/stats on empty storage returns total_events=0."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/stats")
        assert resp.status_code == 200
        assert resp.json()["total_events"] == 0
        assert resp.json()["oldest_timestamp"] is None


class TestUsageAPIPostPurge:
    """Test POST /usage/purge endpoint."""

    def test_purge_returns_removed_count(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """POST /usage/purge triggers purge_expired and returns removed count."""
        from datetime import timedelta

        store = InMemoryMeteringStorage(retention_ttl_seconds=3600)
        now = datetime.now(timezone.utc)
        old = now - timedelta(seconds=7200)
        _run(
            store.record(
                UsageMetrics(task_id="old", agent_id="a1", consumer_id="c1", timestamp=old)
            )
        )
        _run(
            store.record(
                UsageMetrics(task_id="new", agent_id="a1", consumer_id="c1", timestamp=now)
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=store,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.post("/usage/purge")
        assert resp.status_code == 200
        assert resp.json()["status"] == "purged"
        assert resp.json()["removed"] == 1


class TestUsageAPIPostValidate:
    """Test POST /usage/validate endpoint."""

    def test_validate_valid_payload_returns_valid_true(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage/validate with valid payload returns valid=True."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        body = {
            "task_id": "t1",
            "agent_id": "a1",
            "consumer_id": "c1",
            "timestamp": "2026-02-17T12:00:00+00:00",
        }
        resp = client.post("/usage/validate", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["task_id"] == "t1"
        assert data["agent_id"] == "a1"

    def test_validate_invalid_payload_returns_valid_false(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage/validate with invalid payload returns valid=False."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.post("/usage/validate", json={"invalid": "data"})
        assert resp.status_code == 200
        assert resp.json()["valid"] is False
        assert "error" in resp.json()


class TestUsageAPIExport:
    """Test GET /usage/export endpoint."""

    def test_export_json(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/export?format=json returns JSON."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/export", params={"export_format": "json"})
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert len(data["data"]) == 1

    def test_export_csv(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """GET /usage/export?format=csv returns CSV."""
        _run(
            metering_storage.record(
                UsageMetrics(
                    task_id="t1",
                    agent_id="a1",
                    consumer_id="c1",
                    tokens_in=10,
                    tokens_out=20,
                    timestamp=datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc),
                )
            )
        )
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        resp = client.get("/usage/export", params={"export_format": "csv"})
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/csv; charset=utf-8"
        content = resp.text
        assert "tokens_in,tokens_out" in content
        assert "t1,a1,c1,10,20" in content


class TestUsageAPIConfiguration:
    """Test configuration edge cases."""

    def test_usage_api_returns_503_when_storage_missing(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """Usage endpoints return 503 if metering_storage is not configured."""
        # Create app WITHOUT metering_storage
        app = create_app(sample_manifest)
        # We need to manually include the router because create_app only includes it 
        # if metering_storage IS provided. 
        # However, if we include it manually but storage is missing on state, it should 503.
        from asap.transport.usage_api import create_usage_router
        app.include_router(create_usage_router())
        
        client = TestClient(app)
        
        # GET /usage
        resp = client.get("/usage")
        assert resp.status_code == 503
        assert "Usage API not configured" in resp.json()["detail"]
        
        # POST /usage
        resp = client.post("/usage", json={})
        assert resp.status_code == 503


class TestUsageAPIRateLimiting:
    """Test rate limiting on usage API."""

    def test_usage_api_enforces_rate_limit(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """Usage API respects app.state.limiter."""
        # Create app with very strict limit
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="1/minute",
        )
        client = TestClient(app)
        
        # First request succeeds
        resp = client.get("/usage")
        assert resp.status_code == 200
        
        # Second request fails
        resp = client.get("/usage")
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.text

    def test_usage_api_ignores_missing_limiter(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """Usage API proceeds if limiter is not configured on app state."""
        app = create_app(sample_manifest, metering_storage=metering_storage)
        # Manually remove limiter to trigger the 'if limiter is not None' else branch
        if hasattr(app.state, "limiter"):
            delattr(app.state, "limiter")
            
        client = TestClient(app)
        resp = client.get("/usage")
        assert resp.status_code == 200


class TestUsageAPIPostUsageValidation:
    """Additional validation tests for POST /usage."""

    def test_post_usage_invalid_body_returns_400(
        self,
        sample_manifest: Manifest,
        metering_storage: InMemoryMeteringStorage,
    ) -> None:
        """POST /usage with invalid body returns 400 (validation error)."""
        app = create_app(
            sample_manifest,
            metering_storage=metering_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)
        
        # Missing required fields
        resp = client.post("/usage", json={"task_id": "t1"})
        assert resp.status_code == 400
        # Check that it's the Pydantic validation error message
        assert "Field required" in resp.text or "validation error" in resp.text.lower()


class TestUsageAPINotConfigured:
    def test_get_usage_returns_404_when_not_configured(
        self,
        sample_manifest: Manifest,
    ) -> None:
        """GET /usage returns 404 when metering_storage not set (route not registered)."""
        app = create_app(sample_manifest, rate_limit="999999/minute")
        client = TestClient(app)
        resp = client.get("/usage")
        assert resp.status_code == 404
