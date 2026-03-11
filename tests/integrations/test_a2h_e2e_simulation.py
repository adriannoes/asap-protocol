"""E2E simulation: validate ASAP ↔ A2H integration against the A2H OpenAPI spec.

This test module simulates a realistic A2H gateway using httpx mocking,
exercising the full ASAP + A2H flow with payloads matching the official
A2H OpenAPI schema (a2h-protocol.yaml).

Flow under test:
    Agent → discover() → gateway capabilities
    Agent → inform() → fire-and-forget notification
    Agent → authorize() → poll → human APPROVE
    Agent → collect() → poll → structured data response
    Agent → cancel() → cancel pending interaction
    Provider → request_approval() → HITL bridge → ApprovalResult
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
import httpx
import pytest

from asap.handlers.hitl import ApprovalDecision, HumanApprovalProvider
from asap.integrations.a2h import (
    A2HApprovalProvider,
    A2HClient,
    Component,
    ComponentType,
    InteractionState,
)

GATEWAY_URL = "https://a2h-gateway.twilio.test"
NOW = datetime(2026, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
NOW_ISO = NOW.isoformat()


def _httpx_response(status_code: int, body: dict[str, Any]) -> httpx.Response:
    """Build a real httpx.Response matching what AsyncClient.request returns."""
    return httpx.Response(
        status_code=status_code,
        json=body,
        request=httpx.Request("GET", GATEWAY_URL),
    )


GATEWAY_CAPABILITIES = {
    "a2h_supported": ["1.0"],
    "channels": ["sms", "email", "push"],
    "factors": ["passkey.webauthn.v1", "otp.sms.v1"],
    "max_ttl_sec": 3600,
    "locales": ["en-US", "pt-BR"],
    "auth": {"methods": ["api_key", "oauth2"]},
    "replay_protection": {
        "idempotency_window_sec": 300,
        "timestamp_tolerance_sec": 60,
    },
}


class GatewaySimulator:
    """Simulate an A2H gateway responding to HTTP requests per the OpenAPI spec."""

    def __init__(self) -> None:
        self.interactions: dict[str, dict[str, Any]] = {}
        self.captured_requests: list[dict[str, Any]] = []
        self._call_count = 0

    async def handle(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Route a request to the appropriate simulated endpoint."""
        self._call_count += 1
        path = url.replace(GATEWAY_URL, "")
        self.captured_requests.append({"method": method, "path": path, "kwargs": kwargs})

        if path == "/.well-known/a2h" and method == "GET":
            return self._discover()
        if path == "/v1/intent" and method == "POST":
            return self._handle_intent(kwargs.get("json", {}))
        if path.startswith("/v1/status/") and method == "GET":
            interaction_id = path.split("/")[-1]
            return self._handle_status(interaction_id)
        if path.startswith("/v1/cancel/") and method == "POST":
            interaction_id = path.split("/")[-1]
            return self._handle_cancel(interaction_id)

        return _httpx_response(404, {"error": "ERR.INVALID_REQUEST", "message": "Not found"})

    def _discover(self) -> httpx.Response:
        return _httpx_response(200, GATEWAY_CAPABILITIES)

    def _handle_intent(self, payload: dict[str, Any]) -> httpx.Response:
        interaction_id = f"int-{len(self.interactions) + 1:04d}"
        intent_type = payload.get("type", "UNKNOWN")

        self.interactions[interaction_id] = {
            "payload": payload,
            "state": InteractionState.SENT,
            "poll_count": 0,
            "intent_type": intent_type,
        }

        return _httpx_response(
            200,
            {
                "interaction_id": interaction_id,
                "state": "SENT",
                "created_at": NOW_ISO,
                "ttl_sec": payload.get("ttl_sec", 300),
            },
        )

    def _handle_status(self, interaction_id: str) -> httpx.Response:
        if interaction_id not in self.interactions:
            return _httpx_response(404, {"error": "ERR.INVALID_REQUEST", "message": "Not found"})

        entry = self.interactions[interaction_id]
        entry["poll_count"] += 1
        intent_type = entry["intent_type"]

        if entry["poll_count"] == 1:
            entry["state"] = InteractionState.WAITING_INPUT
            return _httpx_response(
                200,
                {
                    "interaction_id": interaction_id,
                    "state": "WAITING_INPUT",
                    "created_at": NOW_ISO,
                    "updated_at": NOW_ISO,
                },
            )

        entry["state"] = InteractionState.ANSWERED
        response_body: dict[str, Any] = {
            "type": "RESPONSE",
            "responds_to": entry["payload"].get("message_id"),
            "interaction_id": interaction_id,
            "status": "ANSWERED",
            "decided_at": NOW_ISO,
        }

        if intent_type == "AUTHORIZE":
            response_body["decision"] = "APPROVE"
            response_body["evidence"] = {
                "factor": "otp.sms.v1",
                "proof": {"verified": True, "timestamp": NOW_ISO},
            }
        elif intent_type == "COLLECT":
            response_body["data"] = {
                "full_name": "Ada Lovelace",
                "department": "Engineering",
                "priority": "high",
            }

        return _httpx_response(
            200,
            {
                "interaction_id": interaction_id,
                "state": "ANSWERED",
                "created_at": NOW_ISO,
                "updated_at": NOW_ISO,
                "response": response_body,
            },
        )

    def _handle_cancel(self, interaction_id: str) -> httpx.Response:
        if interaction_id not in self.interactions:
            return _httpx_response(404, {"error": "ERR.INVALID_REQUEST", "message": "Not found"})

        entry = self.interactions[interaction_id]
        if entry["state"] in {InteractionState.ANSWERED, InteractionState.EXPIRED}:
            return _httpx_response(409, {"error": "ERR.CONFLICT", "message": "Already resolved"})

        entry["state"] = InteractionState.CANCELLED
        return _httpx_response(200, {"success": True, "message": "Cancelled"})


