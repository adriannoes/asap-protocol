"""Integration tests for Lambda Lang content-type negotiation.

Tests the full negotiation flow between client and server including:
- Accept header negotiation
- Content-Type response headers
- Graceful fallback when Lambda is not requested
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.codecs.lambda_codec import LAMBDA_CONTENT_TYPE, decode
from asap.transport.jsonrpc import JsonRpcRequest
from asap.transport.server import create_app

from ...transport.conftest import NoRateLimitTestBase


def _test_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:lambda-test",
        name="Lambda Test Agent",
        version="1.0.0",
        description="Test agent for Lambda negotiation",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://localhost:8000/asap"),
    )


def _make_jsonrpc_body() -> dict[str, Any]:
    envelope = Envelope(
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:lambda-test",
        payload_type="task.request",
        payload=TaskRequest(
            conversation_id="conv-123",
            skill_id="echo",
            input={"message": "hello"},
        ).model_dump(),
        asap_version="0.1",
    )
    rpc = JsonRpcRequest(
        method="asap.send",
        params={"envelope": envelope.model_dump(mode="json")},
        id="req-1",
    )
    return rpc.model_dump()


class TestLambdaNegotiationHappyPath(NoRateLimitTestBase):
    """Test Lambda content-type negotiation happy path."""

    def test_lambda_response_when_accept_header_present(self) -> None:
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": LAMBDA_CONTENT_TYPE},
        )
        assert response.status_code == 200
        assert LAMBDA_CONTENT_TYPE in response.headers["content-type"]
        decoded = decode(response.text)
        assert "result" in decoded
        assert "envelope" in decoded["result"]

    def test_lambda_response_with_quality_values(self) -> None:
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": f"{LAMBDA_CONTENT_TYPE}, application/json;q=0.9"},
        )
        assert response.status_code == 200
        assert LAMBDA_CONTENT_TYPE in response.headers["content-type"]

    def test_lambda_response_round_trip_fidelity(self) -> None:
        """Verify Lambda-encoded response has same structure as JSON response."""
        app = create_app(_test_manifest())
        client = TestClient(app)

        json_resp = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": "application/json"},
        )
        json_data = json_resp.json()

        lambda_resp = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": LAMBDA_CONTENT_TYPE},
        )
        lambda_data = decode(lambda_resp.text)

        assert "result" in json_data
        assert "result" in lambda_data
        assert "envelope" in json_data["result"]
        assert "envelope" in lambda_data["result"]


class TestLambdaNegotiationFallback(NoRateLimitTestBase):
    """Test graceful fallback when Lambda is not requested."""

    def test_json_response_when_no_accept_header(self) -> None:
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post("/asap", json=_make_jsonrpc_body())
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        response.json()

    def test_json_response_when_accept_json_only(self) -> None:
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": "application/json"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        assert LAMBDA_CONTENT_TYPE not in response.headers.get("content-type", "")

    def test_json_response_when_accept_wildcard(self) -> None:
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post(
            "/asap",
            json=_make_jsonrpc_body(),
            headers={"Accept": "*/*"},
        )
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")


class TestLambdaNegotiationMixed(NoRateLimitTestBase):
    """Test mixed scenarios."""

    def test_error_responses_always_json(self) -> None:
        """Error responses should be JSON even when Lambda is requested."""
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post(
            "/asap",
            json={"jsonrpc": "2.0", "method": "wrong.method", "params": {}, "id": "1"},
            headers={"Accept": LAMBDA_CONTENT_TYPE},
        )
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_existing_behavior_unchanged_without_lambda(self) -> None:
        """Verify no behavioral change for non-Lambda requests."""
        app = create_app(_test_manifest())
        client = TestClient(app)
        response = client.post("/asap", json=_make_jsonrpc_body())
        assert response.status_code == 200
        data = response.json()
        assert data.get("jsonrpc") == "2.0"
        assert "result" in data
