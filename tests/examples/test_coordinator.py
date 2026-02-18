"""Tests for coordinator agent example."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.examples.coordinator import (
    DEFAULT_AGENT_ID,
    DEFAULT_AGENT_NAME,
    DEFAULT_AGENT_VERSION,
    DEFAULT_ASAP_ENDPOINT,
    DEFAULT_ECHO_AGENT_ID,
    DEFAULT_ECHO_BASE_URL,
    build_manifest,
    build_task_envelope,
    build_task_request,
    create_coordinator_app,
    dispatch_task,
    main,
    parse_args,
)
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.testing import assert_envelope_valid


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

        assert_envelope_valid(envelope, allowed_payload_types=["task.request"])

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

        assert envelope.payload_dict["input"] == input_data


# Tests for dispatch_task, parse_args, and main functions


class TestParseArgs:
    """Tests for parse_args function."""

    def test_parse_args_defaults(self) -> None:
        """Test parse_args with no arguments uses defaults."""
        args = parse_args([])

        assert args.echo_url == DEFAULT_ECHO_BASE_URL
        assert args.message == "hello from coordinator"

    def test_parse_args_custom_echo_url(self) -> None:
        """Test parse_args with custom echo URL."""
        args = parse_args(["--echo-url", "http://custom:9000"])

        assert args.echo_url == "http://custom:9000"

    def test_parse_args_custom_message(self) -> None:
        """Test parse_args with custom message."""
        args = parse_args(["--message", "custom message"])

        assert args.message == "custom message"

    def test_parse_args_all_options(self) -> None:
        """Test parse_args with all options."""
        args = parse_args(["--echo-url", "http://test:8080", "--message", "test message"])

        assert args.echo_url == "http://test:8080"
        assert args.message == "test message"


class TestDispatchTask:
    """Tests for dispatch_task async function."""

    @pytest.mark.asyncio
    async def test_dispatch_task_sends_envelope(self) -> None:
        """Test that dispatch_task sends an envelope and returns response."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={"result": "echoed"},
            trace_id="test-trace-id",
            correlation_id="test-correlation-id",
        )

        mock_client = AsyncMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("asap.examples.coordinator.ASAPClient", return_value=mock_client):
            response = await dispatch_task(
                payload={"message": "test"}, echo_base_url="http://mock:8001"
            )

        assert response.payload_type == "task.result"
        assert response.payload_dict["result"] == "echoed"
        mock_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_dispatch_task_logs_request_and_response(self) -> None:
        """Test that dispatch_task logs request and response."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={"echoed": True},
            trace_id="trace-123",
            correlation_id="corr-456",
        )

        mock_client = AsyncMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("asap.examples.coordinator.ASAPClient", return_value=mock_client),
            patch("asap.examples.coordinator.logger") as mock_logger,
        ):
            await dispatch_task({"data": "value"})

        assert mock_logger.info.call_count >= 2

    @pytest.mark.asyncio
    async def test_dispatch_task_with_default_echo_url(self) -> None:
        """Test that dispatch_task uses default echo URL."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={},
            trace_id="trace-id",
        )

        mock_client = AsyncMock()
        mock_client.send = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "asap.examples.coordinator.ASAPClient", return_value=mock_client
        ) as mock_asap_client:
            await dispatch_task({"test": True})

        mock_asap_client.assert_called_once_with(DEFAULT_ECHO_BASE_URL)


class TestMain:
    """Tests for main function."""

    def test_main_runs_dispatch_task(self) -> None:
        """Test that main function dispatches a task."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={"result": "done"},
            trace_id="trace-id",
        )

        with patch("asap.examples.coordinator.asyncio.run") as mock_run:
            mock_run.return_value = mock_response
            with patch("asap.examples.coordinator.logger"):
                main(["--message", "test from main"])

        mock_run.assert_called_once()

    def test_main_with_custom_args(self) -> None:
        """Test main with custom command line arguments."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={"data": "custom"},
            trace_id="trace-id",
        )

        with patch("asap.examples.coordinator.asyncio.run") as mock_run:
            mock_run.return_value = mock_response
            with patch("asap.examples.coordinator.logger"):
                main(["--echo-url", "http://custom:9999", "--message", "custom msg"])

        mock_run.assert_called_once()

    def test_main_logs_completion(self) -> None:
        """Test that main logs completion message."""
        mock_response = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:echo-agent",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.result",
            payload={"done": True},
            trace_id="trace-id",
        )

        with (
            patch("asap.examples.coordinator.asyncio.run", return_value=mock_response),
            patch("asap.examples.coordinator.logger") as mock_logger,
        ):
            main([])

        mock_logger.info.assert_called()
        call_args = mock_logger.info.call_args_list[-1]
        assert "asap.coordinator.demo_complete" in str(call_args)