@pytest.fixture
def gateway() -> GatewaySimulator:
    return GatewaySimulator()


@pytest.fixture
def client(gateway: GatewaySimulator) -> A2HClient:
    """A2HClient wired to the gateway simulator via mocked httpx."""
    c = A2HClient(GATEWAY_URL, api_key="test-a2h-key", agent_id="urn:asap:agent:demo")

    async def patched_request(method: str, path: str, **kwargs: Any) -> httpx.Response:
        response = await gateway.handle(method, f"{GATEWAY_URL}{path}", **kwargs)
        response.raise_for_status()
        return response

    c._request = patched_request  # type: ignore[assignment]
    return c


class TestE2EDiscovery:
    """Validate gateway discovery against the A2H OpenAPI spec."""

    @pytest.mark.asyncio
    async def test_discover_returns_spec_compliant_capabilities(self, client: A2HClient) -> None:
        """Gateway capabilities match the GatewayCapabilities schema."""
        caps = await client.discover()

        assert caps.a2h_supported == ["1.0"]
        assert set(caps.channels) == {"sms", "email", "push"}
        assert caps.factors == ["passkey.webauthn.v1", "otp.sms.v1"]
        assert caps.max_ttl_sec == 3600
        assert caps.locales == ["en-US", "pt-BR"]


