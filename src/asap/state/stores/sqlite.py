"""SQLite-backed SnapshotStore and MeteringStore (persistent, file-based)."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import aiosqlite

from asap.models.entities import StateSnapshot
from asap.models.types import TaskID
from asap.state.metering import UsageAggregate, UsageEvent, UsageMetrics

DEFAULT_DB_PATH = "asap_state.db"
SNAPSHOTS_TABLE = "snapshots"
USAGE_EVENTS_TABLE = "usage_events"


def _run_sync(coro: Any) -> Any:
    """Run an async coroutine from sync code (creates new loop or uses existing)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def _snapshot_to_row(snapshot: StateSnapshot) -> tuple[str, str, int, str, int, str]:
    """Serialize StateSnapshot to DB row (task_id, id, version, data, checkpoint, created_at)."""
    data_json = json.dumps(snapshot.data)
    created_at = snapshot.created_at.isoformat()
    checkpoint = 1 if snapshot.checkpoint else 0
    return (
        snapshot.task_id,
        snapshot.id,
        snapshot.version,
        data_json,
        checkpoint,
        created_at,
    )


def _row_to_snapshot(row: tuple[Any, ...]) -> StateSnapshot:
    """Build StateSnapshot from DB row (task_id, id, version, data, checkpoint, created_at)."""
    task_id, id_, version, data_json, checkpoint, created_at_str = row
    data = json.loads(data_json)
    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    return StateSnapshot(
        id=id_,
        task_id=task_id,
        version=version,
        data=data,
        checkpoint=bool(checkpoint),
        created_at=created_at,
    )


def _event_to_row(event: UsageEvent, event_id: str) -> tuple[str, str, str, str, str, str]:
    """Serialize UsageEvent to DB row."""
    metrics_json = event.metrics.model_dump_json()
    ts = event.timestamp.isoformat()
    return (
        event_id,
        event.task_id,
        event.agent_id,
        event.consumer_id,
        metrics_json,
        ts,
    )


def _row_to_event(row: tuple[Any, ...]) -> UsageEvent:
    """Build UsageEvent from DB row."""
    (
        _id,
        task_id,
        agent_id,
        consumer_id,
        metrics_json,
        ts_str,
    ) = row
    metrics = UsageMetrics.model_validate_json(metrics_json)
    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    return UsageEvent(
        task_id=task_id,
        agent_id=agent_id,
        consumer_id=consumer_id,
        metrics=metrics,
        timestamp=ts,
    )


