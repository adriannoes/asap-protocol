"""Tests for metrics cardinality protection against DoS attacks.

These tests validate that the server correctly protects against metrics cardinality
explosion by limiting the number of unique payload_type labels in metrics, even when
receiving many requests with random payload types.

Rate limiting is automatically disabled for these tests via NoRateLimitTestBase
to prevent interference from rate limiting tests.
"""

import re
import uuid
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.observability import get_metrics, reset_metrics
from asap.transport.handlers import HandlerRegistry
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.server import create_app

if TYPE_CHECKING:
    pass


from ..conftest import NoRateLimitTestBase


class TestMetricsCardinalityProtection(NoRateLimitTestBase):
    """Tests for metrics cardinality protection against DoS attacks."""

    @pytest.fixture
    def manifest(self) -> Manifest:
        """Create a sample manifest for testing."""
        return Manifest(
            id="urn:asap:agent:test-metrics",
            name="Test Metrics Server",
            version="1.0.0",
            description="Test server for metrics cardinality protection",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

    @pytest.fixture
    def app_with_registry(self, manifest: Manifest) -> FastAPI:
        """Create app with a registry that has only one handler registered.

        Rate limiting is automatically disabled via NoRateLimitTestBase.
        """
        registry = HandlerRegistry()
        # Register only one handler
        registry.register("task.request", lambda e, m: e)  # Simple echo
        # Rate limiting is automatically disabled via NoRateLimitTestBase
        return create_app(manifest, registry=registry, rate_limit="100000/minute")

    def test_metrics_cardinality_protection_against_dos(self, app_with_registry: FastAPI) -> None:
        """Test that sending many requests with random payload_types doesn't explode metrics."""
        client = TestClient(app_with_registry)
        metrics = get_metrics()
        reset_metrics()  # Start with clean metrics

        # Send many requests with random UUID payload_types
        # Use a smaller number to avoid rate limiting, but still test cardinality
        num_requests = 100
        unique_payload_types_sent = set()

        for i in range(num_requests):
            random_payload_type = f"unknown.type.{uuid.uuid4()}"
            unique_payload_types_sent.add(random_payload_type)
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:client",
                recipient="urn:asap:agent:test-metrics",
                payload_type=random_payload_type,  # Random UUID payload type
                payload=TaskRequest(
                    conversation_id="conv-1",
                    skill_id="echo",
                    input={"message": f"test-{i}"},
                ).model_dump(),
            )

            rpc_request = JsonRpcRequest(
                jsonrpc="2.0",
                method="asap.send",
                params={"envelope": envelope.model_dump(mode="json")},
                id=f"req-{i}",
            )

            # Send request (will fail with handler_not_found, but that's OK)
            client.post(
                "/asap",
                json=rpc_request.model_dump(mode="json"),
                headers={"Content-Type": "application/json"},
            )

        # Verify we sent many unique payload types
        assert len(unique_payload_types_sent) == num_requests, (
            "Test setup error: should have sent unique payload types"
        )

        # Export metrics and count unique payload_type labels
        prometheus_output = metrics.export_prometheus()

        # Count unique payload_type values in the metrics
        # Look for lines like: asap_requests_total{payload_type="other",status="error"} 100
        payload_type_pattern = r'payload_type="([^"]+)"'
        payload_types_found = set(re.findall(payload_type_pattern, prometheus_output))

        # The key test: should only have a small number of payload_types in metrics
        # (e.g., "other" and possibly "task.request"), NOT 100 different UUIDs
        # This proves cardinality protection is working
        assert len(payload_types_found) < 10, (
            f"Found {len(payload_types_found)} unique payload_types in metrics, "
            f"expected < 10 to prevent cardinality explosion. "
            f"Sent {len(unique_payload_types_sent)} unique payload_types, "
            f"but metrics only have {len(payload_types_found)}. "
            f"Found in metrics: {payload_types_found}"
        )

        # Verify that "other" is present (for unknown payload types)
        assert "other" in payload_types_found, (
            f"Expected 'other' payload_type for unknown handlers, but found: {payload_types_found}"
        )

        # The important assertion: we sent many unique payload_types but metrics
        # should only have a constant number of labels (cardinality protection working)
        assert len(payload_types_found) << len(unique_payload_types_sent), (
            f"Cardinality explosion detected! "
            f"Sent {len(unique_payload_types_sent)} unique payload_types, "
            f"but metrics have {len(payload_types_found)} labels. "
            f"This suggests metrics cardinality protection is NOT working."
        )
