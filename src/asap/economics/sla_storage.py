"""SLA storage: record and query SLA metrics and breaches (v1.3).

Protocol and implementations (InMemory, SQLite) for SLA metrics and breach
records. Shares the same SQLite file (asap_state.db) with metering and delegation.

SQLiteSLAStorage (v2.5.1 S1) subclasses :class:`AsyncSqliteRepository`, which owns
the aiosqlite plumbing, WAL pragmas, schema init, ISO parsing, and WHERE assembly
once for all persistent stores. The SLA-specific SQL + row mappers live here.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import aiosqlite  # noqa: F401 - retained so tests can patch `sla_storage.aiosqlite.connect`

from asap.economics.metering import StorageStats
from asap.economics.sla import SLABreach, SLAMetrics
from asap.state.stores._sqlite_base import (
    DEFAULT_DB_PATH,
    AsyncSqliteRepository,
    build_where,
    parse_iso,
)

# Backward-compat alias: tests/economics/test_sla_storage.py:18 imports
# `_parse_iso` from this module. The canonical impl now lives in the shared base.
_parse_iso = parse_iso

# WHERE allow-lists for the SLA query methods (fragments are compile-time
# constants; values are bound via params in build_where — never interpolated).
_METRICS_WHERE: dict[str, str] = {
    "agent_id": "agent_id = ?",
    "start": "period_end >= ?",
    "end": "period_start <= ?",
}
_BREACH_WHERE: dict[str, str] = {
    "agent_id": "agent_id = ?",
    "start": "detected_at >= ?",
    "end": "detected_at <= ?",
}

# Canonical SLA schema (both tables + both indexes); the base runs it
# idempotently under the per-instance lock.
_SLA_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS sla_metrics (
    agent_id TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    uptime_percent REAL NOT NULL,
    latency_p95_ms INTEGER NOT NULL,
    error_rate_percent REAL NOT NULL,
    tasks_completed INTEGER NOT NULL,
    tasks_failed INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sla_metrics_agent_period
    ON sla_metrics (agent_id, period_start);

CREATE TABLE IF NOT EXISTS sla_breaches (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    breach_type TEXT NOT NULL,
    threshold TEXT NOT NULL,
    actual TEXT NOT NULL,
    severity TEXT NOT NULL,
    detected_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_sla_breaches_agent_detected
    ON sla_breaches (agent_id, detected_at);
"""


@runtime_checkable
class SLAStorage(Protocol):
    """Protocol for storing and querying SLA metrics and breaches."""

    async def record_metrics(self, metrics: SLAMetrics) -> None: ...
    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]: ...
    async def record_breach(self, breach: SLABreach) -> None: ...
    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]: ...
    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int: ...
    async def stats(self) -> StorageStats: ...


class SLAStorageBase(ABC):
    """Abstract base for SLA storage implementations."""

    @abstractmethod
    async def record_metrics(self, metrics: SLAMetrics) -> None: ...

    @abstractmethod
    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]: ...

    @abstractmethod
    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int: ...

    @abstractmethod
    async def record_breach(self, breach: SLABreach) -> None: ...

    @abstractmethod
    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]: ...

    @abstractmethod
    async def stats(self) -> StorageStats: ...


def _metrics_matches(
    m: SLAMetrics, agent_id: str | None, start: datetime | None, end: datetime | None
) -> bool:
    if agent_id is not None and m.agent_id != agent_id:
        return False
    if start is not None and m.period_end < start:
        return False
    return not (end is not None and m.period_start > end)


def _breach_matches(
    b: SLABreach, agent_id: str | None, start: datetime | None, end: datetime | None
) -> bool:
    if agent_id is not None and b.agent_id != agent_id:
        return False
    if start is not None and b.detected_at < start:
        return False
    return not (end is not None and b.detected_at > end)


