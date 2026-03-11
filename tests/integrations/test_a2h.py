"""Tests for A2H protocol integration (models, client, provider)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from pydantic import ValidationError

from asap.handlers.hitl import ApprovalDecision, HumanApprovalProvider
from asap.integrations.a2h import (
    A2HApprovalProvider,
    A2HClient,
    A2HMessage,
    A2HResponse,
    AssuranceConfig,
    AssuranceLevel,
    CallbackConfig,
    ChannelBinding,
    ChannelFallback,
    Component,
    ComponentType,
    GatewayCapabilities,
    IntentResponse,
    InteractionStatus,
    RenderContent,
)

GATEWAY_URL = "https://gateway.test"
TIMESTAMP = "2026-01-01T00:00:00Z"


def _mock_response(status_code: int = 200, json_data: dict | None = None) -> MagicMock:
    """Create a mock ``httpx.Response``."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=resp,
        )
    return resp


def _make_client(**kwargs: str) -> A2HClient:
    """Build an ``A2HClient`` with sensible defaults."""
    return A2HClient(GATEWAY_URL, **kwargs)


# ---------------------------------------------------------------------------
# 4.2 — Client tests
# ---------------------------------------------------------------------------


class TestA2HClientDiscover:
    """Discovery endpoint tests."""

    @pytest.mark.asyncio
    async def test_discover_capabilities(self) -> None:
        """Discover returns parsed GatewayCapabilities."""
        client = _make_client()
        payload = {"a2h_supported": ["1.0"], "channels": ["sms", "email"]}
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(json_data=payload)
            caps = await client.discover()

        assert isinstance(caps, GatewayCapabilities)
        assert caps.a2h_supported == ["1.0"]
        assert caps.channels == ["sms", "email"]


