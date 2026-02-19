"""Envelope model for ASAP protocol messages.

The Envelope wraps all ASAP protocol messages, providing metadata for
routing, correlation, tracing, and versioning.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

from pydantic import Field, field_validator, model_validator

from asap.models.base import ASAPBaseModel
from asap.models.ids import generate_id
from asap.models.payloads import PAYLOAD_TYPE_REGISTRY, PayloadType
from asap.models.types import AgentURN
from asap.models.validators import validate_agent_urn


def _normalize_payload_type(pt: str) -> str:
    """Lowercase alphanumeric key for payload_type lookup (e.g. task.request -> taskrequest)."""
    return "".join(c for c in pt.lower() if c.isalnum())


def _parse_payload(payload_type: str, payload: dict[str, Any]) -> PayloadType | dict[str, Any]:
    key = _normalize_payload_type(payload_type)
    payload_class = PAYLOAD_TYPE_REGISTRY.get(key)
    if payload_class is None:
        return payload
    return cast(PayloadType, payload_class.model_validate(payload))


class Envelope(ASAPBaseModel):
    """ASAP protocol message envelope.

    Envelope wraps all protocol messages with metadata for routing,
    correlation, tracing, and versioning. Auto-generates id and timestamp
    if not provided.

    Attributes:
        id: Unique envelope identifier (auto-generated if not provided)
        asap_version: ASAP protocol version (e.g., "0.1")
        timestamp: Message timestamp in UTC (auto-generated if not provided)
        sender: Sender agent URN
        recipient: Recipient agent URN
        payload_type: Type of payload (TaskRequest, TaskResponse, etc.)
        payload: Actual message payload
        correlation_id: Optional ID for correlating request/response pairs
        trace_id: Optional ID for distributed tracing
        extensions: Optional custom extensions

    Example:
        >>> from datetime import datetime, timezone
        >>> envelope = Envelope(
        ...     asap_version="0.1",
        ...     sender="urn:asap:agent:coordinator",
        ...     recipient="urn:asap:agent:research-v1",
        ...     payload_type="TaskRequest",
        ...     payload={"conversation_id": "conv_123", "skill_id": "research", "input": {}}
        ... )
        >>> # id and timestamp are auto-generated
        >>> assert envelope.id is not None
        >>> assert envelope.timestamp is not None
    """

    id: str | None = Field(
        default=None, description="Unique envelope identifier (ULID, auto-generated)"
    )
    asap_version: str = Field(..., description="ASAP protocol version")
    timestamp: datetime | None = Field(
        default=None, description="Message timestamp (UTC, auto-generated)"
    )
    sender: AgentURN = Field(..., description="Sender agent URN")
    recipient: AgentURN = Field(..., description="Recipient agent URN")
    payload_type: str = Field(..., description="Payload type discriminator")
    payload: PayloadType | dict[str, Any] = Field(
        ..., description="Message payload (typed when payload_type known, else dict)"
    )
    correlation_id: str | None = Field(
        default=None, description="Optional correlation ID for request/response pairing"
    )
    trace_id: str | None = Field(
        default=None, description="Optional trace ID for distributed tracing"
    )
    requires_ack: bool = Field(
        default=False,
        description=(
            "When True, receiver must send a MessageAck for this envelope (WebSocket). "
            "Over WebSocket, auto-set for state-changing payloads: TaskRequest, "
            "TaskCancel, StateRestore, MessageSend. HTTP transport uses response as implicit ack."
        ),
    )
    extensions: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional custom extensions. "
            "Can include a 'nonce' field (string) for replay attack prevention. "
            "If provided, the nonce must be unique within the TTL window (typically 10 minutes). "
            "Duplicate nonces will be rejected by the validation layer."
        ),
    )

    @field_validator("id", mode="before")
    @classmethod
    def generate_id_if_missing(cls, v: str | None) -> str:
        """Auto-generate ID if not provided."""
        if v is None:
            return generate_id()
        return v

    @field_validator("timestamp", mode="before")
    @classmethod
    def generate_timestamp_if_missing(cls, v: datetime | None) -> datetime:
        """Auto-generate timestamp if not provided."""
        if v is None:
            return datetime.now(timezone.utc)
        return v

    @field_validator("sender", "recipient")
    @classmethod
    def validate_sender_recipient_urn(cls, v: str) -> str:
        """Validate sender/recipient URN format and length."""
        return validate_agent_urn(v)

    @model_validator(mode="before")
    @classmethod
    def parse_payload_from_dict(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = data.get("payload")
        payload_type = data.get("payload_type")
        if isinstance(payload, dict) and payload_type:
            data = dict(data)
            data["payload"] = _parse_payload(payload_type, payload)
        return data

    @model_validator(mode="after")
    def validate_response_correlation(self) -> "Envelope":
        response_type_keys = {"taskresponse", "mcptoolresult", "mcpresourcedata"}

        if (
            _normalize_payload_type(self.payload_type) in response_type_keys
            and not self.correlation_id
        ):
            raise ValueError(f"{self.payload_type} must have correlation_id for request tracking")
        return self

    @property
    def payload_dict(self) -> dict[str, Any]:
        if isinstance(self.payload, ASAPBaseModel):
            return self.payload.model_dump()
        return self.payload
