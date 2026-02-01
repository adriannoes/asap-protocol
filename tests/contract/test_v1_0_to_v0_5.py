"""Contract tests for v1.0.0 client communicating with v0.5.0 server.

These tests verify that a client using v1.0.0 protocol can successfully
communicate with a server running v0.5.0, ensuring forward compatibility
for gradual migration and rollback scenarios.

Migration scenarios:
1. Gradual upgrade: Clients updated to v1.0.0 while servers remain on v0.5.0
2. Rollback: Server needs to downgrade from v1.0.0 to v0.5.0
3. Heterogeneous environment: Mix of v1.0.0 and v0.5.0 components

Test scenarios:
1. v1.0.0 client basic requests → v0.5.0 server accepts
2. v1.0.0 new optional fields → v0.5.0 server ignores gracefully
3. v1.0.0 security features → v0.5.0 server processes correctly
4. v1.0.0 client receives v0.5.0 responses correctly
5. Graceful degradation for unsupported v1.0.0 features
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

import pytest
from starlette.testclient import TestClient

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
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
V0_5_0_ASAP_VERSION = "0.5"
V1_0_0_ASAP_VERSION = "1.0"
JSONRPC_VERSION = "2.0"
ASAP_METHOD = "asap.send"


class V100Client:
    """Simulated v1.0.0 client that creates messages with new features.

    This class mimics how a v1.0.0 client would construct messages,
    including new optional fields and enhanced features that may not
    be supported by older servers.
    """

    def __init__(self, agent_urn: str) -> None:
        """Initialize the v1.0.0 client.

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
        return f"v100-req-{self._request_counter}"

    def _generate_nonce(self) -> str:
        """Generate a unique nonce for replay attack prevention.

        Returns:
            Unique nonce string
        """
        return f"v100-nonce-{uuid.uuid4().hex}"

    def create_task_request(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
        config: dict[str, Any] | None = None,
        include_nonce: bool = False,
        nonce: str | None = None,
        trace_id: str | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a TaskRequest in JSON-RPC format (v1.0.0 style).

        v1.0.0 format characteristics:
        - asap_version: "1.0"
        - Full extensions support including nonce
        - Optional trace_id for distributed tracing
        - Enhanced metrics and observability fields

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill
            config: Optional configuration
            include_nonce: Whether to include a nonce for replay protection
            nonce: Explicit nonce value (generated if include_nonce=True and nonce=None)
            trace_id: Optional trace ID for distributed tracing
            extensions: Additional extensions to include

        Returns:
            Dictionary representing JSON-RPC wrapped v1.0.0 envelope
        """
        envelope: dict[str, Any] = {
            "asap_version": V1_0_0_ASAP_VERSION,
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

        if trace_id:
            envelope["trace_id"] = trace_id

        # Build extensions with optional nonce
        ext: dict[str, Any] = {}
        if include_nonce:
            ext["nonce"] = nonce if nonce else self._generate_nonce()
        if extensions:
            ext.update(extensions)
        if ext:
            envelope["extensions"] = ext

        return {
            "jsonrpc": JSONRPC_VERSION,
            "method": ASAP_METHOD,
            "params": {"envelope": envelope},
            "id": self._next_request_id(),
        }

    def create_task_request_with_v100_features(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a TaskRequest using v1.0.0-specific features.

        This simulates a v1.0.0 client using new features that may
        not be fully supported by v0.5.0 servers.

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill

        Returns:
            Dictionary representing JSON-RPC wrapped v1.0.0 envelope with new features
        """
        return self.create_task_request(
            recipient=recipient,
            conversation_id=conversation_id,
            skill_id=skill_id,
            input_data=input_data,
            include_nonce=True,
            trace_id=f"v100-trace-{uuid.uuid4().hex[:8]}",
            extensions={
                "nonce": self._generate_nonce(),
                "client_version": "1.0.0",
                "v100_feature": "enhanced_tracing",
                "request_metadata": {"priority": "high", "timeout_hint_ms": 30000},
            },
        )

    def create_task_cancel(
        self,
        recipient: str,
        task_id: str,
        reason: str | None = None,
        include_nonce: bool = True,
    ) -> dict[str, Any]:
        """Create a TaskCancel in JSON-RPC format (v1.0.0 style).

        Args:
            recipient: Target agent URN
            task_id: Task to cancel
            reason: Optional cancellation reason
            include_nonce: Whether to include a nonce

        Returns:
            Dictionary representing JSON-RPC wrapped v1.0.0 TaskCancel envelope
        """
        payload: dict[str, Any] = {"task_id": task_id}
        if reason:
            payload["reason"] = reason

        envelope: dict[str, Any] = {
            "asap_version": V1_0_0_ASAP_VERSION,
            "sender": self.agent_urn,
            "recipient": recipient,
            "payload_type": "task.cancel",
            "payload": payload,
        }

        if include_nonce:
            envelope["extensions"] = {"nonce": self._generate_nonce()}

        return {
            "jsonrpc": JSONRPC_VERSION,
            "method": ASAP_METHOD,
            "params": {"envelope": envelope},
            "id": self._next_request_id(),
        }

    def create_request_with_correlation_id(
        self,
        recipient: str,
        conversation_id: str,
        skill_id: str,
        input_data: dict[str, Any],
        envelope_id: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a TaskRequest with explicit IDs for correlation testing.

        Args:
            recipient: Target agent URN
            conversation_id: Conversation identifier
            skill_id: Skill to execute
            input_data: Input data for the skill
            envelope_id: Explicit envelope ID
            correlation_id: Optional correlation ID

        Returns:
            Dictionary representing JSON-RPC request with explicit IDs
        """
        request = self.create_task_request(
            recipient, conversation_id, skill_id, input_data, include_nonce=True
        )
        request["params"]["envelope"]["id"] = envelope_id
        if correlation_id:
            request["params"]["envelope"]["correlation_id"] = correlation_id
        return request


def create_v05_server() -> tuple[Manifest, HandlerRegistry, TestClient]:
    """Create a v0.5.0 server for testing.

    Simulates a production v0.5.0 server that a v1.0.0 client might connect to.

    Returns:
        Tuple of (manifest, registry, test_client)
    """
    manifest = Manifest(
        id="urn:asap:agent:v05-server",
        name="v0.5.0 Production Server",
        version="0.5.0",
        description="Simulated v0.5.0 production server",
        capabilities=Capability(
            asap_version=V0_5_0_ASAP_VERSION,
            skills=[
                Skill(id="echo", description="Echo skill"),
                Skill(id="process", description="Process data skill"),
            ],
            state_persistence=True,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8050/asap"),
    )

    registry = HandlerRegistry()

    async def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Handle task requests by echoing input as result (v0.5.0 style response)."""
        _ = manifest
        payload = envelope.payload
        task_id = f"task_{payload.get('conversation_id', 'unknown')}"

        response_payload = TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={
                "echo": payload.get("input", {}),
                "server_version": "0.5.0",
            },
            metrics={"duration_ms": 15},
        )

        # v0.5.0 server responds with v0.5.0 format
        return Envelope(
            asap_version=V0_5_0_ASAP_VERSION,
            sender=str(envelope.recipient),
            recipient=str(envelope.sender),
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
            # v0.5.0 preserves trace_id if provided
            trace_id=envelope.trace_id,
        )

    async def cancel_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Handle task cancellation requests (v0.5.0 style)."""
        _ = manifest
        payload = envelope.payload
        task_id = payload.get("task_id", "unknown")

        response_payload = TaskResponse(
            task_id=task_id,
            status=TaskStatus.CANCELLED,
            result={"cancelled": True, "reason": payload.get("reason")},
        )

        return Envelope(
            asap_version=V0_5_0_ASAP_VERSION,
            sender=str(envelope.recipient),
            recipient=str(envelope.sender),
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
        )

    registry.register("task.request", echo_handler)
    registry.register("task.cancel", cancel_handler)

    # Create v0.5.0 server with nonce validation (security feature from v0.5.0)
    app = create_app(manifest, registry, rate_limit="100000/minute", require_nonce=True)
    client = TestClient(app)

    return manifest, registry, client


def create_v05_server_with_auth() -> tuple[Manifest, HandlerRegistry, TestClient]:
    """Create a v0.5.0 server with authentication for testing.

    Returns:
        Tuple of (manifest, registry, test_client)
    """

    def token_validator(token: str) -> str | None:
        """Validate Bearer tokens and return agent ID."""
        valid_tokens = {
            "v100-client-token": "urn:asap:agent:v100-client",
            "production-token": "urn:asap:agent:production-client",
        }
        return valid_tokens.get(token)

    manifest = Manifest(
        id="urn:asap:agent:v05-auth-server",
        name="v0.5.0 Auth Server",
        version="0.5.0",
        description="v0.5.0 server with authentication",
        capabilities=Capability(
            asap_version=V0_5_0_ASAP_VERSION,
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8051/asap"),
        auth=AuthScheme(schemes=["bearer"]),
    )

    registry = HandlerRegistry()

    async def echo_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
        """Handle task requests with v0.5.0 response format."""
        _ = manifest
        payload = envelope.payload
        task_id = f"task_{payload.get('conversation_id', 'unknown')}"

        response_payload = TaskResponse(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={
                "echo": payload.get("input", {}),
                "authenticated": True,
                "server_version": "0.5.0",
            },
        )

        return Envelope(
            asap_version=V0_5_0_ASAP_VERSION,
            sender=str(envelope.recipient),
            recipient=str(envelope.sender),
            payload_type="task.response",
            payload=response_payload.model_dump(),
            correlation_id=envelope.id,
        )

    registry.register("task.request", echo_handler)

    app = create_app(
        manifest,
        registry,
        token_validator=token_validator,
        rate_limit="100000/minute",
    )
    client = TestClient(app)

    return manifest, registry, client


@pytest.fixture
def v05_server() -> Generator[TestClient, None, None]:
    """Fixture providing a v0.5.0 server.

    Yields:
        TestClient for the v0.5.0 server
    """
    _, _, client = create_v05_server()
    yield client


@pytest.fixture
def v05_server_with_auth() -> Generator[TestClient, None, None]:
    """Fixture providing a v0.5.0 server with authentication.

    Yields:
        TestClient for the v0.5.0 server
    """
    _, _, client = create_v05_server_with_auth()
    yield client


@pytest.fixture
def v100_client() -> V100Client:
    """Fixture providing a v1.0.0 client.

    Returns:
        V100Client instance
    """
    return V100Client("urn:asap:agent:v100-client")


class TestV100BasicRequestsToV05Server:
    """Tests for v1.0.0 basic requests to v0.5.0 server."""

    def test_basic_task_request_accepted(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that basic v1.0.0 TaskRequest is accepted by v0.5.0 server."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_v100_basic_001",
            skill_id="echo",
            input_data={"message": "hello from v1.0.0"},
            include_nonce=True,
        )

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        envelope = data["result"]["envelope"]
        assert envelope["payload"]["status"] == "completed"
        assert envelope["payload"]["result"]["echo"]["message"] == "hello from v1.0.0"
        # Server responds with v0.5.0 format
        assert envelope["asap_version"] == V0_5_0_ASAP_VERSION

    def test_v100_version_string_accepted(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that "1.0" version string is accepted by v0.5.0 server."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_version_test",
            skill_id="echo",
            input_data={"version_test": True},
            include_nonce=True,
        )

        # Verify envelope uses v1.0.0 version
        assert request["params"]["envelope"]["asap_version"] == "1.0"

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        assert "result" in response.json()

    def test_task_cancel_accepted(self, v05_server: TestClient, v100_client: V100Client) -> None:
        """Test that v1.0.0 TaskCancel is accepted by v0.5.0 server."""
        request = v100_client.create_task_cancel(
            recipient="urn:asap:agent:v05-server",
            task_id="task_v100_cancel_001",
            reason="User cancelled via v1.0.0 client",
        )

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["envelope"]["payload"]["status"] == "cancelled"


class TestV100NewFeaturesGracefulDegradation:
    """Tests for graceful degradation of v1.0.0 features on v0.5.0 server."""

    def test_new_extensions_ignored_gracefully(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v1.0.0-specific extensions are handled gracefully."""
        request = v100_client.create_task_request_with_v100_features(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_v100_features_001",
            skill_id="echo",
            input_data={"test_new_features": True},
        )

        response = v05_server.post("/asap", json=request)

        # v0.5.0 server should accept request, ignoring unknown extensions
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["envelope"]["payload"]["status"] == "completed"

    def test_trace_id_preserved_by_v05(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that trace_id from v1.0.0 request is preserved by v0.5.0 server."""
        trace_id = "v100-trace-abc123"

        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_trace_test",
            skill_id="echo",
            input_data={"trace_test": True},
            include_nonce=True,
            trace_id=trace_id,
        )

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        envelope = data["result"]["envelope"]
        # v0.5.0 server should preserve trace_id
        assert envelope.get("trace_id") == trace_id

    def test_request_metadata_extension_ignored(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v1.0.0 request_metadata extension is ignored by v0.5.0."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_metadata_test",
            skill_id="echo",
            input_data={"test": True},
            include_nonce=True,
            extensions={
                "request_metadata": {
                    "priority": "critical",
                    "deadline_ms": 5000,
                    "retry_policy": {"max_retries": 3},
                },
            },
        )

        response = v05_server.post("/asap", json=request)

        # Server should process request normally, ignoring metadata
        assert response.status_code == 200
        assert "result" in response.json()


class TestV100SecurityToV05Server:
    """Tests for v1.0.0 security features with v0.5.0 server."""

    def test_nonce_validated_by_v05(self, v05_server: TestClient, v100_client: V100Client) -> None:
        """Test that v0.5.0 server validates nonce from v1.0.0 client."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_nonce_test",
            skill_id="echo",
            input_data={"nonce_test": True},
            include_nonce=True,
        )

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        assert "result" in response.json()

    def test_duplicate_nonce_rejected_by_v05(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v0.5.0 server rejects duplicate nonce from v1.0.0 client."""
        explicit_nonce = "v100-replay-test-nonce"

        # First request
        request1 = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_replay_001",
            skill_id="echo",
            input_data={"first": True},
            include_nonce=True,
            nonce=explicit_nonce,
        )

        response1 = v05_server.post("/asap", json=request1)
        assert response1.status_code == 200
        assert "result" in response1.json()

        # Second request with same nonce (replay attack)
        request2 = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_replay_002",
            skill_id="echo",
            input_data={"replay": True},
            include_nonce=True,
            nonce=explicit_nonce,
        )

        response2 = v05_server.post("/asap", json=request2)
        assert response2.status_code == 200
        data = response2.json()
        assert "error" in data
        assert "nonce" in data["error"]["data"]["error"].lower()

    def test_bearer_auth_works_with_v05(
        self, v05_server_with_auth: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v1.0.0 client can authenticate with v0.5.0 server."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-auth-server",
            conversation_id="conv_auth_test",
            skill_id="echo",
            input_data={"auth_test": True},
        )

        response = v05_server_with_auth.post(
            "/asap",
            json=request,
            headers={"Authorization": "Bearer v100-client-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert data["result"]["envelope"]["payload"]["result"]["authenticated"] is True


class TestV100ResponseCompatibility:
    """Tests for v1.0.0 client handling v0.5.0 responses."""

    def test_v05_response_parseable_by_v100(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v0.5.0 response can be parsed by v1.0.0 client."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_response_test",
            skill_id="echo",
            input_data={"check_response": True},
            include_nonce=True,
        )

        response = v05_server.post("/asap", json=request)
        data = response.json()

        # v1.0.0 client expects these JSON-RPC fields
        assert "jsonrpc" in data
        assert "result" in data
        assert "id" in data

        # v1.0.0 client expects these envelope fields
        envelope = data["result"]["envelope"]
        assert "asap_version" in envelope
        assert "sender" in envelope
        assert "recipient" in envelope
        assert "payload_type" in envelope
        assert "payload" in envelope

        # v1.0.0 client expects these payload fields
        payload = envelope["payload"]
        assert "task_id" in payload
        assert "status" in payload

    def test_v05_server_version_in_response(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that response indicates v0.5.0 server version."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_version_check",
            skill_id="echo",
            input_data={"version_check": True},
            include_nonce=True,
        )

        response = v05_server.post("/asap", json=request)
        data = response.json()

        envelope = data["result"]["envelope"]
        # Response envelope should have v0.5.0 version
        assert envelope["asap_version"] == V0_5_0_ASAP_VERSION
        # Result should indicate server version
        assert envelope["payload"]["result"]["server_version"] == "0.5.0"


class TestV100CorrelationWithV05:
    """Tests for correlation ID handling between v1.0.0 and v0.5.0."""

    def test_correlation_id_in_v05_response(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v0.5.0 response includes correlation_id."""
        request = v100_client.create_request_with_correlation_id(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_corr_test",
            skill_id="echo",
            input_data={"correlation_test": True},
            envelope_id="v100-envelope-corr-001",
        )

        response = v05_server.post("/asap", json=request)
        data = response.json()

        envelope = data["result"]["envelope"]
        # v0.5.0 server should set correlation_id to request envelope id
        assert envelope.get("correlation_id") == "v100-envelope-corr-001"

    def test_jsonrpc_id_preserved(self, v05_server: TestClient, v100_client: V100Client) -> None:
        """Test that JSON-RPC request id is preserved in v0.5.0 response."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_jsonrpc_id",
            skill_id="echo",
            input_data={"id_test": True},
            include_nonce=True,
        )

        request_id = request["id"]
        response = v05_server.post("/asap", json=request)
        data = response.json()

        assert data["id"] == request_id


class TestV100ManifestDiscoveryFromV05:
    """Tests for v1.0.0 client discovering v0.5.0 server manifest."""

    def test_manifest_discoverable(self, v05_server: TestClient) -> None:
        """Test that v1.0.0 client can discover v0.5.0 server manifest."""
        response = v05_server.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        data = response.json()

        # v1.0.0 client expects these fields
        assert "id" in data
        assert "name" in data
        assert "version" in data
        assert "capabilities" in data
        assert "endpoints" in data

    def test_manifest_shows_v05_capabilities(self, v05_server: TestClient) -> None:
        """Test that manifest shows v0.5.0 capabilities."""
        response = v05_server.get("/.well-known/asap/manifest.json")
        data = response.json()

        # v1.0.0 client can detect server is v0.5.0
        assert data["version"] == "0.5.0"
        capabilities = data["capabilities"]
        assert capabilities["asap_version"] == V0_5_0_ASAP_VERSION

    def test_skills_readable_by_v100(self, v05_server: TestClient) -> None:
        """Test that v0.5.0 skills are readable by v1.0.0 client."""
        response = v05_server.get("/.well-known/asap/manifest.json")
        data = response.json()

        skills = data["capabilities"]["skills"]
        assert len(skills) > 0
        for skill in skills:
            assert "id" in skill
            assert "description" in skill


class TestV100ErrorHandlingFromV05:
    """Tests for v1.0.0 client handling v0.5.0 errors."""

    def test_v05_error_format_readable(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v0.5.0 errors are in format v1.0.0 client expects."""
        # Send malformed JSON-RPC
        request = {
            "jsonrpc": "2.0",
            "params": {
                "envelope": {
                    "asap_version": "1.0",
                    "sender": v100_client.agent_urn,
                    "recipient": "urn:asap:agent:v05-server",
                    "payload_type": "task.request",
                    "payload": {},
                    "extensions": {"nonce": "error-test-nonce"},
                }
            },
            "id": "error-test-1",
        }

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()

        # v1.0.0 client expects JSON-RPC error format
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]

    def test_auth_error_format(
        self, v05_server_with_auth: TestClient, v100_client: V100Client
    ) -> None:
        """Test that v0.5.0 auth errors are in v1.0.0-readable format."""
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-auth-server",
            conversation_id="conv_auth_error",
            skill_id="echo",
            input_data={"test": True},
        )

        # Send without auth header
        response = v05_server_with_auth.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestMigrationScenarios:
    """Tests for gradual migration and rollback scenarios."""

    def test_gradual_upgrade_client_first(
        self, v05_server: TestClient, v100_client: V100Client
    ) -> None:
        """Simulate gradual upgrade where client is upgraded to v1.0.0 first.

        This is a common migration pattern where clients are upgraded
        before servers to minimize risk.
        """
        # v1.0.0 client sends request to v0.5.0 server
        request = v100_client.create_task_request(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_migration_001",
            skill_id="echo",
            input_data={"migration_step": "client_upgraded"},
            include_nonce=True,
        )

        response = v05_server.post("/asap", json=request)

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        # Verify communication works across versions
        assert data["result"]["envelope"]["payload"]["status"] == "completed"

    def test_rollback_scenario(self, v05_server: TestClient, v100_client: V100Client) -> None:
        """Simulate rollback where server is downgraded from v1.0.0 to v0.5.0.

        v1.0.0 clients should continue working with rolled-back server.
        """
        # v1.0.0 client using new features
        request = v100_client.create_task_request_with_v100_features(
            recipient="urn:asap:agent:v05-server",
            conversation_id="conv_rollback_001",
            skill_id="echo",
            input_data={"rollback_test": True},
        )

        response = v05_server.post("/asap", json=request)

        # Should work despite server being "older" version
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        # Server responds with its version
        assert data["result"]["envelope"]["asap_version"] == V0_5_0_ASAP_VERSION
