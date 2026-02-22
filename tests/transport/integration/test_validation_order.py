"""Integration tests for validation order in server request processing.

This module tests that timestamp and nonce validations are applied in the
correct order and that both validations are consistently applied together.
"""

from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

if TYPE_CHECKING:
    pass

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.jsonrpc import (
    INVALID_PARAMS,
    JsonRpcErrorResponse,
    JsonRpcRequest,
)
from asap.transport.server import create_app

from ..conftest import NoRateLimitTestBase, TEST_RATE_LIMIT_DEFAULT


@pytest.fixture
def sample_manifest() -> Manifest:
    """Create a sample manifest for testing."""
    return Manifest(
        id="urn:asap:agent:test-server",
        name="Test Server",
        version="1.0.0",
        description="Test server for unit tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[
                Skill(
                    id="echo",
                    description="Echo input as output",
                )
            ],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


@pytest.fixture
def app_with_nonce_store(sample_manifest: Manifest) -> FastAPI:
    """Create FastAPI app with nonce store enabled for testing."""
    return create_app(
        sample_manifest,
        rate_limit=TEST_RATE_LIMIT_DEFAULT,
        require_nonce=True,
    )


@pytest.fixture
def client_with_nonce_store(app_with_nonce_store: FastAPI) -> TestClient:
    """Create test client with nonce store enabled."""
    return TestClient(app_with_nonce_store)


class TestValidationOrder(NoRateLimitTestBase):
    """Tests for validation order in request processing."""

    def test_invalid_timestamp_rejected_before_nonce_check(
        self, client_with_nonce_store: TestClient
    ) -> None:
        """Test that invalid timestamp is rejected before nonce validation.

        This ensures timestamp validation runs first, preventing unnecessary
        nonce store operations for invalid timestamps.
        """
        # Create envelope with old timestamp and valid nonce
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
            timestamp=old_timestamp,
            extensions={"nonce": "unique-nonce-123"},
        )

        rpc_request = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope.model_dump(mode="json")},
            id="test-req-1",
        )

        response = client_with_nonce_store.post("/asap", json=rpc_request.model_dump())

        assert response.status_code == 200
        response_data = response.json()
        assert "error" in response_data

        error_response = JsonRpcErrorResponse(**response_data)
        assert error_response.error.code == INVALID_PARAMS
        assert "timestamp" in error_response.error.data.get("error", "").lower()
        assert "nonce" not in error_response.error.data.get("error", "").lower()

    def test_valid_timestamp_with_invalid_nonce_rejected(
        self, client_with_nonce_store: TestClient
    ) -> None:
        """Test that valid timestamp with duplicate nonce is rejected.

        This ensures nonce validation runs after timestamp validation and
        properly rejects duplicate nonces.
        """
        # Create first envelope with valid timestamp and nonce
        envelope1 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "first request"},
            ).model_dump(),
            timestamp=datetime.now(timezone.utc),
            extensions={"nonce": "duplicate-nonce-456"},
        )

        rpc_request1 = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope1.model_dump(mode="json")},
            id="test-req-1",
        )

        # First request should succeed (or fail for other reasons, but not nonce)
        # We don't care if it succeeds or fails for other reasons,
        # just that nonce validation ran
        client_with_nonce_store.post("/asap", json=rpc_request1.model_dump())

        # Create second envelope with same nonce but valid timestamp
        envelope2 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "duplicate request"},
            ).model_dump(),
            timestamp=datetime.now(timezone.utc),
            extensions={"nonce": "duplicate-nonce-456"},
        )

        rpc_request2 = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope2.model_dump(mode="json")},
            id="test-req-2",
        )

        # Second request should fail with nonce error
        response2 = client_with_nonce_store.post("/asap", json=rpc_request2.model_dump())

        assert response2.status_code == 200
        response_data = response2.json()
        assert "error" in response_data

        error_response = JsonRpcErrorResponse(**response_data)
        assert error_response.error.code == INVALID_PARAMS
        assert "nonce" in error_response.error.data.get("error", "").lower()

    def test_both_validations_return_appropriate_error_codes(
        self, client_with_nonce_store: TestClient
    ) -> None:
        """Test that both validations return appropriate error codes.

        This ensures that timestamp and nonce errors are properly distinguished
        and return INVALID_PARAMS with appropriate error messages.
        """
        # Test timestamp error
        old_timestamp = datetime.now(timezone.utc) - timedelta(minutes=10)
        envelope_timestamp = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
            timestamp=old_timestamp,
        )

        rpc_request_timestamp = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope_timestamp.model_dump(mode="json")},
            id="test-req-timestamp",
        )

        response_timestamp = client_with_nonce_store.post(
            "/asap", json=rpc_request_timestamp.model_dump()
        )

        assert response_timestamp.status_code == 200
        response_data_timestamp = response_timestamp.json()
        assert "error" in response_data_timestamp

        error_response_timestamp = JsonRpcErrorResponse(**response_data_timestamp)
        assert error_response_timestamp.error.code == INVALID_PARAMS
        assert "timestamp" in error_response_timestamp.error.data.get("error", "").lower()

        # Test nonce error (duplicate)
        envelope_nonce1 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
            timestamp=datetime.now(timezone.utc),
            extensions={"nonce": "test-nonce-789"},
        )

        rpc_request_nonce1 = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope_nonce1.model_dump(mode="json")},
            id="test-req-nonce-1",
        )

        # First use - should pass timestamp validation
        client_with_nonce_store.post("/asap", json=rpc_request_nonce1.model_dump())

        # Second use - should fail nonce validation
        envelope_nonce2 = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:test-server",
            payload_type="task.request",
            payload=TaskRequest(
                conversation_id="conv-123",
                skill_id="echo",
                input={"message": "test"},
            ).model_dump(),
            timestamp=datetime.now(timezone.utc),
            extensions={"nonce": "test-nonce-789"},
        )

        rpc_request_nonce2 = JsonRpcRequest(
            method="asap.send",
            params={"envelope": envelope_nonce2.model_dump(mode="json")},
            id="test-req-nonce-2",
        )

        response_nonce = client_with_nonce_store.post("/asap", json=rpc_request_nonce2.model_dump())

        assert response_nonce.status_code == 200
        response_data_nonce = response_nonce.json()
        assert "error" in response_data_nonce

        error_response_nonce = JsonRpcErrorResponse(**response_data_nonce)
        assert error_response_nonce.error.code == INVALID_PARAMS
        assert "nonce" in error_response_nonce.error.data.get("error", "").lower()