class SQLiteSnapshotStore:
    """SQLite-backed SnapshotStore; state persists across process restarts.

    Uses aiosqlite; sync methods wrap async calls so the store conforms to
    the sync SnapshotStore protocol. Call from sync code only (or use
    a dedicated thread if you must use from async context).
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        """Initialize with database file path."""
        self._db_path = Path(db_path)

    async def _ensure_snapshots_table(self, conn: aiosqlite.Connection) -> None:
        """Create snapshots table if not exists."""
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {SNAPSHOTS_TABLE} (
                task_id TEXT NOT NULL,
                id TEXT NOT NULL,
                version INTEGER NOT NULL,
                data TEXT NOT NULL,
                checkpoint INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (task_id, version)
            )
            """
        )
        await conn.commit()

    async def _save_impl(self, snapshot: StateSnapshot) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_snapshots_table(conn)
            row = _snapshot_to_row(snapshot)
            await conn.execute(
                f"""
                INSERT OR REPLACE INTO {SNAPSHOTS_TABLE}
                (task_id, id, version, data, checkpoint, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            await conn.commit()

    async def _get_impl(
        self,
        task_id: TaskID,
        version: int | None,
    ) -> StateSnapshot | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_snapshots_table(conn)
            if version is not None:
                cursor = await conn.execute(
                    f"""
                    SELECT task_id, id, version, data, checkpoint, created_at
                    FROM {SNAPSHOTS_TABLE}
                    WHERE task_id = ? AND version = ?
                    """,
                    (task_id, version),
                )
                row = await cursor.fetchone()
            else:
                cursor = await conn.execute(
                    f"""
                    SELECT task_id, id, version, data, checkpoint, created_at
                    FROM {SNAPSHOTS_TABLE}
                    WHERE task_id = ?
                    ORDER BY version DESC LIMIT 1
                    """,
                    (task_id,),
                )
                row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_snapshot(tuple(row))

    async def _list_versions_impl(self, task_id: TaskID) -> list[int]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_snapshots_table(conn)
            cursor = await conn.execute(
                f"""
                SELECT version FROM {SNAPSHOTS_TABLE}
                WHERE task_id = ?
                ORDER BY version
                """,
                (task_id,),
            )
            rows = await cursor.fetchall()
            return [r[0] for r in rows]

    async def _delete_impl(
        self,
        task_id: TaskID,
        version: int | None,
    ) -> bool:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_snapshots_table(conn)
            if version is not None:
                cursor = await conn.execute(
                    f"DELETE FROM {SNAPSHOTS_TABLE} WHERE task_id = ? AND version = ?",
                    (task_id, version),
                )
            else:
                cursor = await conn.execute(
                    f"DELETE FROM {SNAPSHOTS_TABLE} WHERE task_id = ?",
                    (task_id,),
                )
            await conn.commit()
            return bool(cursor.rowcount) if cursor.rowcount is not None else False

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot (sync wrapper)."""
        _run_sync(self._save_impl(snapshot))

    def get(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> StateSnapshot | None:
        """Get snapshot by task_id and optional version (sync wrapper)."""
        return cast(StateSnapshot | None, _run_sync(self._get_impl(task_id, version)))

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List versions for task (sync wrapper)."""
        return cast(list[int], _run_sync(self._list_versions_impl(task_id)))

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) (sync wrapper)."""
        return cast(bool, _run_sync(self._delete_impl(task_id, version)))

    async def initialize(self) -> None:
        """Create tables if not exists (call from async context if needed)."""
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_snapshots_table(conn)


class SQLiteMeteringStore:
    """SQLite-backed MeteringStore; usage events persist across restarts."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        """Share db_path with SQLiteSnapshotStore for a single DB file."""
        self._db_path = Path(db_path)

    async def _ensure_usage_table(self, conn: aiosqlite.Connection) -> None:
        """Create usage_events table and index if not exists."""
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {USAGE_EVENTS_TABLE} (
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
            ON {USAGE_EVENTS_TABLE} (agent_id, timestamp)
            """
        )
        await conn.commit()

    async def _record_impl(self, event: UsageEvent) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_usage_table(conn)
            event_id = f"evt_{uuid.uuid4().hex}"
            row = _event_to_row(event, event_id)
            await conn.execute(
                f"""
                INSERT INTO {USAGE_EVENTS_TABLE}
                (id, task_id, agent_id, consumer_id, metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )
            await conn.commit()

    async def _query_impl(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
    ) -> list[UsageEvent]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_usage_table(conn)
            start_s = start.isoformat()
            end_s = end.isoformat()
            cursor = await conn.execute(
                f"""
                SELECT id, task_id, agent_id, consumer_id, metrics, timestamp
                FROM {USAGE_EVENTS_TABLE}
                WHERE agent_id = ? AND timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp
                """,
                (agent_id, start_s, end_s),
            )
            rows = await cursor.fetchall()
            return [_row_to_event(tuple(r)) for r in rows]

    async def _aggregate_impl(self, agent_id: str, period: str) -> UsageAggregate:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_usage_table(conn)
            cursor = await conn.execute(
                f"""
                SELECT
                    SUM(CAST(json_extract(metrics, '$.tokens_in') AS INTEGER) + CAST(json_extract(metrics, '$.tokens_out') AS INTEGER)),
                    SUM(CAST(json_extract(metrics, '$.duration_ms') AS INTEGER)),
                    COUNT(*),
                    SUM(CAST(json_extract(metrics, '$.api_calls') AS INTEGER))
                FROM {USAGE_EVENTS_TABLE}
                WHERE agent_id = ?
                """,
                (agent_id,),
            )
            row = await cursor.fetchone()
            if row is None or (row[0] is None and row[1] is None):
                return UsageAggregate(agent_id=agent_id, period=period)
            total_tokens = row[0] or 0
            total_duration = row[1] or 0
            total_tasks = row[2] or 0
            total_api_calls = row[3] or 0
            return UsageAggregate(
                agent_id=agent_id,
                period=period,
                total_tokens=total_tokens,
                total_duration=total_duration,
                total_tasks=total_tasks,
                total_api_calls=total_api_calls,
            )

    def record(self, event: UsageEvent) -> None:
        """Record a usage event (sync wrapper)."""
        _run_sync(self._record_impl(event))

    def query(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
    ) -> list[UsageEvent]:
        """Query events in range (sync wrapper)."""
        return cast(list[UsageEvent], _run_sync(self._query_impl(agent_id, start, end)))

    def aggregate(self, agent_id: str, period: str) -> UsageAggregate:
        """Aggregate usage for agent (sync wrapper)."""
        return cast(UsageAggregate, _run_sync(self._aggregate_impl(agent_id, period)))

    async def initialize(self) -> None:
        """Create usage_events table if not exists."""
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_usage_table(conn)
