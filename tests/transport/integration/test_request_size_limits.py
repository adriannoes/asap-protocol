"""Tests for request size validation in /asap endpoint.

These tests validate that the server correctly enforces maximum request size limits
and rejects requests that exceed the configured limit with HTTP 413 (Payload Too Large).

Rate limiting is automatically disabled for these tests via NoRateLimitTestBase
to prevent interference from rate limiting tests.
"""

import json
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.server import create_app

if TYPE_CHECKING:
    pass


from ..conftest import NoRateLimitTestBase


class TestPayloadSizeValidation(NoRateLimitTestBase):
    """Tests for payload size validation in /asap endpoint."""

    @pytest.fixture
    def manifest(self) -> Manifest:
        """Create a sample manifest for testing."""
        return Manifest(
            id="urn:asap:agent:test-size",
            name="Test Size Server",
            version="1.0.0",
            description="Test server for size validation",
            capabilities=Capability(
                asap_version="0.1",
                skills=[Skill(id="echo", description="Echo skill")],
                state_persistence=False,
            ),
            endpoints=Endpoint(asap="http://localhost:8000/asap"),
        )

    @pytest.fixture
    def app_default_size(self, manifest: Manifest) -> FastAPI:
        """Create app with default 10MB size limit.

        Rate limiting is automatically disabled via NoRateLimitTestBase.
        """
        return create_app(manifest)  # type: ignore[no-any-return]

    @pytest.fixture
    def app_custom_size(self, manifest: Manifest) -> FastAPI:
        """Create app with custom 1MB size limit for testing.

        Rate limiting is automatically disabled via NoRateLimitTestBase.
        """
        return create_app(manifest, max_request_size=1 * 1024 * 1024)  # type: ignore[no-any-return]

    def test_request_under_limit_accepted(self, app_default_size: FastAPI) -> None:
        """Test that requests under 10MB are accepted."""
        client = TestClient(app_default_size)

        # Create a small envelope (well under 10MB)
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-size",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="size-test-1",
        )

        response = client.post("/asap", json=rpc_request.model_dump())

        # Should succeed (200) or return JSON-RPC error if handler not found
        # But should NOT return 413 (Payload Too Large)
        assert response.status_code != 413
        assert response.status_code in [200, 404]

    def test_request_over_limit_rejected(self, app_custom_size: FastAPI) -> None:
        """Test that requests over the limit are rejected with 413."""
        client = TestClient(app_custom_size)

        # Create a payload that exceeds 1MB when serialized
        # Use a smaller multiplier to ensure we exceed 1MB but don't create
        # an unreasonably large object
        large_payload = {"data": "x" * (1024 * 1024)}  # 1MB of data in payload

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-size",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input=large_payload,
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="size-test-2",
        )

        # Serialize to JSON and check size
        request_json = json.dumps(rpc_request.model_dump())
        request_bytes = request_json.encode("utf-8")

        # Verify the request exceeds the limit
        assert len(request_bytes) > 1 * 1024 * 1024, "Request should exceed 1MB limit"

        # Send it with Content-Length header
        response = client.post(
            "/asap",
            content=request_bytes,
            headers={"Content-Type": "application/json", "Content-Length": str(len(request_bytes))},
        )

        # Should return 413 Payload Too Large
        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"].lower()

    def test_content_length_validation(self, app_custom_size: FastAPI) -> None:
        """Test that Content-Length header validation works."""
        client = TestClient(app_custom_size)

        # Create a small request but send it with a Content-Length header
        # that exceeds the limit
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-size",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="size-test-3",
        )

        request_json = json.dumps(rpc_request.model_dump())
        request_bytes = request_json.encode("utf-8")

        # Verify the actual request is small
        assert len(request_bytes) < 1 * 1024 * 1024, "Actual request should be under limit"

        # Send with Content-Length header that exceeds limit
        fake_large_size = 2 * 1024 * 1024  # 2MB
        response = client.post(
            "/asap",
            content=request_bytes,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(fake_large_size),
            },
        )

        # Should return 413 based on Content-Length header
        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"].lower()

    def test_actual_body_size_validation(self, app_custom_size: FastAPI) -> None:
        """Test that actual body size validation works when Content-Length is missing."""
        client = TestClient(app_custom_size)

        # Create a large payload that exceeds 1MB when serialized
        large_payload = {"data": "x" * (1024 * 1024)}  # 1MB of data

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-size",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-1",
                skill_id="echo",
                input=large_payload,
            ).model_dump(),
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="size-test-4",
        )

        request_json = json.dumps(rpc_request.model_dump())
        request_bytes = request_json.encode("utf-8")

        # Verify the request exceeds the limit
        assert len(request_bytes) > 1 * 1024 * 1024, "Request should exceed 1MB limit"

        # Send without Content-Length header (or with incorrect one)
        # The server should check actual body size
        response = client.post(
            "/asap",
            content=request_bytes,
            headers={"Content-Type": "application/json"},
            # Don't set Content-Length, let FastAPI read the body
        )

        # Should return 413 based on actual body size
        assert response.status_code == 413
        assert "exceeds maximum" in response.json()["detail"].lower()
