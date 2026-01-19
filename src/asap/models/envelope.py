"""Envelope model for ASAP protocol messages.

The Envelope wraps all ASAP protocol messages, providing metadata for
routing, correlation, tracing, and versioning.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import Field, field_validator

from asap.models.base import ASAPBaseModel
from asap.models.ids import generate_id


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
    sender: str = Field(..., description="Sender agent URN")
    recipient: str = Field(..., description="Recipient agent URN")
    payload_type: str = Field(..., description="Payload type discriminator")
    payload: dict[str, Any] = Field(..., description="Message payload")
    correlation_id: str | None = Field(
        default=None, description="Optional correlation ID for request/response pairing"
    )
    trace_id: str | None = Field(
        default=None, description="Optional trace ID for distributed tracing"
    )
    extensions: dict[str, Any] | None = Field(
        default=None, description="Optional custom extensions"
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
