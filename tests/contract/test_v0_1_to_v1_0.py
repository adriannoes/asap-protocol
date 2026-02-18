"""Contract tests for v0.1.0 client communicating with v1.0.0 server.

These tests verify that a client using v0.1.0 protocol can successfully
communicate with a server running v1.0.0, ensuring backward compatibility.

Test scenarios:
1. Basic TaskRequest → TaskResponse flow
2. v0.1.0 envelope format accepted by v1.0.0 server
3. Missing optional fields (added in v1.0.0) handled gracefully
4. Error responses maintain backward compatibility
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from starlette.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.enums import TaskStatus
from asap.models.envelope import Envelope
from asap.models.payloads import TaskResponse
from asap.transport.handlers import HandlerRegistry
from asap.transport.server import create_app

if TYPE_CHECKING:
    from collections.abc import Generator


# Note: Rate limiting is automatically disabled for all tests in this package
# via the autouse fixture in conftest.py (following testing-standards.mdc)


# Constants for protocol version simulation
V0_1_0_ASAP_VERSION = "0.1"
V1_0_0_ASAP_VERSION = "1.0"
JSONRPC_VERSION = "2.0"
ASAP_METHOD = "asap.send"


class V010Client:
    """Simulated v0.1.0 client that creates messages in old format.

    This class mimics how a v0.1.0 client would construct messages,
    deliberately omitting fields that were added in later versions.
    The client wraps envelopes in JSON-RPC format as required by the protocol.
    """

    def __init__(self, agent_urn: str) -> None:
        """Initialize the v0.1.0 client.

        Args:
            agent_urn: The URN identifying this client agent
        """
        self.agent_urn = agent_urn
        self._request_counter = 0

    def _next_request_id(self) -> str:
        """Generate next request ID.

        Returns:
            Unique request identifier
        """
        self._request_counter += 1
        return f"v010-req-{self._request_counter}"

    def create_task_request(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a TaskRequest in JSON-RPC format (v0.1.0 style).

        v0.1.0 format characteristics:
        - asap_version: "0.1"
        - No extensions field
        - No trace_id field
        - Minimal required fields only
        - Wrapped in JSON-RPC 2.0 structure

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill
            config: Optional configuration

        Returns:
            Dictionary representing JSON-RPC wrapped v0.1.0 envelope
        """
        envelope: dict[str, Any] = {
            "asap_version": V0_1_0_ASAP_VERSION,
            "sender": self.agent_urn,
            "recipient": recipient,
            "payload_type": "task.request",
            "payload": {
                "conversation_id": conversation_id,
                "skill_id": skill_id,
                "input": input_data,
            },
        }

        if config:
            envelope["payload"]["config"] = config

        return {
            "jsonrpc": JSONRPC_VERSION,
            "method": ASAP_METHOD,
            "params": {"envelope": envelope},
            "id": self._next_request_id(),
        }

    def create_task_request_with_parent(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
        parent_task_id: str,
    ) -> dict[str, Any]:
        """Create a TaskRequest with parent_task_id (subtask scenario).

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill
            parent_task_id: Parent task identifier

        Returns:
            Dictionary representing JSON-RPC wrapped v0.1.0 envelope with parent task
        """
        request = self.create_task_request(recipient, conversation_id, skill_id, input_data)
        request["params"]["envelope"]["payload"]["parent_task_id"] = parent_task_id
        return request

    def create_task_cancel(
        self,
        recipient: str,
        task_id: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Create a TaskCancel in JSON-RPC format (v0.1.0 style).

        Args:
            recipient: Target agent URN
            task_id: Task to cancel
            reason: Optional cancellation reason

        Returns:
            Dictionary representing JSON-RPC wrapped v0.1.0 TaskCancel envelope
        """
        payload: dict[str, Any] = {"task_id": task_id}
        if reason:
            payload["reason"] = reason

        envelope = {
            "asap_version": V0_1_0_ASAP_VERSION,
            "sender": self.agent_urn,
            "recipient": recipient,
            "payload_type": "task.cancel",
            "payload": payload,
        }

        return {
            "jsonrpc": JSONRPC_VERSION,
            "method": ASAP_METHOD,
            "params": {"envelope": envelope},
            "id": self._next_request_id(),
        }

    def create_request_with_explicit_id(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
        envelope_id: str,
    ) -> dict[str, Any]:
        """Create a TaskRequest with explicit envelope ID for correlation testing.

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill
            envelope_id: Explicit envelope ID

        Returns:
            Dictionary representing JSON-RPC request with explicit envelope ID
        """
        request = self.create_task_request(recipient, conversation_id, skill_id, input_data)
        request["params"]["envelope"]["id"] = envelope_id
        return request


def create_v1_server() -> tuple[Manifest, HandlerRegistry, TestClient]:
    """Create a v1.0.0 server for testing.

    Returns:
        Tuple of (manifest, registry, test_client)
    """
    manifest = Manifest(
        id="urn:asap:agent:v1-server",
        name="v1.0.0 Test Server",
        version="1.0.0",
        description="Test server running v1.0.0 protocol",
        capabilities=Capability(
            asap_version=V1_0_0_ASAP_VERSION,
            skills=[
                Skill(id="echo", description="Echo skill"),
                Skill(id="process", description="Process data skill"),
            ],
            state_persistence=True,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8100/asap"),
    )

    registry = HandlerRegistry()

    # Register handler that returns TaskResponse
    async def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Handle task requests by echoing input as result."""
        _ = manifest  # Unused but required by handler signature
        payload = envelope.payload_dict
        task_id = f"task_{payload.get('conversation_id', 'unknown')}"

        response_payload = TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"echo": payload.get("input", {})},
            metrics={"duration_ms": 10},
        )

        return Envelope(
            asap_version=V1_0_0_ASAP_VERSION,
            sender=str(envelope.recipient),
            recipient=str(envelope.sender),
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
        )

    async def cancel_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Handle task cancellation requests."""
        _ = manifest  # Unused but required by handler signature
        payload = envelope.payload_dict
        task_id = payload.get("task_id", "unknown")

        response_payload = TaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            result={"cancelled": True, "reason": payload.get("reason")},
        )

        return Envelope(
            asap_version=V1_0_0_ASAP_VERSION,
            sender=str(envelope.recipient),
            recipient=str(envelope.sender),
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
        )

    registry.register("task.request", echo_handler)
    registry.register("task.cancel", cancel_handler)

    # Create app with high rate limit to avoid test interference
    app = create_app(manifest, registry, rate_limit="100000/minute")
    client = TestClient(app)

    return manifest, registry, client


@pytest.fixture
def v1_server() -> Generator[TestClient, None, None]:
    """Fixture providing a v1.0.0 test server.

    Yields:
        TestClient for the v1.0.0 server
    """
    _, _, client = create_v1_server()
    yield client


@pytest.fixture
def v010_client() -> V010Client:
    """Fixture providing a v0.1.0 client.

    Returns:
        V010Client instance
    """
    return V010Client("urn:asap:agent:v010-client")


class TestV010TaskRequestToV10Server:
    """Tests for v0.1.0 TaskRequest compatibility with v1.0.0 server."""

    def test_basic_task_request_flow(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test basic TaskRequest → TaskResponse flow.

        v0.1.0 client sends minimal TaskRequest, v1.0.0 server responds.
        """
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_v010_001",
            skill_id="echo",
            input_data={"message": "hello from v0.1.0"},
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()

        # Verify JSON-RPC response structure
        assert data["jsonrpc"] == "2.0"
        assert "result" in data
        assert "id" in data

        # Verify envelope in result (wrapped in "envelope" key)
        envelope = data["result"]["envelope"]
        assert envelope["payload_type"] == "task.response"
        assert envelope["payload"]["status"] == "completed"
        assert envelope["payload"]["result"]["echo"]["message"] == "hello from v0.1.0"

    def test_task_request_with_config(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test TaskRequest with optional config field.

        v0.1.0 clients may or may not include config field.
        """
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_v010_002",
            skill_id="process",
            input_data={"data": [1, 2, 3]},
            config={"timeout_seconds": 60},
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["envelope"]["payload"]["status"] == "completed"

    def test_task_request_without_optional_fields(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test TaskRequest without any optional envelope fields.

        v0.1.0 minimal envelope should work without:
        - id (auto-generated)
        - timestamp (auto-generated)
        - correlation_id
        - trace_id
        - extensions
        """
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_v010_003",
            skill_id="echo",
            input_data={"minimal": True},
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()

        # Server should return valid response
        envelope = data["result"]["envelope"]
        assert "id" in envelope  # Server auto-generates id
        assert envelope.get("correlation_id") is not None  # Links to request

    def test_task_request_with_parent_task(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test TaskRequest as subtask with parent_task_id.

        Subtask functionality should work across versions.
        """
        request = v010_client.create_task_request_with_parent(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_v010_004",
            skill_id="echo",
            input_data={"subtask_data": "processing"},
            parent_task_id="task_parent_001",
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["envelope"]["payload"]["status"] == "completed"


class TestV010EnvelopeFormatCompatibility:
    """Tests for v0.1.0 envelope format compatibility."""

    def test_v010_version_string_accepted(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test that "0.1" version string is accepted by v1.0.0 server."""
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_version_test",
            skill_id="echo",
            input_data={"version_test": True},
        )

        # Verify the envelope uses v0.1.0 version
        assert request["params"]["envelope"]["asap_version"] == "0.1"

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200

    def test_response_format_readable_by_v010(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test that v1.0.0 response can be parsed by v0.1.0 client.

        Response should contain only fields that v0.1.0 expects,
        or additional fields that v0.1.0 can safely ignore.
        """
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_response_test",
            skill_id="echo",
            input_data={"check_response": True},
        )

        response = v1_server.post("/asap", json=request)
        data = response.json()

        # v0.1.0 expected JSON-RPC fields
        assert "jsonrpc" in data
        assert "result" in data
        assert "id" in data

        # v0.1.0 expected envelope fields (wrapped in "envelope" key)
        envelope = data["result"]["envelope"]
        assert "asap_version" in envelope
        assert "sender" in envelope
        assert "recipient" in envelope
        assert "payload_type" in envelope
        assert "payload" in envelope

        # v0.1.0 expected payload fields for TaskResponse
        payload = envelope["payload"]
        assert "task_id" in payload
        assert "status" in payload

    def test_without_extensions_field(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test that v0.1.0 client can send requests without extensions.

        v0.1.0 didn't have extensions field, server should handle gracefully.
        """
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_no_extensions",
            skill_id="echo",
            input_data={"no_extensions": True},
        )

        # Ensure no extensions field (v0.1.0 behavior)
        assert "extensions" not in request["params"]["envelope"]

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200


class TestV010TaskCancelCompatibility:
    """Tests for v0.1.0 TaskCancel compatibility."""

    def test_basic_cancel_request(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test basic task cancellation from v0.1.0 client."""
        request = v010_client.create_task_cancel(
            recipient="urn:asap:agent:v1-server",
            task_id="task_to_cancel_001",
            reason="User requested cancellation",
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["envelope"]["payload"]["status"] == "cancelled"

    def test_cancel_without_reason(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test cancellation without optional reason field."""
        request = v010_client.create_task_cancel(
            recipient="urn:asap:agent:v1-server",
            task_id="task_to_cancel_002",
        )

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["envelope"]["payload"]["status"] == "cancelled"


class TestV010ErrorHandlingCompatibility:
    """Tests for error handling compatibility between versions."""

    def test_malformed_jsonrpc_returns_error(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test that malformed JSON-RPC returns proper error response.

        v0.1.0 clients should receive error responses for malformed requests.
        Note: Missing payload fields are handler-specific validation, not protocol-level.
        This test verifies protocol-level validation for invalid JSON-RPC structure.
        """
        # Send request with missing required JSON-RPC fields
        request = {
            "jsonrpc": "2.0",
            # Missing "method" field
            "params": {
                "envelope": {
                    "asap_version": "0.1",
                    "sender": v010_client.agent_urn,
                    "recipient": "urn:asap:agent:v1-server",
                    "payload_type": "task.request",
                    "payload": {},
                }
            },
            "id": "error-test-1",
        }

        response = v1_server.post("/asap", json=request)

        # JSON-RPC always returns 200, errors are in the body
        assert response.status_code == 200
        data = response.json()

        # Should have error field for JSON-RPC error
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_empty_task_request_payload_rejected_by_strict_validation(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Empty task.request payload is rejected (422) before handler."""
        request = {
            "jsonrpc": "2.0",
            "method": "asap.send",
            "params": {
                "envelope": {
                    "asap_version": "0.1",
                    "sender": v010_client.agent_urn,
                    "recipient": "urn:asap:agent:v1-server",
                    "payload_type": "task.request",
                    "payload": {},
                }
            },
            "id": "empty-payload-test",
        }

        response = v1_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32602
        assert "Invalid envelope" in data["error"]["data"]["error"]

    def test_unknown_skill_handled(self, v1_server: TestClient, v010_client: V010Client) -> None:
        """Test that unknown skill requests are handled gracefully."""
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_unknown_skill",
            skill_id="nonexistent_skill",
            input_data={"test": True},
        )

        response = v1_server.post("/asap", json=request)

        # Should succeed if handler doesn't validate skill
        # or return proper error
        assert response.status_code == 200
        data = response.json()
        # Either success or error is acceptable
        assert "result" in data or "error" in data


class TestV010ManifestDiscovery:
    """Tests for manifest discovery compatibility."""

    def test_manifest_endpoint_accessible(self, v1_server: TestClient) -> None:
        """Test that v0.1.0 client can discover v1.0.0 server manifest."""
        response = v1_server.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        data = response.json()

        # v0.1.0 expected manifest fields
        assert "id" in data
        assert "name" in data
        assert "version" in data
        assert "capabilities" in data
        assert "endpoints" in data

    def test_manifest_skills_readable(self, v1_server: TestClient) -> None:
        """Test that skills in manifest are readable by v0.1.0 client."""
        response = v1_server.get("/.well-known/asap/manifest.json")
        data = response.json()

        capabilities = data["capabilities"]
        assert "skills" in capabilities
        assert len(capabilities["skills"]) > 0

        # Each skill should have id and description
        for skill in capabilities["skills"]:
            assert "id" in skill
            assert "description" in skill


class TestV010CorrelationIdHandling:
    """Tests for correlation ID handling across versions."""

    def test_correlation_id_in_response(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test that responses include correlation_id linking to request.

        v0.1.0 clients may rely on correlation_id for request tracking.
        """
        request = v010_client.create_request_with_explicit_id(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_correlation_test",
            skill_id="echo",
            input_data={"track_me": True},
            envelope_id="req_v010_correlation_001",
        )

        response = v1_server.post("/asap", json=request)
        data = response.json()

        # Response correlation_id should match request envelope id
        envelope = data["result"]["envelope"]
        assert envelope.get("correlation_id") == "req_v010_correlation_001"

    def test_jsonrpc_id_preserved_in_response(
        self, v1_server: TestClient, v010_client: V010Client
    ) -> None:
        """Test that JSON-RPC request id is preserved in response."""
        request = v010_client.create_task_request(
            recipient="urn:asap:agent:v1-server",
            conversation_id="conv_jsonrpc_id_test",
            skill_id="echo",
            input_data={"test_jsonrpc_id": True},
        )

        # Get the request id for verification
        request_id = request["id"]

        response = v1_server.post("/asap", json=request)
        data = response.json()

        # JSON-RPC response id should match request id
        assert data["id"] == request_id
