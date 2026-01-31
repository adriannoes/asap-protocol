"""Tests for echo agent example."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.examples.echo_agent import (
    DEFAULT_AGENT_ID,
    DEFAULT_AGENT_NAME,
    DEFAULT_AGENT_VERSION,
    DEFAULT_ASAP_ENDPOINT,
    build_manifest,
    create_echo_app,
    parse_args,
)
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.testing import assert_envelope_valid, assert_task_completed
from asap.transport.jsonrpc import JsonRpcRequest


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

    def test_build_manifest_has_echo_skill(self) -> None:
        """Test that manifest includes echo skill."""
        manifest = build_manifest()

        skill_ids = [s.id for s in manifest.capabilities.skills]
        assert "echo" in skill_ids


class TestCreateEchoApp:
    """Tests for create_echo_app function."""

    def test_create_echo_app_returns_fastapi_app(self) -> None:
        """Test that create_echo_app returns a FastAPI instance."""
        app = create_echo_app()

        assert isinstance(app, FastAPI)

    def test_create_echo_app_has_asap_endpoint(self) -> None:
        """Test that app has /asap endpoint."""
        app = create_echo_app()
        client = TestClient(app)

        # Should accept POST requests (though it will fail without proper payload)
        response = client.post("/asap", json={})
        # Invalid request, but endpoint exists
        assert response.status_code == 200  # JSON-RPC always returns 200

    def test_create_echo_app_has_manifest_endpoint(self) -> None:
        """Test that app has manifest endpoint."""
        app = create_echo_app()
        client = TestClient(app)

        response = client.get("/.well-known/asap/manifest.json")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == DEFAULT_AGENT_ID

    def test_echo_app_echoes_task_input(self) -> None:
        """Test that echo app correctly echoes task input."""
        app = create_echo_app()
        client = TestClient(app)

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:test",
            recipient=DEFAULT_AGENT_ID,
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv_test",
                skill_id="echo",
                input={"message": "Hello, Echo!"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-echo",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        result_envelope = Envelope.model_validate(data["result"]["envelope"])
        assert_envelope_valid(result_envelope, allowed_payload_types=["task.response"])
        assert_task_completed(result_envelope)
        assert result_envelope.payload["result"]["echoed"] == {"message": "Hello, Echo!"}


class TestParseArgs:
    """Tests for parse_args function."""

    def test_parse_args_default_values(self) -> None:
        """Test parse_args with no arguments returns defaults."""
        args = parse_args([])

        assert args.host == "127.0.0.1"
        assert args.port == 8001

    def test_parse_args_custom_host(self) -> None:
        """Test parse_args with custom host."""
        args = parse_args(["--host", "0.0.0.0"])

        assert args.host == "0.0.0.0"
        assert args.port == 8001

    def test_parse_args_custom_port(self) -> None:
        """Test parse_args with custom port."""
        args = parse_args(["--port", "9999"])

        assert args.host == "127.0.0.1"
        assert args.port == 9999

    def test_parse_args_custom_host_and_port(self) -> None:
        """Test parse_args with custom host and port."""
        args = parse_args(["--host", "localhost", "--port", "8888"])

        assert args.host == "localhost"
        assert args.port == 8888
