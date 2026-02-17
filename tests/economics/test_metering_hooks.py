"""Tests for metering hooks (task lifecycle integration)."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.economics.hooks import record_task_usage
from asap.models.entities import Manifest
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.state.metering import InMemoryMeteringStore
from asap.models.entities import Capability, Endpoint, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler


@pytest.fixture
def metering_store() -> InMemoryMeteringStore:
    """Fresh InMemoryMeteringStore for each test."""
    return InMemoryMeteringStore()


@pytest.fixture
def sample_manifest() -> Manifest:
    """Sample manifest for agent_id."""
    return Manifest(
        id="urn:asap:agent:test-agent",
        name="Test Agent",
        version="1.0.0",
        description="Test",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def task_request_envelope(sample_manifest: Manifest) -> Envelope:
    """Envelope with task.request payload."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:consumer",
        recipient=sample_manifest.id,
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv_01",
            skill_id="echo",
            input={"test": "data"},
        ).model_dump(),
    )


@pytest.fixture
def task_response_envelope(sample_manifest: Manifest) -> Envelope:
    """Envelope with task.response payload (no metrics)."""
    return Envelope(
        asap_version="0.1",
        sender=sample_manifest.id,
        recipient="urn:asap:agent:consumer",
        payload_type="task.response",
        payload=TaskResponse(
            task_id="task_123",
            status="completed",
            result={"echoed": {"test": "data"}},
        ).model_dump(),
    )


class TestRecordTaskUsage:
    """Test record_task_usage extraction and recording."""

    def test_records_usage_with_measured_duration(
        self,
        metering_store: InMemoryMeteringStore,
        task_request_envelope: Envelope,
        task_response_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """record_task_usage stores event with duration, agent, consumer."""
        record_task_usage(
            metering_store,
            task_request_envelope,
            task_response_envelope,
            duration_ms=1234.5,
            manifest=sample_manifest,
        )

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 1
        assert events[0].task_id == "task_123"
        assert events[0].agent_id == sample_manifest.id
        assert events[0].consumer_id == "urn:asap:agent:consumer"
        assert events[0].metrics.duration_ms == 1234  # int(round(1234.5))
        assert events[0].metrics.tokens_in == 0
        assert events[0].metrics.tokens_out == 0
        assert events[0].metrics.api_calls == 0

    def test_extracts_agent_reported_metrics(
        self,
        metering_store: InMemoryMeteringStore,
        task_request_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """record_task_usage extracts tokens_in, tokens_out, api_calls from TaskResponse.metrics."""
        response_with_metrics = Envelope(
            asap_version="0.1",
            sender=sample_manifest.id,
            recipient="urn:asap:agent:consumer",
            payload_type="task.response",
            payload=TaskResponse(
                task_id="task_456",
                status="completed",
                result={},
                metrics={
                    "tokens_in": 1500,
                    "tokens_out": 2300,
                    "api_calls": 5,
                },
            ).model_dump(),
        )

        record_task_usage(
            metering_store,
            task_request_envelope,
            response_with_metrics,
            duration_ms=500.0,
            manifest=sample_manifest,
        )

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 1
        assert events[0].metrics.tokens_in == 1500
        assert events[0].metrics.tokens_out == 2300
        assert events[0].metrics.api_calls == 5
        assert events[0].metrics.duration_ms == 500

    def test_skips_non_task_request(
        self,
        metering_store: InMemoryMeteringStore,
        task_response_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """record_task_usage skips when envelope is not task.request."""
        other_envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:other",
            recipient=sample_manifest.id,
            payload_type="state.query",
            payload={},
        )
        record_task_usage(
            metering_store,
            other_envelope,
            task_response_envelope,
            duration_ms=100.0,
            manifest=sample_manifest,
        )
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 0

    def test_skips_when_response_not_task_response(
        self,
        metering_store: InMemoryMeteringStore,
        task_request_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """record_task_usage skips when response is not task.response."""
        other_response = Envelope(
            asap_version="0.1",
            sender=sample_manifest.id,
            recipient="urn:asap:agent:consumer",
            payload_type="task.update",
            payload={"task_id": "t1", "status": "working"},
        )
        record_task_usage(
            metering_store,
            task_request_envelope,
            other_response,
            duration_ms=100.0,
            manifest=sample_manifest,
        )
        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 0


class TestHandlerRegistryMetering:
    """Test HandlerRegistry integration with metering_store."""

    @pytest.mark.asyncio
    async def test_registry_records_on_task_completion(
        self,
        metering_store: InMemoryMeteringStore,
        task_request_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """HandlerRegistry with metering_store records usage after task.request."""
        registry = HandlerRegistry(metering_store=metering_store)
        registry.register("task.request", create_echo_handler())

        response = await registry.dispatch_async(task_request_envelope, sample_manifest)

        assert response.payload_type == "task.response"
        task_id = response.payload.get("task_id")
        assert task_id is not None

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 1
        assert events[0].task_id == task_id
        assert events[0].agent_id == sample_manifest.id
        assert events[0].consumer_id == "urn:asap:agent:consumer"
        assert events[0].metrics.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_registry_no_double_counting(
        self,
        metering_store: InMemoryMeteringStore,
        task_request_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """Single dispatch records exactly one event (no double-counting)."""
        registry = HandlerRegistry(metering_store=metering_store)
        registry.register("task.request", create_echo_handler())

        await registry.dispatch_async(task_request_envelope, sample_manifest)

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_registry_without_metering_store_does_not_record(
        self,
        task_request_envelope: Envelope,
        sample_manifest: Manifest,
    ) -> None:
        """HandlerRegistry without metering_store does not fail (no recording)."""
        registry = HandlerRegistry(metering_store=None)
        registry.register("task.request", create_echo_handler())

        response = await registry.dispatch_async(task_request_envelope, sample_manifest)
        assert response.payload_type == "task.response"


class TestCreateAppMeteringIntegration:
    """Test create_app with metering_store via HTTP."""

    def test_create_app_with_metering_store_records_on_post_asap(
        self,
        metering_store: InMemoryMeteringStore,
        sample_manifest: Manifest,
        isolated_rate_limiter: object,
    ) -> None:
        """POST /asap with metering_store records usage to store."""
        from asap.transport.server import create_app

        app: FastAPI = create_app(
            sample_manifest,
            metering_store=metering_store,
            rate_limit="999999/minute",
        )
        if isolated_rate_limiter is not None:
            app.state.limiter = isolated_rate_limiter

        client = TestClient(app)
        rpc_body = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": {
                    "asap_version": "0.1",
                    "sender": "urn:asap:agent:consumer",
                    "recipient": sample_manifest.id,
                    "payload_type": "task.request",
                    "payload": {
                        "conversation_id": "conv_01",
                        "skill_id": "echo",
                        "input": {"test": "data"},
                    },
                }
            },
            "id": "req-1",
        }

        response = client.post("/asap", json=rpc_body)
        assert response.status_code == 200

        data = response.json()
        assert "result" in data
        assert "envelope" in data["result"]

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 1, 1, tzinfo=timezone.utc)
        events = metering_store.query(sample_manifest.id, start, end)
        assert len(events) == 1
        assert events[0].agent_id == sample_manifest.id
        assert events[0].consumer_id == "urn:asap:agent:consumer"
