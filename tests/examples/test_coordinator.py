"""Tests for coordinator agent example."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.examples.coordinator import (
    DEFAULT_AGENT_ID,
    DEFAULT_AGENT_NAME,
    DEFAULT_AGENT_VERSION,
    DEFAULT_ASAP_ENDPOINT,
    DEFAULT_ECHO_AGENT_ID,
    build_manifest,
    build_task_envelope,
    build_task_request,
    create_coordinator_app,
)
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest


class TestBuildManifest:
    """Tests for build_manifest function."""

    def test_build_manifest_returns_valid_manifest(self) -> None:
        """Test that build_manifest returns a valid Manifest."""
        manifest = build_manifest()

        assert manifest.id == DEFAULT_AGENT_ID
        assert manifest.name == DEFAULT_AGENT_NAME
        assert manifest.version == DEFAULT_AGENT_VERSION
        assert manifest.endpoints.asap == DEFAULT_ASAP_ENDPOINT

    def test_build_manifest_with_custom_endpoint(self) -> None:
        """Test build_manifest with custom endpoint."""
        custom_endpoint = "http://custom.host:9000/asap"
        manifest = build_manifest(asap_endpoint=custom_endpoint)

        assert manifest.endpoints.asap == custom_endpoint

    def test_build_manifest_has_coordinate_skill(self) -> None:
        """Test that manifest includes coordinate skill."""
        manifest = build_manifest()

        skill_ids = [s.id for s in manifest.capabilities.skills]
        assert "coordinate" in skill_ids


class TestCreateCoordinatorApp:
    """Tests for create_coordinator_app function."""

    def test_create_coordinator_app_returns_fastapi_app(self) -> None:
        """Test that create_coordinator_app returns a FastAPI instance."""
        app = create_coordinator_app()

        assert isinstance(app, FastAPI)

    def test_create_coordinator_app_has_manifest_endpoint(self) -> None:
        """Test that app has manifest endpoint."""
        app = create_coordinator_app()
        client = TestClient(app)

        response = client.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == DEFAULT_AGENT_ID
        assert data["name"] == DEFAULT_AGENT_NAME


class TestBuildTaskRequest:
    """Tests for build_task_request function."""

    def test_build_task_request_returns_task_request(self) -> None:
        """Test that build_task_request returns a TaskRequest."""
        payload = {"message": "test"}
        request = build_task_request(payload)

        assert isinstance(request, TaskRequest)
        assert request.skill_id == "echo"
        assert request.input == payload

    def test_build_task_request_generates_conversation_id(self) -> None:
        """Test that build_task_request generates a conversation_id."""
        request = build_task_request({"data": "value"})

        assert request.conversation_id is not None
        assert len(request.conversation_id) > 0


class TestBuildTaskEnvelope:
    """Tests for build_task_envelope function."""

    def test_build_task_envelope_returns_envelope(self) -> None:
        """Test that build_task_envelope returns an Envelope."""
        payload = {"key": "value"}
        envelope = build_task_envelope(payload)

        assert isinstance(envelope, Envelope)
        assert envelope.payload_type == "task.request"

    def test_build_task_envelope_has_correct_sender_recipient(self) -> None:
        """Test that envelope has correct sender and recipient."""
        envelope = build_task_envelope({"test": True})

        assert envelope.sender == DEFAULT_AGENT_ID
        assert envelope.recipient == DEFAULT_ECHO_AGENT_ID

    def test_build_task_envelope_generates_trace_id(self) -> None:
        """Test that envelope generates a trace_id."""
        envelope = build_task_envelope({})

        assert envelope.trace_id is not None
        assert len(envelope.trace_id) > 0

    def test_build_task_envelope_payload_contains_input(self) -> None:
        """Test that envelope payload contains the input."""
        input_data = {"message": "Hello", "count": 42}
        envelope = build_task_envelope(input_data)

        assert envelope.payload["input"] == input_data
