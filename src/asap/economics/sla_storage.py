"""SLA storage: record and query SLA metrics and breaches (v1.3).

Protocol and implementations (InMemory, SQLite) for SLA metrics and breach
records. Shares the same SQLite file (asap_state.db) with metering and delegation.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiosqlite
from typing import Optional

from asap.economics.metering import StorageStats
from asap.economics.sla import SLABreach, SLAMetrics

_DEFAULT_DB_PATH = "asap_state.db"
_METRICS_TABLE = "sla_metrics"
_BREACHES_TABLE = "sla_breaches"


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
        self._lock: Optional[asyncio.Lock] = None
        self._metrics: list[SLAMetrics] = []
        self._breaches: list[SLABreach] = []

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def record_metrics(self, metrics: SLAMetrics) -> None:
        async with self.lock:
            self._metrics.append(metrics)

    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]:
        async with self.lock:
            out = [m for m in self._metrics if _metrics_matches(m, agent_id, start, end)]
        out = sorted(out, key=lambda m: m.period_start)
        return out[offset : offset + limit] if limit is not None else out[offset:]

    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        async with self.lock:
            return sum(1 for m in self._metrics if _metrics_matches(m, agent_id, start, end))

    async def record_breach(self, breach: SLABreach) -> None:
        async with self.lock:
            self._breaches.append(breach)

    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]:
        async with self.lock:
            out = [b for b in self._breaches if _breach_matches(b, agent_id, start, end)]
        return sorted(out, key=lambda b: b.detected_at)

    async def stats(self) -> StorageStats:
        async with self.lock:
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


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class SQLiteSLAStorage(SLAStorageBase):
    """SQLite-backed SLA storage. Tables: sla_metrics, sla_breaches. Shares asap_state.db."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._initialized = False

    async def _ensure_tables(self, conn: aiosqlite.Connection) -> None:
        if self._initialized:
            return
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_METRICS_TABLE} (
                agent_id TEXT NOT NULL,
                period_start TEXT NOT NULL,
                period_end TEXT NOT NULL,
                uptime_percent REAL NOT NULL,
                latency_p95_ms INTEGER NOT NULL,
                error_rate_percent REAL NOT NULL,
                tasks_completed INTEGER NOT NULL,
                tasks_failed INTEGER NOT NULL
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_sla_metrics_agent_period
            ON {_METRICS_TABLE} (agent_id, period_start)
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_BREACHES_TABLE} (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                breach_type TEXT NOT NULL,
                threshold TEXT NOT NULL,
                actual TEXT NOT NULL,
                severity TEXT NOT NULL,
                detected_at TEXT NOT NULL,
                resolved_at TEXT
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_sla_breaches_agent_detected
            ON {_BREACHES_TABLE} (agent_id, detected_at)
            """
        )
        await conn.commit()
        self._initialized = True

    async def record_metrics(self, metrics: SLAMetrics) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            await conn.execute(
                f"""
                INSERT INTO {_METRICS_TABLE} (
                    agent_id, period_start, period_end,
                    uptime_percent, latency_p95_ms, error_rate_percent,
                    tasks_completed, tasks_failed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
            await conn.commit()

    async def query_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SLAMetrics]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            query = f"SELECT agent_id, period_start, period_end, uptime_percent, latency_p95_ms, error_rate_percent, tasks_completed, tasks_failed FROM {_METRICS_TABLE} WHERE 1=1"
            params: list[object] = []
            if agent_id is not None:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if start is not None:
                query += " AND period_end >= ?"
                params.append(start.isoformat())
            if end is not None:
                query += " AND period_start <= ?"
                params.append(end.isoformat())
            query += " ORDER BY period_start"
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            elif offset > 0:
                query += " LIMIT -1 OFFSET ?"
                params.append(offset)
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [
            SLAMetrics(
                agent_id=str(r[0]),
                period_start=_parse_iso(str(r[1])) or datetime.now(timezone.utc),
                period_end=_parse_iso(str(r[2])) or datetime.now(timezone.utc),
                uptime_percent=float(r[3]),
                latency_p95_ms=int(r[4]),
                error_rate_percent=float(r[5]),
                tasks_completed=int(r[6]),
                tasks_failed=int(r[7]),
            )
            for r in rows
        ]

    async def count_metrics(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> int:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            query = f"SELECT COUNT(*) FROM {_METRICS_TABLE} WHERE 1=1"
            params: list[object] = []
            if agent_id is not None:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if start is not None:
                query += " AND period_end >= ?"
                params.append(start.isoformat())
            if end is not None:
                query += " AND period_start <= ?"
                params.append(end.isoformat())
            cursor = await conn.execute(query, params)
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def record_breach(self, breach: SLABreach) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            await conn.execute(
                f"""
                INSERT OR REPLACE INTO {_BREACHES_TABLE} (id, agent_id, breach_type, threshold, actual, severity, detected_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
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
            await conn.commit()

    async def query_breaches(
        self,
        agent_id: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> list[SLABreach]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            query = f"SELECT id, agent_id, breach_type, threshold, actual, severity, detected_at, resolved_at FROM {_BREACHES_TABLE} WHERE 1=1"
            params: list[object] = []
            if agent_id is not None:
                query += " AND agent_id = ?"
                params.append(agent_id)
            if start is not None:
                query += " AND detected_at >= ?"
                params.append(start.isoformat())
            if end is not None:
                query += " AND detected_at <= ?"
                params.append(end.isoformat())
            query += " ORDER BY detected_at"
            cursor = await conn.execute(query, params)
            rows = await cursor.fetchall()
        return [
            SLABreach(
                id=str(r[0]),
                agent_id=str(r[1]),
                breach_type=str(r[2]),
                threshold=str(r[3]),
                actual=str(r[4]),
                severity=str(r[5]),
                detected_at=_parse_iso(str(r[6])) or datetime.now(timezone.utc),
                resolved_at=_parse_iso(str(r[7])) if r[7] else None,
            )
            for r in rows
        ]

    async def stats(self) -> StorageStats:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {_METRICS_TABLE}")
            m_count = (await cursor.fetchone() or (0,))[0]
            cursor = await conn.execute(f"SELECT COUNT(*) FROM {_BREACHES_TABLE}")
            b_count = (await cursor.fetchone() or (0,))[0]
            cursor = await conn.execute(f"SELECT MIN(period_start) FROM {_METRICS_TABLE}")
            m_oldest = (await cursor.fetchone() or (None,))[0]
            cursor = await conn.execute(f"SELECT MIN(detected_at) FROM {_BREACHES_TABLE}")
            b_oldest = (await cursor.fetchone() or (None,))[0]
        oldest_ts: datetime | None = None
        for raw in (m_oldest, b_oldest):
            if raw is not None:
                dt = _parse_iso(str(raw))
                if dt and (oldest_ts is None or dt < oldest_ts):
                    oldest_ts = dt
        return StorageStats(
            total_events=m_count + b_count,
            oldest_timestamp=oldest_ts,
            retention_ttl_seconds=None,
        )
