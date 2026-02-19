"""Metering storage: record, query, aggregate usage metrics (v1.3).

**Architecture:** Two metering layers exist:
- **Economics layer** (this module): ``MeteringStorage`` protocol with full CRUD,
  aggregation, summary, stats, purge. Used by the Usage REST API and as the
  backend for the adapter.
- **State layer** (``asap.state.metering``): ``MeteringStore`` protocol with
  minimal record/query/aggregate. Used by handlers for task completion recording.
  The ``metering_storage_adapter`` bridges economics -> state so a single
  MeteringStorage can serve both the API and handlers.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, Union, cast, runtime_checkable

if TYPE_CHECKING:
    from asap.state.metering import MeteringStore, UsageAggregate as StateUsageAggregate, UsageEvent

import aiosqlite
from pydantic import Field

from asap.economics.metering import (
    StorageStats,
    UsageAggregateByAgent,
    UsageAggregateByConsumer,
    UsageAggregateByPeriod,
    UsageMetrics,
    UsageSummary,
)
from asap.models.base import ASAPBaseModel

UsageAggregate = Union[
    UsageAggregateByAgent,
    UsageAggregateByConsumer,
    UsageAggregateByPeriod,
]


class MeteringQuery(ASAPBaseModel):
    agent_id: str | None = Field(default=None, description="Filter by agent")
    consumer_id: str | None = Field(default=None, description="Filter by consumer")
    task_id: str | None = Field(default=None, description="Filter by task")
    start: datetime | None = Field(default=None, description="Start of time range")
    end: datetime | None = Field(default=None, description="End of time range")
    limit: int | None = Field(default=None, ge=1, description="Max events to return")
    offset: int = Field(default=0, ge=0, description="Events to skip")


@runtime_checkable
class MeteringStorage(Protocol):
    async def record(self, metrics: UsageMetrics) -> None: ...
    async def query(self, filters: MeteringQuery) -> list[UsageMetrics]: ...
    async def aggregate(
        self,
        group_by: str,
        filters: MeteringQuery | None = None,
    ) -> list[UsageAggregate]: ...
    async def summary(self, filters: MeteringQuery | None = None) -> UsageSummary: ...
    async def stats(self) -> StorageStats: ...
    async def purge_expired(self) -> int: ...


class MeteringStorageBase(ABC):
    @abstractmethod
    async def record(self, metrics: UsageMetrics) -> None: ...

    @abstractmethod
    async def query(self, filters: MeteringQuery) -> list[UsageMetrics]: ...

    @abstractmethod
    async def aggregate(
        self,
        group_by: str,
        filters: MeteringQuery | None = None,
    ) -> list[UsageAggregate]: ...

    @abstractmethod
    async def summary(self, filters: MeteringQuery | None = None) -> UsageSummary: ...

    @abstractmethod
    async def stats(self) -> StorageStats: ...

    @abstractmethod
    async def purge_expired(self) -> int: ...


def _matches(e: UsageMetrics, f: MeteringQuery) -> bool:
    return (
        (f.agent_id is None or e.agent_id == f.agent_id)
        and (f.consumer_id is None or e.consumer_id == f.consumer_id)
        and (f.task_id is None or e.task_id == f.task_id)
        and (f.start is None or e.timestamp >= f.start)
        and (f.end is None or e.timestamp <= f.end)
    )


def _apply_query_filters(
    events: list[UsageMetrics],
    filters: MeteringQuery,
) -> list[UsageMetrics]:
    filtered = sorted((e for e in events if _matches(e, filters)), key=lambda x: x.timestamp)
    out = filtered[filters.offset :]
    return out[: filters.limit] if filters.limit else out


def _aggregate_by_agent(events: list[UsageMetrics]) -> list[UsageAggregateByAgent]:
    """Aggregate usage by agent_id."""
    by_agent: dict[str, list[UsageMetrics]] = {}
    for e in events:
        by_agent.setdefault(e.agent_id, []).append(e)
    out: list[UsageAggregateByAgent] = []
    for agent_id, agent_events in by_agent.items():
        total_tokens = sum(e.tokens_in + e.tokens_out for e in agent_events)
        total_duration = sum(e.duration_ms for e in agent_events)
        total_tasks = len(agent_events)
        total_api_calls = sum(e.api_calls for e in agent_events)
        avg_tokens = total_tokens / total_tasks if total_tasks else 0.0
        avg_duration = total_duration / total_tasks if total_tasks else 0.0
        out.append(
            UsageAggregateByAgent(
                agent_id=agent_id,
                period="all",
                total_tokens=total_tokens,
                total_duration_ms=total_duration,
                total_tasks=total_tasks,
                total_api_calls=total_api_calls,
                avg_tokens_per_task=avg_tokens,
                avg_duration_ms_per_task=avg_duration,
            )
        )
    return sorted(out, key=lambda a: a.agent_id)


def _aggregate_by_consumer(events: list[UsageMetrics]) -> list[UsageAggregateByConsumer]:
    """Aggregate usage by consumer_id."""
    by_consumer: dict[str, list[UsageMetrics]] = {}
    for e in events:
        by_consumer.setdefault(e.consumer_id, []).append(e)
    out: list[UsageAggregateByConsumer] = []
    for consumer_id, consumer_events in by_consumer.items():
        total_tokens = sum(e.tokens_in + e.tokens_out for e in consumer_events)
        total_duration = sum(e.duration_ms for e in consumer_events)
        total_tasks = len(consumer_events)
        total_api_calls = sum(e.api_calls for e in consumer_events)
        avg_tokens = total_tokens / total_tasks if total_tasks else 0.0
        out.append(
            UsageAggregateByConsumer(
                consumer_id=consumer_id,
                period="all",
                total_tokens=total_tokens,
                total_duration_ms=total_duration,
                total_tasks=total_tasks,
                total_api_calls=total_api_calls,
                avg_tokens_per_task=avg_tokens,
            )
        )
    return sorted(out, key=lambda a: a.consumer_id)


def _compute_summary(events: list[UsageMetrics]) -> UsageSummary:
    """Compute UsageSummary from a list of events."""
    if not events:
        return UsageSummary()
    total_tokens = sum(e.tokens_in + e.tokens_out for e in events)
    total_duration = sum(e.duration_ms for e in events)
    total_tasks = len(events)
    total_api_calls = sum(e.api_calls for e in events)
    unique_agents = len({e.agent_id for e in events})
    unique_consumers = len({e.consumer_id for e in events})
    return UsageSummary(
        total_tasks=total_tasks,
        total_tokens=total_tokens,
        total_duration_ms=total_duration,
        unique_agents=unique_agents,
        unique_consumers=unique_consumers,
        total_api_calls=total_api_calls,
    )


def _aggregate_by_period(
    events: list[UsageMetrics],
    period_format: str,
) -> list[UsageAggregateByPeriod]:
    """Aggregate usage by time period (day or week)."""

    def _period_key(ts: datetime) -> str:
        d = ts.date()
        if period_format == "day":
            return d.isoformat()
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"

    by_period: dict[str, list[UsageMetrics]] = {}
    for e in events:
        key = _period_key(e.timestamp)
        by_period.setdefault(key, []).append(e)

    out: list[UsageAggregateByPeriod] = []
    for period, period_events in by_period.items():
        total_tokens = sum(e.tokens_in + e.tokens_out for e in period_events)
        total_duration = sum(e.duration_ms for e in period_events)
        total_tasks = len(period_events)
        total_api_calls = sum(e.api_calls for e in period_events)
        unique_agents = len({e.agent_id for e in period_events})
        unique_consumers = len({e.consumer_id for e in period_events})
        out.append(
            UsageAggregateByPeriod(
                period=period,
                total_tokens=total_tokens,
                total_duration_ms=total_duration,
                total_tasks=total_tasks,
                total_api_calls=total_api_calls,
                unique_agents=unique_agents,
                unique_consumers=unique_consumers,
            )
        )
    return sorted(out, key=lambda a: a.period)


class InMemoryMeteringStorage(MeteringStorageBase):
    """In-memory MeteringStorage for development and testing.

    Stores UsageMetrics in a list. Not persistent across restarts.
    Async-safe via asyncio.Lock. Optional retention_ttl_seconds for auto-cleanup.
    """

    def __init__(self, retention_ttl_seconds: int | None = None) -> None:
        """Initialize the in-memory store.

        Args:
            retention_ttl_seconds: If set, purge_expired() removes events older
                than this. None disables retention (keep all).
        """
        self._lock = asyncio.Lock()
        self._events: list[UsageMetrics] = []
        self._retention_ttl_seconds = retention_ttl_seconds

    async def record(self, metrics: UsageMetrics) -> None:
        """Append a usage event (async-safe)."""
        async with self._lock:
            self._events.append(metrics)

    async def query(self, filters: MeteringQuery) -> list[UsageMetrics]:
        """Return events matching filters, sorted by timestamp."""
        async with self._lock:
            return _apply_query_filters(list(self._events), filters)

    async def aggregate(
        self,
        group_by: str,
        filters: MeteringQuery | None = None,
    ) -> list[UsageAggregate]:
        """Aggregate by agent, consumer, day, or week, optionally filtered."""
        async with self._lock:
            events = list(self._events)
        if filters is not None:
            agg_filters = MeteringQuery(
                agent_id=filters.agent_id,
                consumer_id=filters.consumer_id,
                task_id=filters.task_id,
                start=filters.start,
                end=filters.end,
                limit=None,
                offset=0,
            )
            events = _apply_query_filters(events, agg_filters)
        if group_by == "agent":
            return cast(list[UsageAggregate], _aggregate_by_agent(events))
        if group_by == "consumer":
            return cast(list[UsageAggregate], _aggregate_by_consumer(events))
        if group_by == "day":
            return cast(list[UsageAggregate], _aggregate_by_period(events, "day"))
        if group_by == "week":
            return cast(list[UsageAggregate], _aggregate_by_period(events, "week"))
        raise ValueError(
            f"group_by must be one of 'agent', 'consumer', 'day', 'week'; got {group_by!r}"
        )

    async def summary(self, filters: MeteringQuery | None = None) -> UsageSummary:
        """Return dashboard summary, optionally filtered."""
        async with self._lock:
            events = list(self._events)
        if filters is not None:
            agg_filters = MeteringQuery(
                agent_id=filters.agent_id,
                consumer_id=filters.consumer_id,
                task_id=filters.task_id,
                start=filters.start,
                end=filters.end,
                limit=None,
                offset=0,
            )
            events = _apply_query_filters(events, agg_filters)
        return _compute_summary(events)

    async def stats(self) -> StorageStats:
        """Return storage statistics."""
        async with self._lock:
            events = list(self._events)
        if not events:
            return StorageStats(
                total_events=0,
                oldest_timestamp=None,
                retention_ttl_seconds=self._retention_ttl_seconds,
            )
        oldest = min(e.timestamp for e in events)
        return StorageStats(
            total_events=len(events),
            oldest_timestamp=oldest,
            retention_ttl_seconds=self._retention_ttl_seconds,
        )

    async def purge_expired(self) -> int:
        """Remove events older than retention_ttl_seconds. Returns count removed."""
        if self._retention_ttl_seconds is None:
            return 0
        from datetime import timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._retention_ttl_seconds)
        cutoff = cutoff.replace(microsecond=0)
        async with self._lock:
            before = len(self._events)
            self._events = [e for e in self._events if e.timestamp >= cutoff]
            return before - len(self._events)


# Adapter: MeteringStorage -> MeteringStore (state layer) for handler recording.
def metering_storage_adapter(storage: MeteringStorage) -> "MeteringStore":
    """Create MeteringStore adapter wrapping MeteringStorage for use by handlers."""

    class _Adapter:
        def __init__(self, s: MeteringStorage) -> None:
            self._storage = s

        async def record(self, event: "UsageEvent") -> None:
            metrics = UsageMetrics.from_usage_event(event)
            await self._storage.record(metrics)

        async def query(
            self,
            agent_id: str,
            start: datetime,
            end: datetime,
            limit: int | None = None,
            offset: int = 0,
        ) -> list["UsageEvent"]:
            filters = MeteringQuery(
                agent_id=agent_id,
                start=start,
                end=end,
                limit=limit,
                offset=offset,
            )
            events = await self._storage.query(filters)
            return [m.to_usage_event() for m in events]

        async def aggregate(self, agent_id: str, period: str) -> "StateUsageAggregate":
            from asap.economics.metering import UsageAggregateByAgent
            from asap.state.metering import UsageAggregate as StateUsageAggregate

            filters = _period_to_metering_query(agent_id, period)
            aggs = await self._storage.aggregate("agent", filters=filters)
            for a in aggs:
                if isinstance(a, UsageAggregateByAgent) and a.agent_id == agent_id:
                    return StateUsageAggregate(
                        agent_id=a.agent_id,
                        period=period,
                        total_tokens=a.total_tokens,
                        total_duration=a.total_duration_ms,
                        total_tasks=a.total_tasks,
                        total_api_calls=a.total_api_calls,
                    )
            return StateUsageAggregate(agent_id=agent_id, period=period)

    return _Adapter(storage)


def _period_to_metering_query(agent_id: str, period: str) -> MeteringQuery | None:
    """Convert period string (hour, day, week, today) to MeteringQuery with start/end.

    Returns None for unknown periods (no time filter).
    """
    from datetime import timedelta, timezone

    now = datetime.now(timezone.utc)
    if period in ("hour", "h"):
        start = now - timedelta(hours=1)
        return MeteringQuery(agent_id=agent_id, start=start, end=now)
    if period in ("day", "d", "today"):
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return MeteringQuery(agent_id=agent_id, start=start, end=now)
    if period in ("week", "w"):
        start = now - timedelta(weeks=1)
        return MeteringQuery(agent_id=agent_id, start=start, end=now)
    # Unknown period: filter by agent_id only (no time range)
    return MeteringQuery(agent_id=agent_id)


# SQLite storage constants (aligned with state layer for shared DB).
_DEFAULT_DB_PATH = "asap_state.db"
# Safe to use in f-strings: compile-time constant, never user-controlled (no SQL injection).
_USAGE_EVENTS_TABLE = "usage_events"


def _metrics_to_row(metrics: UsageMetrics, event_id: str) -> tuple[str, str, str, str, str, str]:
    """Serialize UsageMetrics to DB row (same schema as state UsageEvent)."""
    metrics_json = json.dumps(
        {
            "tokens_in": metrics.tokens_in,
            "tokens_out": metrics.tokens_out,
            "duration_ms": metrics.duration_ms,
            "api_calls": metrics.api_calls,
        }
    )
    ts = metrics.timestamp.isoformat()
    return (
        event_id,
        metrics.task_id,
        metrics.agent_id,
        metrics.consumer_id,
        metrics_json,
        ts,
    )


def _row_to_metrics(row: tuple[Any, ...]) -> UsageMetrics:
    """Build UsageMetrics from DB row."""
    _id, task_id, agent_id, consumer_id, metrics_json, ts_str = row
    data = json.loads(metrics_json)
    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return UsageMetrics(
        task_id=task_id,
        agent_id=agent_id,
        consumer_id=consumer_id,
        tokens_in=data.get("tokens_in", 0),
        tokens_out=data.get("tokens_out", 0),
        duration_ms=data.get("duration_ms", 0),
        api_calls=data.get("api_calls", 0),
        timestamp=ts,
    )


class SQLiteMeteringStorage(MeteringStorageBase):
    """SQLite-backed MeteringStorage; usage events persist across restarts.

    Uses the same usage_events table as state SQLiteMeteringStore for
    compatibility. Indexed by agent_id, consumer_id, and timestamp.
    Optional retention_ttl_seconds for configurable TTL; call purge_expired()
    periodically to remove old data.
    """

    def __init__(
        self,
        db_path: str | Path = _DEFAULT_DB_PATH,
        retention_ttl_seconds: int | None = None,
    ) -> None:
        """Initialize with database file path.

        Args:
            db_path: Path to SQLite database file.
            retention_ttl_seconds: If set, purge_expired() removes events older
                than this. None disables retention (keep all).
        """
        self._db_path = Path(db_path)
        self._retention_ttl_seconds = retention_ttl_seconds

    async def _ensure_table(self, conn: aiosqlite.Connection) -> None:
        """Create usage_events table and indexes if not exists."""
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_USAGE_EVENTS_TABLE} (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                consumer_id TEXT NOT NULL,
                metrics TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_usage_agent_timestamp
            ON {_USAGE_EVENTS_TABLE} (agent_id, timestamp)
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_usage_consumer_timestamp
            ON {_USAGE_EVENTS_TABLE} (consumer_id, timestamp)
            """
        )
        await conn.commit()

    async def _record_impl(self, metrics: UsageMetrics) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            event_id = f"evt_{uuid.uuid4().hex}"
            row = _metrics_to_row(metrics, event_id)
            await conn.execute(
                f"""
                INSERT INTO {_USAGE_EVENTS_TABLE}
                (id, task_id, agent_id, consumer_id, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            await conn.commit()

    async def _query_impl(self, filters: MeteringQuery) -> list[UsageMetrics]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            conditions: list[str] = []
            params: list[Any] = []
            if filters.agent_id is not None:
                conditions.append("agent_id = ?")
                params.append(filters.agent_id)
            if filters.consumer_id is not None:
                conditions.append("consumer_id = ?")
                params.append(filters.consumer_id)
            if filters.task_id is not None:
                conditions.append("task_id = ?")
                params.append(filters.task_id)
            if filters.start is not None:
                conditions.append("timestamp >= ?")
                params.append(filters.start.isoformat())
            if filters.end is not None:
                conditions.append("timestamp <= ?")
                params.append(filters.end.isoformat())
            where = " AND ".join(conditions) if conditions else "1=1"
            sql = f"""
                SELECT id, task_id, agent_id, consumer_id, metrics, timestamp
                FROM {_USAGE_EVENTS_TABLE}
                WHERE {where}
                ORDER BY timestamp
                LIMIT ? OFFSET ?
            """
            limit_val = filters.limit if filters.limit is not None else -1
            params.extend([limit_val, filters.offset])
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            return [_row_to_metrics(tuple(r)) for r in rows]

    async def _aggregate_impl(
        self,
        group_by: str,
        filters: MeteringQuery | None = None,
    ) -> list[UsageAggregate]:
        if filters is not None:
            agg_filters = MeteringQuery(
                agent_id=filters.agent_id,
                consumer_id=filters.consumer_id,
                task_id=filters.task_id,
                start=filters.start,
                end=filters.end,
                limit=None,
                offset=0,
            )
            events = await self._query_impl(agg_filters)
        else:
            async with aiosqlite.connect(self._db_path) as conn:
                await self._ensure_table(conn)
                cursor = await conn.execute(
                    f"""
                    SELECT id, task_id, agent_id, consumer_id, metrics, timestamp
                    FROM {_USAGE_EVENTS_TABLE}
                    ORDER BY timestamp
                    """,
                )
                rows = await cursor.fetchall()
            events = [_row_to_metrics(tuple(r)) for r in rows]
        if group_by == "agent":
            return cast(list[UsageAggregate], _aggregate_by_agent(events))
        if group_by == "consumer":
            return cast(list[UsageAggregate], _aggregate_by_consumer(events))
        if group_by == "day":
            return cast(list[UsageAggregate], _aggregate_by_period(events, "day"))
        if group_by == "week":
            return cast(list[UsageAggregate], _aggregate_by_period(events, "week"))
        raise ValueError(
            f"group_by must be one of 'agent', 'consumer', 'day', 'week'; got {group_by!r}"
        )

    async def record(self, metrics: UsageMetrics) -> None:
        """Record a usage event."""
        await self._record_impl(metrics)

    async def query(self, filters: MeteringQuery) -> list[UsageMetrics]:
        """Query events with filters."""
        return await self._query_impl(filters)

    async def aggregate(
        self,
        group_by: str,
        filters: MeteringQuery | None = None,
    ) -> list[UsageAggregate]:
        """Aggregate by agent, consumer, day, or week."""
        return await self._aggregate_impl(group_by, filters)

    async def _summary_impl(self, filters: MeteringQuery | None = None) -> UsageSummary:
        """Compute summary from events, optionally filtered."""
        if filters is not None:
            summary_filters = MeteringQuery(
                agent_id=filters.agent_id,
                consumer_id=filters.consumer_id,
                task_id=filters.task_id,
                start=filters.start,
                end=filters.end,
                limit=None,
                offset=0,
            )
            events = await self._query_impl(summary_filters)
        else:
            async with aiosqlite.connect(self._db_path) as conn:
                await self._ensure_table(conn)
                cursor = await conn.execute(
                    f"""
                    SELECT id, task_id, agent_id, consumer_id, metrics, timestamp
                    FROM {_USAGE_EVENTS_TABLE}
                    ORDER BY timestamp
                    """,
                )
                rows = await cursor.fetchall()
            events = [_row_to_metrics(tuple(r)) for r in rows]
        return _compute_summary(events)

    async def summary(self, filters: MeteringQuery | None = None) -> UsageSummary:
        """Return dashboard summary."""
        return await self._summary_impl(filters)

    async def _stats_impl(self) -> StorageStats:
        """Compute storage stats from SQLite."""
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            cursor = await conn.execute(
                f"""
                SELECT COUNT(*), MIN(timestamp)
                FROM {_USAGE_EVENTS_TABLE}
                """,
            )
            row = await cursor.fetchone()
        count = row[0] if row and row[0] is not None else 0
        oldest_ts: datetime | None = None
        if row and row[1] is not None:
            oldest_ts = datetime.fromisoformat(str(row[1]).replace("Z", "+00:00"))
        return StorageStats(
            total_events=count,
            oldest_timestamp=oldest_ts,
            retention_ttl_seconds=self._retention_ttl_seconds,
        )

    async def stats(self) -> StorageStats:
        """Return storage statistics."""
        return await self._stats_impl()

    async def _purge_expired_impl(self) -> int:
        """Delete events older than retention_ttl_seconds. Returns count removed."""
        if self._retention_ttl_seconds is None:
            return 0
        from datetime import timedelta, timezone

        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._retention_ttl_seconds)
        cutoff = cutoff.replace(microsecond=0)
        cutoff_str = cutoff.isoformat()
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_table(conn)
            cursor = await conn.execute(
                f"""
                DELETE FROM {_USAGE_EVENTS_TABLE}
                WHERE timestamp < ?
                """,
                (cutoff_str,),
            )
            deleted = cursor.rowcount if cursor.rowcount is not None else 0
            await conn.commit()
            return max(0, deleted)

    async def purge_expired(self) -> int:
        """Remove events older than retention_ttl_seconds. Returns count removed."""
        return await self._purge_expired_impl()
