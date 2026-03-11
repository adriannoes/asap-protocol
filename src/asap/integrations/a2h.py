"""A2H (Agent-to-Human) protocol integration for ASAP.

This module provides Pydantic models for the A2H protocol envelope, responses,
and discovery types. Models map to the A2H OpenAPI spec.

See: https://github.com/twilio-labs/Agent2Human
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

from asap.handlers.hitl import ApprovalDecision, ApprovalResult


class IntentType(StrEnum):
    """Intent types for A2H protocol messages."""

    INFORM = "INFORM"
    COLLECT = "COLLECT"
    AUTHORIZE = "AUTHORIZE"
    ESCALATE = "ESCALATE"
    RESULT = "RESULT"
    RESPONSE = "RESPONSE"
    ERROR = "ERROR"


class InteractionState(StrEnum):
    """State of an A2H interaction."""

    PENDING = "PENDING"
    SENT = "SENT"
    WAITING_INPUT = "WAITING_INPUT"
    ANSWERED = "ANSWERED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class AssuranceLevel(StrEnum):
    """Assurance level for human verification."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class ComponentType(StrEnum):
    """UI component types for A2H forms."""

    TEXT = "TEXT"
    SELECT = "SELECT"
    MULTISELECT = "MULTISELECT"
    CHECKBOX = "CHECKBOX"
    RADIO = "RADIO"
    TEXTAREA = "TEXTAREA"
    NUMBER = "NUMBER"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"


class ChannelFallback(BaseModel):
    """Fallback channel for message delivery."""

    model_config = ConfigDict(extra="forbid")

    type: str
    address: str


class ChannelBinding(BaseModel):
    """Primary channel and optional fallbacks for message delivery."""

    model_config = ConfigDict(extra="forbid")

    type: str
    address: str
    nonce: str | None = None
    expires_at: datetime | None = None
    render: RenderContent | None = None
    fallback: list[ChannelFallback] | None = None


class RenderContent(BaseModel):
    """Rendered content for display to the human."""

    model_config = ConfigDict(extra="forbid")

    body: str
    title: str | None = None
    footer: str | None = None
    icon: str | None = None


class AssuranceConfig(BaseModel):
    """Configuration for assurance/verification level."""

    model_config = ConfigDict(extra="forbid")

    level: AssuranceLevel = AssuranceLevel.LOW
    required_factors: list[str] | None = None


class Component(BaseModel):
    """Form component for collecting human input."""

    model_config = ConfigDict(extra="forbid")

    type: ComponentType
    name: str
    label: str | None = None
    required: bool = False
    options: list[dict[str, str]] | None = None
    validation: dict[str, Any] | None = None


class CallbackConfig(BaseModel):
    """Webhook callback configuration."""

    model_config = ConfigDict(extra="forbid")

    url: str
    secret: str


class A2HMessage(BaseModel):
    """A2H protocol message envelope."""

    model_config = ConfigDict(extra="forbid")

    type: IntentType
    message_id: str
    agent_id: str
    principal_id: str
    a2h_version: str = "1.0"
    a2h_min_version: str | None = None
    interaction_id: str | None = None
    responds_to: str | None = None
    channel: ChannelBinding | None = None
    render: RenderContent | None = None
    links: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    ttl_sec: int = 300
    assurance: AssuranceConfig | None = None
    explanation_bundle: dict[str, str] | None = None
    callback: CallbackConfig | None = None
    components: list[Component] | None = None
    created_at: datetime | None = None
    signature: str | None = None


class IntentResponse(BaseModel):
    """Response metadata for an A2H intent."""

    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    state: InteractionState
    created_at: datetime
    ttl_sec: int
    channel_id: str | None = None
    duplicate: bool | None = None


class A2HResponse(BaseModel):
    """Human response to an A2H intent."""

    model_config = ConfigDict(extra="forbid")

    type: IntentType = IntentType.RESPONSE
    responds_to: str | None = None
    interaction_id: str | None = None
    status: str | None = None
    decision: str | None = None
    decided_at: datetime | None = None
    data: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    signature: str | None = None


class InteractionStatus(BaseModel):
    """Status of an A2H interaction."""

    model_config = ConfigDict(extra="forbid")

    interaction_id: str
    state: InteractionState
    created_at: datetime
    updated_at: datetime
    response: A2HResponse | None = None
    error: dict[str, Any] | None = None


class GatewayCapabilities(BaseModel):
    """Gateway discovery capabilities (extra fields allowed for future spec extensions)."""

    model_config = ConfigDict(extra="allow")

    a2h_supported: list[str]
    channels: list[str]
    factors: list[str] | None = None
    max_ttl_sec: int | None = None
    locales: list[str] | None = None
    jwks_uri: str | None = None
    quiet_hours: dict[str, str] | None = None
    limits: dict[str, float] | None = None
    auth: dict[str, Any] | None = None
    replay_protection: dict[str, Any] | None = None
    webhooks: dict[str, Any] | None = None


