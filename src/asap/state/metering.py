"""ASAP Metering Store for usage and economics (v1.3 foundation).

This module defines the abstract interface and models for storing usage metering
data, enabling the v1.3 Economics Layer (METER-001 to METER-006).

Example:
    >>> store = InMemoryMeteringStore()
    >>> isinstance(store, MeteringStore)
    True
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from datetime import datetime
from typing import Protocol, runtime_checkable

from pydantic import Field

from asap.models.base import ASAPBaseModel


class UsageMetrics(ASAPBaseModel):
    """Metrics for a single usage event (tokens, duration, API calls).

    Attributes:
        tokens_in: Input token count.
        tokens_out: Output token count.
        duration_ms: Duration in milliseconds.
        api_calls: Number of API calls.
    """

    tokens_in: int = Field(default=0, ge=0, description="Input token count")
    tokens_out: int = Field(default=0, ge=0, description="Output token count")
    duration_ms: int = Field(default=0, ge=0, description="Duration in milliseconds")
    api_calls: int = Field(default=0, ge=0, description="Number of API calls")


class UsageEvent(ASAPBaseModel):
    """A single usage event for metering (v1.3 foundation).

    Attributes:
        task_id: Task identifier.
        agent_id: Agent that produced the usage.
        consumer_id: Consumer (caller) identifier.
        metrics: Token, duration and API call metrics.
        timestamp: When the event occurred (UTC).
    """

    task_id: str = Field(..., description="Task identifier")
    agent_id: str = Field(..., description="Agent that produced the usage")
    consumer_id: str = Field(..., description="Consumer (caller) identifier")
    metrics: UsageMetrics = Field(
        default_factory=UsageMetrics,
        description="Token, duration and API call metrics",
    )
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")


class UsageAggregate(ASAPBaseModel):
    """Aggregated usage for an agent over a period.

    Attributes:
        agent_id: Agent identifier.
        period: Aggregation period (e.g. 'hour', 'day').
        total_tokens: Sum of input + output tokens.
        total_duration: Total duration in milliseconds.
        total_tasks: Number of tasks.
        total_api_calls: Total API calls.
    """

    agent_id: str = Field(..., description="Agent identifier")
    period: str = Field(..., description="Aggregation period (e.g. hour, day)")
    total_tokens: int = Field(default=0, ge=0, description="Sum of tokens (in + out)")
    total_duration: int = Field(default=0, ge=0, description="Total duration in ms")
    total_tasks: int = Field(default=0, ge=0, description="Number of tasks")
    total_api_calls: int = Field(default=0, ge=0, description="Total API calls")


@runtime_checkable
class MeteringStore(Protocol):
    """Protocol for usage metering storage implementations.

    Provides the interface for recording and querying usage events and
    aggregates. Implementations can use various backends (memory, SQLite, etc.).
    Foundation for v1.3 Usage Metering.

    Example:
        >>> class CustomMeteringStore:
        ...     async def record(self, event: UsageEvent) -> None: ...
        ...     async def query(self, agent_id: str, start: datetime, end: datetime) -> list[UsageEvent]: ...
        ...     async def aggregate(self, agent_id: str, period: str) -> UsageAggregate: ...
        >>> isinstance(CustomMeteringStore(), MeteringStore)
        True
    """

    def record(self, event: "UsageEvent") -> "Awaitable[None]":
        """Record a usage event.

        Args:
            event: The usage event to store.

        Example:
            >>> store = InMemoryMeteringStore()
            >>> event = UsageEvent(task_id="task_01", agent_id="agent_01", ...)
            >>> store.record(event)
        """
        ...

    def query(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> Awaitable[list["UsageEvent"]]:
        """Query usage events for an agent in a time range.

        Args:
            agent_id: Agent identifier.
            start: Start of the time range (inclusive).
            end: End of the time range (inclusive).
            limit: Maximum number of events to return (None = no limit).
            offset: Number of events to skip (default 0).

        Returns:
            List of usage events in the range, ordered by timestamp.

        Example:
            >>> store = InMemoryMeteringStore()
            >>> events = store.query("agent_01", start, end)
        """
        ...

    def aggregate(self, agent_id: str, period: str) -> Awaitable["UsageAggregate"]:
        """Aggregate usage for an agent over a period.

        Args:
            agent_id: Agent identifier.
            period: Aggregation period (e.g. "hour", "day").

        Returns:
            Usage aggregate for the period.

        Example:
            >>> store = InMemoryMeteringStore()
            >>> agg = store.aggregate("agent_01", "day")
        """
        ...


class InMemoryMeteringStore:
    """In-memory implementation of MeteringStore.

    Stores usage events in a list with asyncio.Lock for async-safe concurrent access.
    Used for testing and development; not persistent across restarts.
    """

    def __init__(self) -> None:
        """Initialize the in-memory metering store."""
        self._lock = asyncio.Lock()
        self._events: list[UsageEvent] = []

    async def record(self, event: UsageEvent) -> None:
        """Append a usage event to the store (async-safe)."""
        async with self._lock:
            self._events.append(event)

    async def query(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[UsageEvent]:
        """Return events for the agent in [start, end], sorted by timestamp."""
        if offset < 0:
            raise ValueError("offset must be non-negative")
        async with self._lock:
            out = [
                e for e in self._events if e.agent_id == agent_id and start <= e.timestamp <= end
            ]
        out = sorted(out, key=lambda e: e.timestamp)
        return out[offset : offset + limit] if limit is not None else out[offset:]

    async def aggregate(self, agent_id: str, period: str) -> UsageAggregate:
        """Aggregate all stored events for the agent into one UsageAggregate."""
        async with self._lock:
            agent_events = [e for e in self._events if e.agent_id == agent_id]
        total_tokens = sum(e.metrics.tokens_in + e.metrics.tokens_out for e in agent_events)
        total_duration = sum(e.metrics.duration_ms for e in agent_events)
        total_tasks = len(agent_events)
        total_api_calls = sum(e.metrics.api_calls for e in agent_events)
        return UsageAggregate(
            agent_id=agent_id,
            period=period,
            total_tokens=total_tokens,
            total_duration=total_duration,
            total_tasks=total_tasks,
            total_api_calls=total_api_calls,
        )
