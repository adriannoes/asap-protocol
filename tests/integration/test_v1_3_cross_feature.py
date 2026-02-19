"""Cross-feature integration tests for v1.3.0 (SLA + Metering + Delegation + Health).

Validates that SLA integrates correctly with Metering (E1), Delegation (E2),
and Health (v1.1) endpoints.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from joserfc import jwk, jwt as jose_jwt

from asap.auth import OAuth2Config
from asap.crypto.keys import generate_keypair
from asap.economics import (
    InMemoryMeteringStorage,
    InMemorySLAStorage,
    SLAMetrics,
    UsageMetrics,
    compute_error_rate_percent,
    compute_latency_p95_ms,
    compute_uptime_percent,
)
from asap.economics.delegation_storage import InMemoryDelegationStorage
from asap.models.entities import (
    Capability,
    Endpoint,
    Manifest,
    Skill,
    SLADefinition,
)
from asap.transport.server import create_app


def _run(coro: Any) -> Any:
    """Run async coroutine from sync test."""
    return asyncio.run(coro)


def _usage_metrics_to_sla_metrics(
    agent_id: str,
    events: list[UsageMetrics],
    period_start: datetime,
    period_end: datetime,
    uptime_percent: float = 100.0,
) -> SLAMetrics | None:
    """Derive SLAMetrics from UsageMetrics (metering data).

    Latency p95 from duration_ms; error rate from completed/failed (assume all
    recorded are completed, failed=0 unless we have failure data).
    """
    if not events:
        return None
    durations = [e.duration_ms for e in events]
    tasks_completed = len(events)
    tasks_failed = 0
    return SLAMetrics(
        agent_id=agent_id,
        period_start=period_start,
        period_end=period_end,
        uptime_percent=uptime_percent,
        latency_p95_ms=compute_latency_p95_ms(durations),
        error_rate_percent=compute_error_rate_percent(tasks_completed, tasks_failed),
        tasks_completed=tasks_completed,
        tasks_failed=tasks_failed,
    )


@pytest.fixture
def cross_feature_manifest() -> Manifest:
    """Manifest with SLA for cross-feature tests."""
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


class TestSlaMeteringIntegration:
    """SLA + Metering: SLA metrics derived from metering data."""

    def test_sla_metrics_derived_from_metering_latency_p95_matches(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """Latency p95 from task metrics (metering) matches SLA calculation."""
        metering = InMemoryMeteringStorage()
        sla_storage = InMemorySLAStorage()

        period_start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        period_end = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)

        events = [
            UsageMetrics(
                task_id="t1",
                agent_id="urn:asap:agent:test-server",
                consumer_id="urn:asap:agent:consumer",
                duration_ms=100,
                timestamp=period_start,
            ),
            UsageMetrics(
                task_id="t2",
                agent_id="urn:asap:agent:test-server",
                consumer_id="urn:asap:agent:consumer",
                duration_ms=200,
                timestamp=period_start,
            ),
            UsageMetrics(
                task_id="t3",
                agent_id="urn:asap:agent:test-server",
                consumer_id="urn:asap:agent:consumer",
                duration_ms=300,
                timestamp=period_start,
            ),
        ]
        for e in events:
            _run(metering.record(e))

        sla_metrics = _usage_metrics_to_sla_metrics(
            "urn:asap:agent:test-server",
            events,
            period_start,
            period_end,
        )
        assert sla_metrics is not None
        expected_p95 = compute_latency_p95_ms([100, 200, 300])
        assert sla_metrics.latency_p95_ms == expected_p95

        _run(sla_storage.record_metrics(sla_metrics))

        app = create_app(
            cross_feature_manifest,
            metering_storage=metering,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)

        usage_resp = client.get("/usage")
        assert usage_resp.status_code == 200
        usage_data = usage_resp.json()["data"]
        assert len(usage_data) == 3

        sla_resp = client.get("/sla/history")
        assert sla_resp.status_code == 200
        sla_data = sla_resp.json()["data"]
        assert len(sla_data) == 1
        assert sla_data[0]["latency_p95_ms"] == expected_p95


class TestSlaHealthIntegration:
    """SLA + Health: Uptime from health checks; downtime triggers breach."""

    def test_uptime_calculation_uses_health_check_pattern(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """Uptime percentage computed from ok_count/total_count (health check pattern)."""
        ok_count = 98
        total_count = 100
        uptime = compute_uptime_percent(ok_count, total_count)
        assert uptime == 98.0

    def test_low_uptime_triggers_availability_breach(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """SLAMetrics with uptime below SLA threshold triggers availability breach."""
        from asap.economics.sla import evaluate_breach_conditions

        period_start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        period_end = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)

        metrics = SLAMetrics(
            agent_id="urn:asap:agent:test-server",
            period_start=period_start,
            period_end=period_end,
            uptime_percent=97.0,
            latency_p95_ms=100,
            error_rate_percent=0.0,
            tasks_completed=100,
            tasks_failed=0,
        )
        conditions = evaluate_breach_conditions(
            cross_feature_manifest.sla,
            metrics,
        )
        assert len(conditions) >= 1
        assert any(c.breach_type == "availability" for c in conditions)

    def test_health_endpoint_and_sla_both_available(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """App with SLA and health endpoints serves both."""
        sla_storage = InMemorySLAStorage()
        app = create_app(
            cross_feature_manifest,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)

        health_resp = client.get("/.well-known/asap/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["status"] == "healthy"

        sla_resp = client.get("/sla")
        assert sla_resp.status_code == 200


class TestSlaDelegationIntegration:
    """SLA + Delegation: Delegated agent SLA tracked separately."""

    def test_delegated_agent_sla_tracked_separately(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """SLA metrics for delegated agent appear in GET /sla when filtered."""
        key_set, oauth2_key = _make_oauth2_jwk()
        delegation_key_store = _make_delegation_key_store()
        delegation_storage = InMemoryDelegationStorage()
        sla_storage = InMemorySLAStorage()

        now = datetime.now(timezone.utc)
        delegate_metrics = SLAMetrics(
            agent_id="urn:asap:agent:delegate",
            period_start=now - timedelta(hours=1),
            period_end=now,
            uptime_percent=99.5,
            latency_p95_ms=150,
            error_rate_percent=0.5,
            tasks_completed=50,
            tasks_failed=0,
        )
        _run(sla_storage.record_metrics(delegate_metrics))

        async def jwks_fetcher(_uri: str) -> jwk.KeySet:
            return key_set

        app = create_app(
            cross_feature_manifest,
            oauth2_config=OAuth2Config(
                jwks_uri="https://auth.example.com/jwks.json",
                path_prefix="/asap",
                jwks_fetcher=jwks_fetcher,
            ),
            delegation_key_store=delegation_key_store,
            delegation_storage=delegation_storage,
            sla_storage=sla_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)

        bearer = _make_bearer_token(oauth2_key, sub="urn:asap:agent:delegator")
        create_resp = client.post(
            "/asap/delegations",
            json={
                "delegate": "urn:asap:agent:delegate",
                "scopes": ["task.execute"],
                "max_tasks": 5,
            },
            headers={"Authorization": f"Bearer {bearer}"},
        )
        assert create_resp.status_code == 201

        sla_resp = client.get("/sla", params={"agent_id": "urn:asap:agent:delegate"})
        assert sla_resp.status_code == 200
        data = sla_resp.json()
        assert len(data["data"]) == 1
        assert data["data"][0]["agent_id"] == "urn:asap:agent:delegate"


class TestFullV13Integration:
    """Full integration: delegation -> metering -> SLA -> breach."""

    def test_full_flow_delegation_metering_sla_breach(
        self,
        cross_feature_manifest: Manifest,
    ) -> None:
        """Create delegation, execute tasks (metering), check SLA, trigger breach."""
        metering = InMemoryMeteringStorage()
        sla_storage = InMemorySLAStorage()
        key_set, oauth2_key = _make_oauth2_jwk()
        delegation_key_store = _make_delegation_key_store()
        delegation_storage = InMemoryDelegationStorage()

        period_start = datetime(2026, 2, 18, 0, 0, 0, tzinfo=timezone.utc)
        period_end = datetime(2026, 2, 18, 1, 0, 0, tzinfo=timezone.utc)

        high_latency_events = [
            UsageMetrics(
                task_id="t1",
                agent_id="urn:asap:agent:delegate",
                consumer_id="urn:asap:agent:delegator",
                duration_ms=800,
                timestamp=period_start,
            ),
        ]
        for e in high_latency_events:
            _run(metering.record(e))

        sla_metrics = _usage_metrics_to_sla_metrics(
            "urn:asap:agent:delegate",
            high_latency_events,
            period_start,
            period_end,
        )
        assert sla_metrics is not None
        assert sla_metrics.latency_p95_ms == 800
        _run(sla_storage.record_metrics(sla_metrics))

        from asap.economics.sla import BreachDetector, evaluate_breach_conditions

        delegate_sla = SLADefinition(
            availability="99%",
            max_latency_p95_ms=500,
            max_error_rate="1%",
        )
        conditions = evaluate_breach_conditions(delegate_sla, sla_metrics)
        assert len(conditions) >= 1
        assert any(c.breach_type == "latency" for c in conditions)

        detector = BreachDetector(storage=sla_storage)
        _run(
            detector.check_and_record(
                "urn:asap:agent:delegate",
                delegate_sla,
                sla_metrics,
            )
        )

        async def jwks_fetcher(_uri: str) -> jwk.KeySet:
            return key_set

        app = create_app(
            cross_feature_manifest,
            metering_storage=metering,
            sla_storage=sla_storage,
            oauth2_config=OAuth2Config(
                jwks_uri="https://auth.example.com/jwks.json",
                path_prefix="/asap",
                jwks_fetcher=jwks_fetcher,
            ),
            delegation_key_store=delegation_key_store,
            delegation_storage=delegation_storage,
            rate_limit="999999/minute",
        )
        client = TestClient(app)

        usage_resp = client.get("/usage")
        assert usage_resp.status_code == 200
        assert len(usage_resp.json()["data"]) == 1

        breaches_resp = client.get("/sla/breaches")
        assert breaches_resp.status_code == 200
        breaches = breaches_resp.json()["data"]
        assert len(breaches) >= 1
        assert any(b["breach_type"] == "latency" for b in breaches)


def _make_oauth2_jwk() -> tuple[jwk.KeySet, jwk.RSAKey]:
    key = jwk.RSAKey.generate_key(2048, private=True)
    key_set = jwk.KeySet.import_key_set({"keys": [key.as_dict(private=False)]})
    return key_set, key


def _make_delegation_key_store() -> Any:
    private_key, _ = generate_keypair()

    def store(_delegator_urn: str) -> Any:
        return private_key

    return store


def _make_bearer_token(oauth2_key: jwk.RSAKey, sub: str = "urn:asap:agent:delegator") -> str:
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "sub": sub,
        "scope": "asap:execute",
        "exp": now + 3600,
    }
    return jose_jwt.encode(header, claims, oauth2_key)