TERMINAL_STATES = frozenset(
    {InteractionState.EXPIRED, InteractionState.CANCELLED, InteractionState.FAILED}
)


class A2HClient:
    """Async HTTP client for the A2H (Agent-to-Human) protocol."""

    def __init__(
        self,
        gateway_url: str,
        *,
        api_key: str | None = None,
        oauth_token: str | None = None,
        agent_id: str = "asap-agent",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self.oauth_token = oauth_token
        self.agent_id = agent_id
        self._external_client = http_client

    def _headers(self) -> dict[str, str]:
        """Build HTTP headers for gateway requests."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-A2H-API-Key"] = self.api_key
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send an HTTP request to the gateway and raise on non-2xx.

        Reuses the injected ``http_client`` when available (connection pooling
        for polling). Falls back to a per-request AsyncClient otherwise.
        """
        if self._external_client is not None:
            response = await self._external_client.request(
                method,
                f"{self.gateway_url}{path}",
                headers=self._headers(),
                **kwargs,
            )
            response.raise_for_status()
            return response
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{self.gateway_url}{path}",
                headers=self._headers(),
                **kwargs,
            )
            response.raise_for_status()
            return response

    def _build_message(
        self,
        intent_type: IntentType,
        principal_id: str,
        *,
        body: str | None = None,
        channel: ChannelBinding | None = None,
        components: list[Component] | None = None,
        assurance: AssuranceConfig | None = None,
        explanation: str | None = None,
        responds_to: str | None = None,
        params: dict[str, Any] | None = None,
        conversation_id: str | None = None,
    ) -> A2HMessage:
        """Construct an ``A2HMessage`` with auto-generated message_id and created_at."""
        render = RenderContent(body=body) if body else None
        explanation_bundle = {"why": explanation} if explanation else None
        links = {"a2a_thread": f"asap:conversation/{conversation_id}"} if conversation_id else None
        return A2HMessage(
            type=intent_type,
            message_id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            principal_id=principal_id,
            channel=channel,
            render=render,
            components=components,
            assurance=assurance,
            explanation_bundle=explanation_bundle,
            responds_to=responds_to,
            params=params,
            links=links,
            created_at=datetime.now(timezone.utc),
        )

    async def _send_intent(self, message: A2HMessage) -> IntentResponse:
        """POST /v1/intent and return the parsed IntentResponse."""
        resp = await self._request("POST", "/v1/intent", json=message.model_dump(exclude_none=True))
        return IntentResponse.model_validate(resp.json())

    async def _poll_until_resolved(
        self,
        interaction_id: str,
        *,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> A2HResponse:
        """Poll ``get_status()`` in a loop until the interaction resolves.

        Raises:
            ValueError: If the interaction reaches a terminal state
                (EXPIRED, CANCELLED, FAILED) or ANSWERED with no response payload.
            TimeoutError: If elapsed time exceeds *max_wait* seconds.
        """
        start = time.monotonic()
        while True:
            status = await self.get_status(interaction_id)
            if status.state == InteractionState.ANSWERED:
                if status.response is None:
                    raise ValueError(f"Interaction {interaction_id} answered but response is None")
                return status.response
            if status.state in TERMINAL_STATES:
                raise ValueError(f"Interaction {interaction_id} ended with state: {status.state}")
            if time.monotonic() - start > max_wait:
                raise TimeoutError(
                    f"Polling timed out after {max_wait}s for interaction {interaction_id}"
                )
            await asyncio.sleep(poll_interval)

    async def discover(self) -> GatewayCapabilities:
        """Fetch ``GET /.well-known/a2h`` and return parsed capabilities."""
        resp = await self._request("GET", "/.well-known/a2h")
        return GatewayCapabilities.model_validate(resp.json())

    async def inform(
        self,
        principal_id: str,
        body: str,
        *,
        channel: ChannelBinding | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Send a fire-and-forget INFORM intent; returns the interaction ID."""
        message = self._build_message(
            IntentType.INFORM,
            principal_id,
            body=body,
            channel=channel,
            conversation_id=conversation_id,
        )
        response = await self._send_intent(message)
        return response.interaction_id

    async def send_result(
        self,
        principal_id: str,
        body: str,
        *,
        responds_to: str | None = None,
        channel: ChannelBinding | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Send a fire-and-forget RESULT intent; returns the interaction ID."""
        message = self._build_message(
            IntentType.RESULT,
            principal_id,
            body=body,
            responds_to=responds_to,
            channel=channel,
            conversation_id=conversation_id,
        )
        response = await self._send_intent(message)
        return response.interaction_id

    async def get_status(self, interaction_id: str) -> InteractionStatus:
        """Poll ``GET /v1/status/{interaction_id}``."""
        resp = await self._request("GET", f"/v1/status/{interaction_id}")
        return InteractionStatus.model_validate(resp.json())

    async def cancel(self, interaction_id: str) -> bool:
        """Cancel a pending interaction.

        Returns:
            True if cancelled successfully, False if not found (404) or
            already resolved (409).
        """
        try:
            await self._request("POST", f"/v1/cancel/{interaction_id}")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (404, 409):
                return False
            raise
        return True

    async def authorize(
        self,
        principal_id: str,
        body: str,
        *,
        assurance: AssuranceConfig | None = None,
        channel: ChannelBinding | None = None,
        explanation: str | None = None,
        conversation_id: str | None = None,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> A2HResponse:
        """Send AUTHORIZE intent and poll until the human responds.

        Args:
            assurance: Verification level and required auth factors.
            explanation: Human-readable reason included in the A2H explanation_bundle.
            poll_interval: Seconds between status polls.
            max_wait: Maximum seconds to wait before raising TimeoutError.
        """
        message = self._build_message(
            IntentType.AUTHORIZE,
            principal_id,
            body=body,
            assurance=assurance,
            channel=channel,
            explanation=explanation,
            conversation_id=conversation_id,
        )
        intent = await self._send_intent(message)
        return await self._poll_until_resolved(
            intent.interaction_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
        )

    async def collect(
        self,
        principal_id: str,
        components: list[Component],
        *,
        body: str | None = None,
        channel: ChannelBinding | None = None,
        conversation_id: str | None = None,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> A2HResponse:
        """Send COLLECT intent with form components and poll until the human responds.

        Args:
            components: Typed form fields (TEXT, SELECT, etc.) presented to the human.
            poll_interval: Seconds between status polls.
            max_wait: Maximum seconds to wait before raising TimeoutError.
        """
        message = self._build_message(
            IntentType.COLLECT,
            principal_id,
            body=body,
            components=components,
            channel=channel,
            conversation_id=conversation_id,
        )
        intent = await self._send_intent(message)
        return await self._poll_until_resolved(
            intent.interaction_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
        )

    async def escalate(
        self,
        principal_id: str,
        targets: list[str],
        *,
        body: str | None = None,
        channel: ChannelBinding | None = None,
        conversation_id: str | None = None,
        poll_interval: float = 2.0,
        max_wait: float = 300.0,
    ) -> A2HResponse:
        """Send ESCALATE intent to target agents and poll until resolved.

        Args:
            targets: Escalation target identifiers (sent as ``params.targets``).
            poll_interval: Seconds between status polls.
            max_wait: Maximum seconds to wait before raising TimeoutError.
        """
        message = self._build_message(
            IntentType.ESCALATE,
            principal_id,
            body=body,
            params={"targets": targets},
            channel=channel,
            conversation_id=conversation_id,
        )
        intent = await self._send_intent(message)
        return await self._poll_until_resolved(
            intent.interaction_id,
            poll_interval=poll_interval,
            max_wait=max_wait,
        )


class A2HApprovalProvider:
    """HITL provider bridging HumanApprovalProvider to the A2H protocol.

    Delegates approval requests to an A2HClient, translating between
    the generic HITL interface and A2H-specific AUTHORIZE/INFORM intents.
    """

    def __init__(self, client: A2HClient) -> None:
        self._client = client

    async def request_approval(
        self,
        *,
        context: str,
        principal_id: str,
        assurance_level: str = "LOW",
        timeout_seconds: float = 300.0,
    ) -> ApprovalResult:
        """Delegate to A2HClient.authorize and map the response to ApprovalResult."""
        a2h_response = await self._client.authorize(
            principal_id=principal_id,
            body=context,
            assurance=AssuranceConfig(level=AssuranceLevel(assurance_level)),
            max_wait=timeout_seconds,
        )
        decision = (
            ApprovalDecision.APPROVE
            if a2h_response.decision == "APPROVE"
            else ApprovalDecision.DECLINE
        )
        return ApprovalResult(
            decision=decision,
            data=a2h_response.data,
            evidence=a2h_response.evidence,
            decided_at=a2h_response.decided_at,
            interaction_id=a2h_response.interaction_id,
        )

    async def notify(self, *, principal_id: str, body: str) -> str:
        """Send a fire-and-forget INFORM notification; returns the interaction ID."""
        return await self._client.inform(principal_id=principal_id, body=body)