class TestA2HClientIntents:
    """Fire-and-forget intent tests (INFORM, RESULT)."""

    @pytest.mark.asyncio
    async def test_inform_sends_correct_payload(self) -> None:
        """Inform posts an INFORM intent and returns the interaction ID."""
        client = _make_client()
        intent_data = {
            "interaction_id": "int-1",
            "state": "SENT",
            "created_at": TIMESTAMP,
            "ttl_sec": 300,
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(json_data=intent_data)
            result = await client.inform("user-1", "Hello")

        assert result == "int-1"
        call_kwargs = mock_req.call_args
        assert call_kwargs.args[0] == "POST"
        assert call_kwargs.args[1] == "/v1/intent"
        sent_json = call_kwargs.kwargs["json"]
        assert sent_json["type"] == "INFORM"
        assert sent_json["principal_id"] == "user-1"

    @pytest.mark.asyncio
    async def test_send_result_payload(self) -> None:
        """send_result posts a RESULT intent with responds_to set."""
        client = _make_client()
        intent_data = {
            "interaction_id": "int-2",
            "state": "SENT",
            "created_at": TIMESTAMP,
            "ttl_sec": 300,
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(json_data=intent_data)
            result = await client.send_result("user-1", "Done", responds_to="orig-msg")

        assert result == "int-2"
        sent_json = mock_req.call_args.kwargs["json"]
        assert sent_json["type"] == "RESULT"
        assert sent_json["responds_to"] == "orig-msg"


class TestA2HClientPolling:
    """Polling-based intent tests (authorize, collect, cancel)."""

    @pytest.mark.asyncio
    async def test_authorize_polls_until_answered(self) -> None:
        """Authorize polls status until ANSWERED and returns the response."""
        client = _make_client()
        responses = [
            _mock_response(
                json_data={
                    "interaction_id": "int-1",
                    "state": "SENT",
                    "created_at": TIMESTAMP,
                    "ttl_sec": 300,
                }
            ),
            _mock_response(
                json_data={
                    "interaction_id": "int-1",
                    "state": "WAITING_INPUT",
                    "created_at": TIMESTAMP,
                    "updated_at": "2026-01-01T00:00:01Z",
                }
            ),
            _mock_response(
                json_data={
                    "interaction_id": "int-1",
                    "state": "ANSWERED",
                    "created_at": TIMESTAMP,
                    "updated_at": "2026-01-01T00:00:02Z",
                    "response": {
                        "decision": "APPROVE",
                        "interaction_id": "int-1",
                    },
                }
            ),
        ]
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = responses
            result = await client.authorize(
                "user-1",
                "Approve deploy?",
                poll_interval=0.01,
                max_wait=5.0,
            )

        assert isinstance(result, A2HResponse)
        assert result.decision == "APPROVE"
        assert mock_req.call_count == 3

    @pytest.mark.asyncio
    async def test_authorize_timeout_raises(self) -> None:
        """Authorize raises TimeoutError when polling exceeds max_wait."""
        client = _make_client()
        intent_resp = _mock_response(
            json_data={
                "interaction_id": "int-1",
                "state": "SENT",
                "created_at": TIMESTAMP,
                "ttl_sec": 300,
            }
        )
        waiting_resp = _mock_response(
            json_data={
                "interaction_id": "int-1",
                "state": "WAITING_INPUT",
                "created_at": TIMESTAMP,
                "updated_at": TIMESTAMP,
            }
        )
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [intent_resp, *([waiting_resp] * 50)]
            with pytest.raises(TimeoutError, match="timed out"):
                await client.authorize(
                    "user-1",
                    "Approve?",
                    poll_interval=0.01,
                    max_wait=0.05,
                )

    @pytest.mark.asyncio
    async def test_authorize_expired_raises_value_error(self) -> None:
        """Authorize raises ValueError when interaction expires."""
        client = _make_client()
        intent_resp = _mock_response(
            json_data={
                "interaction_id": "int-1",
                "state": "SENT",
                "created_at": TIMESTAMP,
                "ttl_sec": 300,
            }
        )
        expired_resp = _mock_response(
            json_data={
                "interaction_id": "int-1",
                "state": "EXPIRED",
                "created_at": TIMESTAMP,
                "updated_at": TIMESTAMP,
            }
        )
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [intent_resp, expired_resp]
            with pytest.raises(ValueError, match="EXPIRED"):
                await client.authorize(
                    "user-1",
                    "Approve?",
                    poll_interval=0.01,
                    max_wait=5.0,
                )

    @pytest.mark.asyncio
    async def test_collect_returns_structured_data(self) -> None:
        """Collect returns A2HResponse with structured data."""
        client = _make_client()
        intent_resp = _mock_response(
            json_data={
                "interaction_id": "int-c",
                "state": "SENT",
                "created_at": TIMESTAMP,
                "ttl_sec": 300,
            }
        )
        answered_resp = _mock_response(
            json_data={
                "interaction_id": "int-c",
                "state": "ANSWERED",
                "created_at": TIMESTAMP,
                "updated_at": TIMESTAMP,
                "response": {
                    "interaction_id": "int-c",
                    "data": {"name": "Alice", "age": "30"},
                },
            }
        )
        components = [
            Component(type=ComponentType.TEXT, name="name"),
            Component(type=ComponentType.NUMBER, name="age"),
        ]
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [intent_resp, answered_resp]
            result = await client.collect(
                "user-1",
                components,
                poll_interval=0.01,
                max_wait=5.0,
            )

        assert isinstance(result, A2HResponse)
        assert result.data == {"name": "Alice", "age": "30"}

    @pytest.mark.asyncio
    async def test_cancel_interaction_success(self) -> None:
        """Cancel returns True on a successful 200 response."""
        client = _make_client()
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = _mock_response(status_code=200)
            assert await client.cancel("int-1") is True

    @pytest.mark.asyncio
    async def test_cancel_interaction_not_found(self) -> None:
        """Cancel returns False when the gateway responds 404."""
        client = _make_client()
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 404
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = httpx.HTTPStatusError(
                "not found", request=MagicMock(), response=mock_resp
            )
            assert await client.cancel("int-1") is False


class TestA2HClientHeaders:
    """Authentication header tests."""

    def test_api_key_auth_header(self) -> None:
        """API key client includes X-A2H-API-Key header."""
        client = _make_client(api_key="test-key")
        headers = client._headers()
        assert headers["X-A2H-API-Key"] == "test-key"

    def test_oauth_bearer_header(self) -> None:
        """OAuth client includes Authorization: Bearer header."""
        client = _make_client(oauth_token="tok")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer tok"

    def test_no_auth_headers(self) -> None:
        """Client without credentials only sends Content-Type."""
        client = _make_client()
        headers = client._headers()
        assert headers == {"Content-Type": "application/json"}


class TestA2HClientBuildMessage:
    """Message construction tests."""

    def test_a2a_thread_link_populated(self) -> None:
        """_build_message sets a2a_thread link when conversation_id is provided."""
        client = _make_client()
        msg = client._build_message("INFORM", "user-1", body="hi", conversation_id="conv-123")
        assert msg.links is not None
        assert msg.links["a2a_thread"] == "asap:conversation/conv-123"

    def test_a2a_thread_link_absent_without_conversation_id(self) -> None:
        """_build_message leaves links as None without conversation_id."""
        client = _make_client()
        msg = client._build_message("INFORM", "user-1", body="hi")
        assert msg.links is None


# ---------------------------------------------------------------------------
# Model validation tests
# ---------------------------------------------------------------------------


_FORBID_EXTRA_MODELS: list[tuple[str, type, dict]] = [
    (
        "ChannelFallback",
        ChannelFallback,
        {"type": "sms", "address": "+1", "bad": 1},
    ),
    (
        "ChannelBinding",
        ChannelBinding,
        {"type": "sms", "address": "+1", "bad": 1},
    ),
    ("RenderContent", RenderContent, {"body": "hi", "bad": 1}),
    ("AssuranceConfig", AssuranceConfig, {"level": "LOW", "bad": 1}),
    (
        "Component",
        Component,
        {"type": "TEXT", "name": "f", "bad": 1},
    ),
    (
        "CallbackConfig",
        CallbackConfig,
        {"url": "https://x", "secret": "s", "bad": 1},
    ),
    (
        "A2HMessage",
        A2HMessage,
        {
            "type": "INFORM",
            "message_id": "m",
            "agent_id": "a",
            "principal_id": "p",
            "bad": 1,
        },
    ),
    (
        "IntentResponse",
        IntentResponse,
        {
            "interaction_id": "i",
            "state": "SENT",
            "created_at": TIMESTAMP,
            "ttl_sec": 300,
            "bad": 1,
        },
    ),
    (
        "A2HResponse",
        A2HResponse,
        {"interaction_id": "i", "bad": 1},
    ),
    (
        "InteractionStatus",
        InteractionStatus,
        {
            "interaction_id": "i",
            "state": "SENT",
            "created_at": TIMESTAMP,
            "updated_at": TIMESTAMP,
            "bad": 1,
        },
    ),
]


class TestModelValidation:
    """Pydantic model extra-field rejection tests."""

    @pytest.mark.parametrize(
        ("label", "model_cls", "data"),
        _FORBID_EXTRA_MODELS,
        ids=[t[0] for t in _FORBID_EXTRA_MODELS],
    )
    def test_models_forbid_extra_fields(self, label: str, model_cls: type, data: dict) -> None:
        """Models with extra='forbid' reject unknown fields."""
        with pytest.raises(ValidationError):
            model_cls(**data)

    def test_gateway_capabilities_allows_extra(self) -> None:
        """GatewayCapabilities accepts unknown fields for spec extensibility."""
        caps = GatewayCapabilities(
            a2h_supported=["1.0"],
            channels=["sms"],
            future_field="hello",
        )
        assert caps.a2h_supported == ["1.0"]


# ---------------------------------------------------------------------------
# 4.3 — Provider tests
# ---------------------------------------------------------------------------


class TestA2HApprovalProvider:
    """A2HApprovalProvider protocol conformance and behavior tests."""

    def test_a2h_provider_satisfies_protocol(self) -> None:
        """A2HApprovalProvider is a valid HumanApprovalProvider."""
        mock_client = MagicMock(spec=A2HClient)
        provider = A2HApprovalProvider(mock_client)
        assert isinstance(provider, HumanApprovalProvider)

    @pytest.mark.asyncio
    async def test_a2h_provider_approve(self) -> None:
        """Provider maps APPROVE decision from A2HResponse to ApprovalDecision."""
        mock_client = AsyncMock(spec=A2HClient)
        mock_client.authorize.return_value = A2HResponse(decision="APPROVE", interaction_id="int-1")
        provider = A2HApprovalProvider(mock_client)

        result = await provider.request_approval(context="Deploy to prod?", principal_id="user-1")

        assert result.decision == ApprovalDecision.APPROVE
        assert result.interaction_id == "int-1"

    @pytest.mark.asyncio
    async def test_a2h_provider_decline(self) -> None:
        """Provider maps DECLINE decision correctly."""
        mock_client = AsyncMock(spec=A2HClient)
        mock_client.authorize.return_value = A2HResponse(decision="DECLINE", interaction_id="int-2")
        provider = A2HApprovalProvider(mock_client)

        result = await provider.request_approval(context="Delete DB?", principal_id="user-1")

        assert result.decision == ApprovalDecision.DECLINE

    @pytest.mark.asyncio
    async def test_a2h_provider_maps_assurance_level(self) -> None:
        """Provider forwards assurance_level as AssuranceConfig to authorize()."""
        mock_client = AsyncMock(spec=A2HClient)
        mock_client.authorize.return_value = A2HResponse(decision="APPROVE", interaction_id="int-3")
        provider = A2HApprovalProvider(mock_client)

        await provider.request_approval(
            context="High-risk op",
            principal_id="user-1",
            assurance_level="HIGH",
        )

        call_kwargs = mock_client.authorize.call_args.kwargs
        assert call_kwargs["assurance"] == AssuranceConfig(level=AssuranceLevel.HIGH)

    @pytest.mark.asyncio
    async def test_a2h_provider_timeout_propagates(self) -> None:
        """TimeoutError from authorize() propagates through the provider."""
        mock_client = AsyncMock(spec=A2HClient)
        mock_client.authorize.side_effect = TimeoutError("timed out")
        provider = A2HApprovalProvider(mock_client)

        with pytest.raises(TimeoutError, match="timed out"):
            await provider.request_approval(context="Approve?", principal_id="user-1")

    @pytest.mark.asyncio
    async def test_a2h_provider_notify(self) -> None:
        """Provider.notify delegates to client.inform and returns the ID."""
        mock_client = AsyncMock(spec=A2HClient)
        mock_client.inform.return_value = "int-1"
        provider = A2HApprovalProvider(mock_client)

        result = await provider.notify(principal_id="user-1", body="Done!")

        mock_client.inform.assert_called_once_with(principal_id="user-1", body="Done!")
        assert result == "int-1"
