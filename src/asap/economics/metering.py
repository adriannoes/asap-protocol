"""Observability metering models for usage tracking (v1.3).

Defines metrics schema for tracking resource consumption per task:
tokens, duration, API calls. Integrates with MeteringStore from state layer.

Example:
    >>> from datetime import timezone
    >>> from asap.economics import UsageMetrics
    >>> record = UsageMetrics(
    ...     task_id="task_123",
    ...     agent_id="urn:asap:agent:provider",
    ...     consumer_id="urn:asap:agent:consumer",
    ...     tokens_in=1500,
    ...     tokens_out=2300,
    ...     duration_ms=4500,
    ...     api_calls=3,
    ...     timestamp=datetime.now(timezone.utc),
    ... )
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import Field

from asap.models.base import ASAPBaseModel

if TYPE_CHECKING:
    from asap.state.metering import UsageEvent


class UsageMetrics(ASAPBaseModel):
    """Flat usage metrics for a single task. Maps to UsageEvent via MeteringStore."""

    task_id: str = Field(..., description="Task identifier")
    agent_id: str = Field(..., description="Agent that produced the usage")
    consumer_id: str = Field(..., description="Consumer (caller) identifier")
    tokens_in: int = Field(default=0, ge=0, description="Input token count")
    tokens_out: int = Field(default=0, ge=0, description="Output token count")
    duration_ms: int = Field(default=0, ge=0, description="Duration in milliseconds")
    api_calls: int = Field(default=0, ge=0, description="Number of API calls")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")

    def to_usage_event(self) -> "UsageEvent":
        from asap.state.metering import UsageEvent, UsageMetrics as StateUsageMetrics

        return UsageEvent(
            task_id=self.task_id,
            agent_id=self.agent_id,
            consumer_id=self.consumer_id,
            metrics=StateUsageMetrics(
                tokens_in=self.tokens_in,
                tokens_out=self.tokens_out,
                duration_ms=self.duration_ms,
                api_calls=self.api_calls,
            ),
            timestamp=self.timestamp,
        )

    @classmethod
    def from_usage_event(cls, event: "UsageEvent") -> UsageMetrics:
        return cls(
            task_id=event.task_id,
            agent_id=event.agent_id,
            consumer_id=event.consumer_id,
            tokens_in=event.metrics.tokens_in,
            tokens_out=event.metrics.tokens_out,
            duration_ms=event.metrics.duration_ms,
            api_calls=event.metrics.api_calls,
            timestamp=event.timestamp,
        )


class UsageAggregateByAgent(ASAPBaseModel):
    agent_id: str = Field(..., description="Agent identifier")
    period: str = Field(..., description="Aggregation period (e.g. hour, day)")
    total_tokens: int = Field(default=0, ge=0, description="Sum of tokens (in + out)")
    total_duration_ms: int = Field(default=0, ge=0, description="Total duration in ms")
    total_tasks: int = Field(default=0, ge=0, description="Number of tasks")
    total_api_calls: int = Field(default=0, ge=0, description="Total API calls")
    avg_tokens_per_task: float = Field(default=0.0, ge=0, description="Average tokens per task")
    avg_duration_ms_per_task: float = Field(
        default=0.0, ge=0, description="Average duration per task in ms"
    )


class UsageAggregateByConsumer(ASAPBaseModel):
    consumer_id: str = Field(..., description="Consumer identifier")
    period: str = Field(..., description="Aggregation period (e.g. hour, day)")
    total_tokens: int = Field(default=0, ge=0, description="Sum of tokens (in + out)")
    total_duration_ms: int = Field(default=0, ge=0, description="Total duration in ms")
    total_tasks: int = Field(default=0, ge=0, description="Number of tasks")
    total_api_calls: int = Field(default=0, ge=0, description="Total API calls")
    avg_tokens_per_task: float = Field(default=0.0, ge=0, description="Average tokens per task")


class UsageAggregateByPeriod(ASAPBaseModel):
    period: str = Field(..., description="Aggregation period label")
    total_tokens: int = Field(default=0, ge=0, description="Sum of tokens (in + out)")
    total_duration_ms: int = Field(default=0, ge=0, description="Total duration in ms")
    total_tasks: int = Field(default=0, ge=0, description="Number of tasks")
    total_api_calls: int = Field(default=0, ge=0, description="Total API calls")
    unique_agents: int = Field(default=0, ge=0, description="Number of distinct agents")
    unique_consumers: int = Field(default=0, ge=0, description="Number of distinct consumers")


class BatchUsageRequest(ASAPBaseModel):
    events: list[UsageMetrics] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Usage metrics to record (max 1000 per batch)",
    )


class StorageStats(ASAPBaseModel):
    total_events: int = Field(default=0, ge=0, description="Total events stored")
    oldest_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of oldest record",
    )
    retention_ttl_seconds: int | None = Field(
        default=None,
        description="Retention TTL in seconds; None if disabled",
    )


class UsageSummary(ASAPBaseModel):
    total_tasks: int = Field(default=0, ge=0, description="Total number of tasks")
    total_tokens: int = Field(default=0, ge=0, description="Sum of tokens (in + out)")
    total_duration_ms: int = Field(default=0, ge=0, description="Total duration in ms")
    unique_agents: int = Field(default=0, ge=0, description="Number of distinct agents")
    unique_consumers: int = Field(default=0, ge=0, description="Number of distinct consumers")
    total_api_calls: int = Field(default=0, ge=0, description="Total API calls")
