"""End-to-end tests for ASAP protocol transport layer.

This module tests the full round-trip communication between
ASAP client and server, verifying end-to-end functionality.
"""

from typing import TYPE_CHECKING

import httpx
import pytest
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest, TaskResponse
from asap.testing import (
    assert_envelope_valid,
    assert_response_correlates,
    assert_task_completed,
)
from asap.transport.client import ASAPClient
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase


# Test fixtures
@pytest.fixture
def test_manifest() -> Manifest:
    """Create a test manifest for integration tests."""
    return Manifest(
        id="urn:asap:agent:integration-test",
        name="Integration Test Agent",
        version="1.0.0",
        description="Agent for integration testing",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(id="echo", description="Echo skill for testing"),
                Skill(id="greet", description="Greeting skill"),
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def test_app(test_manifest: Manifest) -> TestClient:
    """Create a test client with the ASAP app.

    Rate limiting is automatically disabled via NoRateLimitTestBase.
    """
    app = create_app(test_manifest, rate_limit="100000/minute")
    return TestClient(app)


@pytest.fixture
def sample_task_request_envelope() -> Envelope:
    """Create a sample TaskRequest envelope."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:test-client",
        recipient="urn:asap:agent:integration-test",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv_integration_123",
            skill_id="echo",
            input={"message": "Hello from integration test!"},
        ).model_dump(),
        trace_id="trace_integration_001",
    )


class TestFullRoundTrip(NoRateLimitTestBase):
    """Tests for complete request-response round-trip."""

    def test_client_to_server_round_trip(
        self, test_app: TestClient, sample_task_request_envelope: Envelope
    ) -> None:
        """Test sending request and receiving response through full stack."""
        # Create JSON-RPC request
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": sample_task_request_envelope.model_dump(mode="json"),
            },
            "id": "integration-test-1",
        }

        # Send request to server
        response = test_app.post("/asap", json=json_rpc_request)

        # Verify HTTP response
        assert response.status_code == 200

        # Parse JSON-RPC response
        json_rpc_response = response.json()
        assert json_rpc_response["jsonrpc"] == "2.0"
        assert json_rpc_response["id"] == "integration-test-1"
        assert "result" in json_rpc_response
        assert "envelope" in json_rpc_response["result"]

        # Parse response envelope
        response_envelope = Envelope(**json_rpc_response["result"]["envelope"])

        # Verify response envelope
        assert_envelope_valid(
            response_envelope, allowed_payload_types=["task.response"]
        )
        assert_task_completed(response_envelope)
        assert response_envelope.sender == "urn:asap:agent:integration-test"
        assert response_envelope.recipient == sample_task_request_envelope.sender
        assert_response_correlates(
            sample_task_request_envelope, response_envelope
        )
        assert response_envelope.trace_id == sample_task_request_envelope.trace_id

    def test_response_contains_task_response_payload(
        self, test_app: TestClient, sample_task_request_envelope: Envelope
    ) -> None:
        """Test that response contains valid TaskResponse payload."""
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": sample_task_request_envelope.model_dump(mode="json"),
            },
            "id": "integration-test-2",
        }

        response = test_app.post("/asap", json=json_rpc_request)
        json_rpc_response = response.json()
        response_envelope = Envelope(**json_rpc_response["result"]["envelope"])

        # Parse and verify TaskResponse
        task_response = TaskResponse(**response_envelope.payload)
        assert task_response.task_id is not None
        assert task_response.status == TaskStatus.COMPLETED

    def test_echo_returns_input_data(
        self, test_app: TestClient, sample_task_request_envelope: Envelope
    ) -> None:
        """Test that echo handler returns the input data."""
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": sample_task_request_envelope.model_dump(mode="json"),
            },
            "id": "integration-test-3",
        }

        response = test_app.post("/asap", json=json_rpc_request)
        json_rpc_response = response.json()
        response_envelope = Envelope(**json_rpc_response["result"]["envelope"])
        task_response = TaskResponse(**response_envelope.payload)

        # Verify echo result
        assert task_response.result is not None
        assert "echoed" in task_response.result
        assert task_response.result["echoed"] == {"message": "Hello from integration test!"}


class TestManifestDiscovery(NoRateLimitTestBase):
    """Tests for manifest discovery endpoint."""

    def test_manifest_accessible_via_well_known(self, test_app: TestClient) -> None:
        """Test manifest is accessible at .well-known endpoint."""
        response = test_app.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        manifest_data = response.json()

        assert manifest_data["id"] == "urn:asap:agent:integration-test"
        assert manifest_data["name"] == "Integration Test Agent"
        assert manifest_data["version"] == "1.0.0"

    def test_manifest_contains_skills(self, test_app: TestClient) -> None:
        """Test manifest contains skill definitions."""
        response = test_app.get("/.well-known/asap/manifest.json")
        manifest_data = response.json()

        skills = manifest_data["capabilities"]["skills"]
        skill_ids = [s["id"] for s in skills]

        assert "echo" in skill_ids
        assert "greet" in skill_ids

    def test_manifest_contains_endpoints(self, test_app: TestClient) -> None:
        """Test manifest contains endpoint information."""
        response = test_app.get("/.well-known/asap/manifest.json")
        manifest_data = response.json()

        assert "endpoints" in manifest_data
        assert manifest_data["endpoints"]["asap"] == "http://localhost:8000/asap"


class TestCorrelationAndTracing(NoRateLimitTestBase):
    """Tests for correlation ID and trace ID propagation."""

    def test_correlation_id_matches_request_id(
        self, test_app: TestClient, sample_task_request_envelope: Envelope
    ) -> None:
        """Test correlation_id in response matches request envelope id."""
        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": sample_task_request_envelope.model_dump(mode="json"),
            },
            "id": "correlation-test-1",
        }

        response = test_app.post("/asap", json=json_rpc_request)
        json_rpc_response = response.json()
        response_envelope = Envelope(**json_rpc_response["result"]["envelope"])

        assert_response_correlates(
            sample_task_request_envelope, response_envelope
        )

    def test_trace_id_propagated_through_response(self, test_app: TestClient) -> None:
        """Test trace_id is propagated from request to response."""
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:tracer",
            recipient="urn:asap:agent:integration-test",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_trace_test",
                skill_id="echo",
                input={"data": "test"},
            ).model_dump(),
            trace_id="my-custom-trace-id-12345",
        )

        json_rpc_request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {"envelope": envelope.model_dump(mode="json")},
            "id": "trace-test-1",
        }

        response = test_app.post("/asap", json=json_rpc_request)
        json_rpc_response = response.json()
        response_envelope = Envelope(**json_rpc_response["result"]["envelope"])

        assert response_envelope.trace_id == "my-custom-trace-id-12345"

    def test_multiple_requests_have_unique_response_ids(self, test_app: TestClient) -> None:
        """Test each request generates unique response envelope IDs."""
        response_ids = []

        for i in range(5):
            envelope = Envelope(
                asap_version="0.1",
                sender="urn:asap:agent:multi-requester",
                recipient="urn:asap:agent:integration-test",
                payload_type="task.request",
                payload=TaskRequest(
                    conversation_id=f"conv_multi_{i}",
                    skill_id="echo",
                    input={"iteration": i},
                ).model_dump(),
            )

            json_rpc_request = {
                "jsonrpc": "2.0",
                "method": "asap.send",
                "params": {"envelope": envelope.model_dump(mode="json")},
                "id": f"multi-{i}",
            }

            response = test_app.post("/asap", json=json_rpc_request)
            json_rpc_response = response.json()
            response_envelope = Envelope(**json_rpc_response["result"]["envelope"])
            response_ids.append(response_envelope.id)

        # All response IDs should be unique
        assert len(response_ids) == len(set(response_ids))


class TestErrorScenarios(NoRateLimitTestBase):
    """Tests for error handling in integration scenarios."""

    def test_invalid_json_returns_parse_error(self, test_app: TestClient) -> None:
        """Test invalid JSON returns JSON-RPC parse error."""
        response = test_app.post(
            "/asap",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        json_rpc_response = response.json()
        assert "error" in json_rpc_response

    def test_missing_method_returns_error(self, test_app: TestClient) -> None:
        """Test missing method field returns error."""
        response = test_app.post(
            "/asap",
            json={"jsonrpc": "2.0", "params": {}, "id": "no-method"},
        )

        assert response.status_code == 200
        json_rpc_response = response.json()
        assert "error" in json_rpc_response

    def test_unknown_method_returns_method_not_found(self, test_app: TestClient) -> None:
        """Test unknown method returns method not found error."""
        response = test_app.post(
            "/asap",
            json={
                "jsonrpc": "2.0",
                "method": "unknown.method",
                "params": {},
                "id": "unknown-method",
            },
        )

        assert response.status_code == 200
        json_rpc_response = response.json()
        assert "error" in json_rpc_response
        assert json_rpc_response["error"]["code"] == -32601  # Method not found


class TestAsyncClientIntegration(NoRateLimitTestBase):
    """Tests for ASAPClient with real server (using httpx MockTransport)."""

    async def test_async_client_with_mock_server(
        self, test_manifest: Manifest, sample_task_request_envelope: Envelope
    ) -> None:
        """Test ASAPClient communicating with mocked server responses."""
        # Create expected response
        response_envelope = Envelope(
            asap_version="0.1",
            sender=test_manifest.id,
            recipient=sample_task_request_envelope.sender,
            payload_type="task.response",
            payload=TaskResponse(
                task_id="task_async_001",
                status=TaskStatus.COMPLETED,
                result={"echoed": sample_task_request_envelope.payload.get("input", {})},
            ).model_dump(),
            correlation_id=sample_task_request_envelope.id,
            trace_id=sample_task_request_envelope.trace_id,
        )

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "jsonrpc": "2.0",
                    "result": {"envelope": response_envelope.model_dump(mode="json")},
                    "id": "req-1",
                },
            )

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            response = await client.send(sample_task_request_envelope)

        assert response.payload_type == "task.response"
        assert response.correlation_id == sample_task_request_envelope.id

    async def test_async_client_handles_server_error(
        self, sample_task_request_envelope: Envelope
    ) -> None:
        """Test ASAPClient handles server error responses."""
        from asap.transport.client import ASAPRemoteError

        def mock_transport(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": "Internal error"},
                    "id": "req-1",
                },
            )

        async with ASAPClient(
            "http://localhost:8000",
            transport=httpx.MockTransport(mock_transport),
        ) as client:
            with pytest.raises(ASAPRemoteError) as exc_info:
                await client.send(sample_task_request_envelope)

            assert exc_info.value.code == -32603


class TestHandlerRegistryIntegration(NoRateLimitTestBase):
    """Tests for HandlerRegistry with server integration."""

    def test_custom_handler_with_registry(self, test_manifest: Manifest) -> None:
        """Test using custom handler registry with server."""

        # Create custom handler
        def custom_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
            return Envelope(
                asap_version="0.1",
                sender=manifest.id,
                recipient=envelope.sender,
                payload_type="task.response",
                payload=TaskResponse(
                    task_id="custom_task_001",
                    status=TaskStatus.COMPLETED,
                    result={"custom": "response", "processed_by": "custom_handler"},
                ).model_dump(),
                correlation_id=envelope.id,
                trace_id=envelope.trace_id,
            )

        # Create registry and register handler
        registry = HandlerRegistry()
        registry.register("task.request", custom_handler)

        # Verify registration
        assert registry.has_handler("task.request")
        assert "task.request" in registry.list_handlers()

    def test_echo_handler_via_registry(
        self, test_manifest: Manifest, sample_task_request_envelope: Envelope
    ) -> None:
        """Test echo handler works correctly through registry."""
        registry = HandlerRegistry()
        registry.register("task.request", create_echo_handler())

        response = registry.dispatch(sample_task_request_envelope, test_manifest)

        assert response.payload_type == "task.response"
        task_response = TaskResponse(**response.payload)
        assert task_response.status == TaskStatus.COMPLETED
        assert "echoed" in (task_response.result or {})