class TestE2EFireAndForget:
    """Validate INFORM and RESULT intents (no polling)."""

    @pytest.mark.asyncio
    async def test_inform_sends_spec_compliant_envelope(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """INFORM payload matches the A2HMessage schema."""
        interaction_id = await client.inform(
            "did:example:alice",
            "Your expense report has been approved.",
            conversation_id="conv-abc-123",
        )

        assert interaction_id == "int-0001"

        sent = gateway.captured_requests[-1]
        assert sent["path"] == "/v1/intent"
        payload = sent["kwargs"]["json"]

        assert payload["type"] == "INFORM"
        assert payload["agent_id"] == "urn:asap:agent:demo"
        assert payload["principal_id"] == "did:example:alice"
        assert payload["a2h_version"] == "1.0"
        assert payload["render"]["body"] == "Your expense report has been approved."
        assert payload["links"]["a2a_thread"] == "asap:conversation/conv-abc-123"
        assert "message_id" in payload
        assert "created_at" in payload

    @pytest.mark.asyncio
    async def test_send_result_includes_responds_to(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """RESULT intent includes responds_to for correlation."""
        await client.send_result(
            "did:example:alice",
            "Task completed successfully.",
            responds_to="msg-original-001",
        )

        payload = gateway.captured_requests[-1]["kwargs"]["json"]
        assert payload["type"] == "RESULT"
        assert payload["responds_to"] == "msg-original-001"


class TestE2EAuthorize:
    """Validate the full AUTHORIZE → poll → APPROVE flow."""

    @pytest.mark.asyncio
    async def test_authorize_full_flow_with_assurance(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """AUTHORIZE: send → SENT → WAITING_INPUT → ANSWERED(APPROVE) with evidence."""
        response = await client.authorize(
            "did:example:bob",
            "Authorize $5,000 wire transfer to vendor Acme Corp?",
            explanation="Quarterly invoice payment, PO-2026-0042",
            poll_interval=0.01,
            max_wait=5.0,
        )

        assert response.decision == "APPROVE"
        assert response.evidence is not None
        assert response.evidence["factor"] == "otp.sms.v1"
        assert response.decided_at is not None

        intent_payload = gateway.captured_requests[0]["kwargs"]["json"]
        assert intent_payload["type"] == "AUTHORIZE"
        assert intent_payload["explanation_bundle"]["why"] == (
            "Quarterly invoice payment, PO-2026-0042"
        )
        assert intent_payload["render"]["body"] == (
            "Authorize $5,000 wire transfer to vendor Acme Corp?"
        )

        assert gateway.interactions["int-0001"]["poll_count"] == 2

    @pytest.mark.asyncio
    async def test_authorize_api_key_in_headers(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """API key auth header is sent per A2H spec Section 1.8.7."""
        headers = client._headers()
        assert headers["X-A2H-API-Key"] == "test-a2h-key"
        assert headers["Content-Type"] == "application/json"


class TestE2ECollect:
    """Validate the COLLECT → poll → structured data flow."""

    @pytest.mark.asyncio
    async def test_collect_with_typed_components(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """COLLECT sends typed components and receives structured data back."""
        components = [
            Component(type=ComponentType.TEXT, name="full_name", label="Full Name", required=True),
            Component(
                type=ComponentType.SELECT,
                name="department",
                label="Department",
                options=[
                    {"value": "eng", "label": "Engineering"},
                    {"value": "sales", "label": "Sales"},
                ],
            ),
            Component(
                type=ComponentType.RADIO,
                name="priority",
                label="Priority",
                options=[
                    {"value": "low", "label": "Low"},
                    {"value": "high", "label": "High"},
                ],
            ),
        ]

        response = await client.collect(
            "did:example:carol",
            components,
            body="Please fill in your onboarding details:",
            poll_interval=0.01,
            max_wait=5.0,
        )

        assert response.data == {
            "full_name": "Ada Lovelace",
            "department": "Engineering",
            "priority": "high",
        }

        intent_payload = gateway.captured_requests[0]["kwargs"]["json"]
        assert intent_payload["type"] == "COLLECT"
        assert len(intent_payload["components"]) == 3
        assert intent_payload["components"][0]["type"] == "TEXT"
        assert intent_payload["components"][0]["required"] is True
        assert intent_payload["components"][1]["type"] == "SELECT"
        assert intent_payload["components"][1]["options"] is not None


class TestE2ECancel:
    """Validate cancel interaction flows."""

    @pytest.mark.asyncio
    async def test_cancel_pending_interaction(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """Cancel succeeds on a SENT (non-terminal) interaction."""
        interaction_id = await client.inform("did:example:alice", "Test notification")
        cancelled = await client.cancel(interaction_id)
        assert cancelled is True
        assert gateway.interactions[interaction_id]["state"] == InteractionState.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_unknown_interaction_returns_false(self, client: A2HClient) -> None:
        """Cancel returns False for non-existent interaction (404)."""
        cancelled = await client.cancel("int-nonexistent")
        assert cancelled is False


class TestE2EApprovalProvider:
    """Validate the HITL bridge: A2HApprovalProvider → HumanApprovalProvider."""

    @pytest.mark.asyncio
    async def test_full_approval_flow_via_provider(self, client: A2HClient) -> None:
        """Complete flow: provider.request_approval → A2HClient.authorize → ApprovalResult."""
        provider = A2HApprovalProvider(client)

        assert isinstance(provider, HumanApprovalProvider)

        result = await provider.request_approval(
            context="Deploy v2.2.0 to production?",
            principal_id="did:example:devops-lead",
            assurance_level="LOW",
            timeout_seconds=60.0,
        )

        assert result.decision == ApprovalDecision.APPROVE
        assert result.interaction_id is not None
        assert result.evidence is not None
        assert result.decided_at is not None

    @pytest.mark.asyncio
    async def test_notify_then_approve_combined_flow(self, client: A2HClient) -> None:
        """Realistic pattern: notify human first, then request approval (PRD US-1 + US-2)."""
        provider = A2HApprovalProvider(client)

        notify_id = await provider.notify(
            principal_id="did:example:alice",
            body="Agent is about to process sensitive data.",
        )
        assert notify_id == "int-0001"

        result = await provider.request_approval(
            context="Allow agent to access PII records for report generation?",
            principal_id="did:example:alice",
            assurance_level="HIGH",
            timeout_seconds=30.0,
        )
        assert result.decision == ApprovalDecision.APPROVE


class TestE2ECrossProtocolLink:
    """Validate ASAP ↔ A2H cross-protocol traceability (links.a2a_thread)."""

    @pytest.mark.asyncio
    async def test_a2a_thread_links_asap_conversation(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """A2H messages include a2a_thread linking back to the ASAP conversation."""
        await client.inform(
            "did:example:alice",
            "Task update",
            conversation_id="conv-asap-7890",
        )

        payload = gateway.captured_requests[-1]["kwargs"]["json"]
        assert payload["links"]["a2a_thread"] == "asap:conversation/conv-asap-7890"

    @pytest.mark.asyncio
    async def test_no_link_without_conversation_id(
        self, client: A2HClient, gateway: GatewaySimulator
    ) -> None:
        """Without conversation_id, links field is omitted from the envelope."""
        await client.inform("did:example:alice", "No ASAP context")

        payload = gateway.captured_requests[-1]["kwargs"]["json"]
        assert "links" not in payload