class InMemorySLAStorage(SLAStorageBase):
    """In-memory SLA storage for development and testing. Async-safe via asyncio.Lock."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._metrics: list[SLAMetrics] = []
        self._breaches: list[SLABreach] = []

    async def record_metrics(self, metrics: SLAMetrics) -> None:
        async with self._lock:
            self._metrics.append(metrics)

    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        async with self._lock:
            out = [m for m in self._metrics if _metrics_matches(m, agent_id, start, end)]
        out = sorted(out, key=lambda m: m.period_start)
        return out[offset : offset + limit] if limit is not None else out[offset:]

    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        async with self._lock:
            return sum(1 for m in self._metrics if _metrics_matches(m, agent_id, start, end))

    async def record_breach(self, breach: SLABreach) -> None:
        async with self._lock:
            self._breaches.append(breach)

    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]:
        async with self._lock:
            out = [b for b in self._breaches if _breach_matches(b, agent_id, start, end)]
        return sorted(out, key=lambda b: b.detected_at)

    async def stats(self) -> StorageStats:
        async with self._lock:
            total = len(self._metrics) + len(self._breaches)
            all_ts: list[datetime] = []
            for m in self._metrics:
                all_ts.extend([m.period_start, m.period_end])
            for b in self._breaches:
                all_ts.append(b.detected_at)
            oldest = min(all_ts) if all_ts else None
        return StorageStats(
            total_events=total,
            oldest_timestamp=oldest,
            retention_ttl_seconds=None,
        )


def _metrics_filters(
    agent_id: str | None, start: datetime | None, end: datetime | None
) -> dict[str, Any]:
    """Build the filter dict shared by query_metrics/count_metrics."""
    return {
        "agent_id": agent_id,
        "start": start.isoformat() if start else None,
        "end": end.isoformat() if end else None,
    }


def _row_to_metrics(r: tuple[Any, ...]) -> SLAMetrics:
    # Columns are NOT NULL; the `or now()` fallback only guards corrupted rows
    # so the non-Optional SLAMetrics fields stay non-None.
    return SLAMetrics(
        agent_id=str(r[0]),
        period_start=parse_iso(str(r[1])) or datetime.now(timezone.utc),
        period_end=parse_iso(str(r[2])) or datetime.now(timezone.utc),
        uptime_percent=float(r[3]),
        latency_p95_ms=int(r[4]),
        error_rate_percent=float(r[5]),
        tasks_completed=int(r[6]),
        tasks_failed=int(r[7]),
    )


def _row_to_breach(r: tuple[Any, ...]) -> SLABreach:
    # detected_at is NOT NULL (keep fallback); resolved_at is nullable (None passthrough).
    return SLABreach(
        id=str(r[0]),
        agent_id=str(r[1]),
        breach_type=str(r[2]),
        threshold=str(r[3]),
        actual=str(r[4]),
        severity=str(r[5]),
        detected_at=parse_iso(str(r[6])) or datetime.now(timezone.utc),
        resolved_at=parse_iso(str(r[7])) if r[7] else None,
    )


class SQLiteSLAStorage(AsyncSqliteRepository, SLAStorageBase):
    """SQLite-backed SLA storage. Tables: sla_metrics, sla_breaches. Shares asap_state.db.

    The base owns connection lifecycle, WAL pragmas, idempotent schema init, and
    the execute/fetch_all/fetch_one helpers; WHERE assembly is routed through
    build_where so dynamic fragments are allow-list-guarded.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        super().__init__(db_path, schema_ddl=_SLA_SCHEMA_DDL)

    async def record_metrics(self, metrics: SLAMetrics) -> None:
        await self.execute(
            "INSERT INTO sla_metrics (agent_id, period_start, period_end, "
            "uptime_percent, latency_p95_ms, error_rate_percent, "
            "tasks_completed, tasks_failed) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                metrics.agent_id,
                metrics.period_start.isoformat(),
                metrics.period_end.isoformat(),
                metrics.uptime_percent,
                metrics.latency_p95_ms,
                metrics.error_rate_percent,
                metrics.tasks_completed,
                metrics.tasks_failed,
            ),
        )

    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]:
        if offset < 0:
            raise ValueError("offset must be non-negative")
        where, params = build_where(_metrics_filters(agent_id, start, end), _METRICS_WHERE)
        # `where` is assembled by build_where from the _METRICS_WHERE allow-list;
        # values are bound via params — never interpolated into SQL.
        query = (
            f"SELECT agent_id, period_start, period_end, uptime_percent, "
            f"latency_p95_ms, error_rate_percent, tasks_completed, tasks_failed "
            f"FROM sla_metrics WHERE {where} ORDER BY period_start"  # nosec B608
        )
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)
        rows = await self.fetch_all(query, tuple(params))
        return [_row_to_metrics(r) for r in rows]

    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        where, params = build_where(_metrics_filters(agent_id, start, end), _METRICS_WHERE)
        row = await self.fetch_one(
            f"SELECT COUNT(*) FROM sla_metrics WHERE {where}",  # nosec B608
            tuple(params),
        )
        return int(row[0]) if row else 0

    async def record_breach(self, breach: SLABreach) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO sla_breaches (id, agent_id, breach_type, "
            "threshold, actual, severity, detected_at, resolved_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                breach.id,
                breach.agent_id,
                breach.breach_type,
                breach.threshold,
                breach.actual,
                breach.severity,
                breach.detected_at.isoformat(),
                breach.resolved_at.isoformat() if breach.resolved_at else None,
            ),
        )

    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]:
        filters = {
            "agent_id": agent_id,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        }
        where, params = build_where(filters, _BREACH_WHERE)
        query = (
            f"SELECT id, agent_id, breach_type, threshold, actual, severity, "
            f"detected_at, resolved_at FROM sla_breaches WHERE {where} "
            f"ORDER BY detected_at"  # nosec B608
        )
        rows = await self.fetch_all(query, tuple(params))
        return [_row_to_breach(r) for r in rows]

    async def stats(self) -> StorageStats:
        m_count_row = await self.fetch_one("SELECT COUNT(*) FROM sla_metrics")
        b_count_row = await self.fetch_one("SELECT COUNT(*) FROM sla_breaches")
        m_oldest_row = await self.fetch_one("SELECT MIN(period_start) FROM sla_metrics")
        b_oldest_row = await self.fetch_one("SELECT MIN(detected_at) FROM sla_breaches")
        m_count = int(m_count_row[0]) if m_count_row else 0
        b_count = int(b_count_row[0]) if b_count_row else 0
        oldest_ts: datetime | None = None
        for raw in (
            m_oldest_row[0] if m_oldest_row else None,
            b_oldest_row[0] if b_oldest_row else None,
        ):
            if raw is not None:
                dt = parse_iso(str(raw))
                if dt and (oldest_ts is None or dt < oldest_ts):
                    oldest_ts = dt
        return StorageStats(
            total_events=m_count + b_count,
            oldest_timestamp=oldest_ts,
            retention_ttl_seconds=None,
        )


__all__ = [
    "SLAStorage",
    "SLAStorageBase",
    "InMemorySLAStorage",
    "SQLiteSLAStorage",
    "_parse_iso",
]
