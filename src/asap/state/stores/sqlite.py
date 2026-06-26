"""SQLite-backed SnapshotStore and MeteringStore (persistent, file-based).

Both stores subclass :class:`AsyncSqliteRepository` (v2.5.1 S1): the base owns
aiosqlite connection lifecycle, WAL pragma setup, and idempotent schema init;
this module supplies per-store DDL, SQL, and row mappers. The sync->async bridge
for :class:`SQLiteSnapshotStore` lives in :mod:`state.stores._sync_bridge`.

The canonical ``usage_events`` DDL + :func:`_ensure_usage_events_schema` stay here
because ``asap.economics.storage`` imports the helper directly (state is the lower
layer, so the import direction is acyclic).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import aiosqlite

from asap.models.entities import StateSnapshot
from asap.models.ids import generate_id
from asap.models.types import TaskID
from asap.state.metering import UsageAggregate, UsageEvent, UsageMetrics
from asap.state.stores._sqlite_base import DEFAULT_DB_PATH, AsyncSqliteRepository
from asap.state.stores._sync_bridge import (
    _co_snapshot_delete,
    _co_snapshot_get,
    _co_snapshot_list_versions,
    _co_snapshot_save,
    _run_sync,
)

# Canonical usage_events DDL: single source of truth for the table + BOTH indexes
# (agent and consumer). State is the lower layer, so economics.storage can import
# it without forming an import cycle; both stores call _ensure_usage_events_schema
# so the physical schema is identical regardless of which store initializes first.
_USAGE_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    consumer_id TEXT NOT NULL,
    metrics TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_usage_agent_timestamp
ON usage_events (agent_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_usage_consumer_timestamp
ON usage_events (consumer_id, timestamp);
"""

_SNAPSHOTS_DDL = """
CREATE TABLE IF NOT EXISTS snapshots (
    task_id TEXT NOT NULL,
    id TEXT NOT NULL,
    version INTEGER NOT NULL,
    data TEXT NOT NULL,
    checkpoint INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (task_id, version)
)
"""

_SNAPSHOT_COLS = "task_id, id, version, data, checkpoint, created_at"
_SAVE_SQL = f"INSERT OR REPLACE INTO snapshots ({_SNAPSHOT_COLS}) VALUES (?, ?, ?, ?, ?, ?)"
_GET_BY_VERSION_SQL = f"SELECT {_SNAPSHOT_COLS} FROM snapshots WHERE task_id = ? AND version = ?"  # nosec B608 — _SNAPSHOT_COLS is a hardcoded constant, not user input
_GET_LATEST_SQL = (
    f"SELECT {_SNAPSHOT_COLS} FROM snapshots WHERE task_id = ? ORDER BY version DESC LIMIT 1"  # nosec B608 — _SNAPSHOT_COLS is a hardcoded constant, not user input
)
_LIST_VERSIONS_SQL = "SELECT version FROM snapshots WHERE task_id = ? ORDER BY version"
_DELETE_VERSION_SQL = "DELETE FROM snapshots WHERE task_id = ? AND version = ?"
_DELETE_TASK_SQL = "DELETE FROM snapshots WHERE task_id = ?"

_INSERT_EVENT_SQL = (
    "INSERT INTO usage_events "
    "(id, task_id, agent_id, consumer_id, metrics, timestamp) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)
_QUERY_EVENTS_SQL = (
    "SELECT id, task_id, agent_id, consumer_id, metrics, timestamp "
    "FROM usage_events "
    "WHERE agent_id = ? AND timestamp >= ? AND timestamp <= ? "
    "ORDER BY timestamp"
)
_AGGREGATE_SQL = """
SELECT
    SUM(CAST(json_extract(metrics, '$.tokens_in') AS INTEGER) + CAST(json_extract(metrics, '$.tokens_out') AS INTEGER)),
    SUM(CAST(json_extract(metrics, '$.duration_ms') AS INTEGER)),
    COUNT(*),
    SUM(CAST(json_extract(metrics, '$.api_calls') AS INTEGER))
FROM usage_events
WHERE agent_id = ?
"""


async def _ensure_usage_events_schema(conn: aiosqlite.Connection) -> None:
    """Apply the canonical usage_events schema (table + both indexes), idempotently.

    Economics imports this and calls it with a raw connection; ``SQLiteMeteringStore``
    instead relies on the base's ``_ensure_schema`` (same DDL), so the table is never
    created twice on one instance.
    """
    await conn.executescript(_USAGE_EVENTS_DDL)
    await conn.commit()


def _snapshot_to_row(snapshot: StateSnapshot) -> tuple[str, str, int, str, int, str]:
    return (
        snapshot.task_id,
        snapshot.id,
        snapshot.version,
        json.dumps(snapshot.data),
        1 if snapshot.checkpoint else 0,
        snapshot.created_at.isoformat(),
    )


def _row_to_snapshot(row: tuple[Any, ...]) -> StateSnapshot:
    task_id, id_, version, data_json, checkpoint, created_at_str = row
    return StateSnapshot(
        id=id_,
        task_id=task_id,
        version=version,
        data=json.loads(data_json),
        checkpoint=bool(checkpoint),
        created_at=datetime.fromisoformat(created_at_str.replace("Z", "+00:00")),
    )


def _event_to_row(event: UsageEvent, event_id: str) -> tuple[str, str, str, str, str, str]:
    return (
        event_id,
        event.task_id,
        event.agent_id,
        event.consumer_id,
        event.metrics.model_dump_json(),
        event.timestamp.isoformat(),
    )


def _row_to_event(row: tuple[Any, ...]) -> UsageEvent:
    _id, task_id, agent_id, consumer_id, metrics_json, ts_str = row
    return UsageEvent(
        task_id=task_id,
        agent_id=agent_id,
        consumer_id=consumer_id,
        metrics=UsageMetrics.model_validate_json(metrics_json),
        timestamp=datetime.fromisoformat(ts_str.replace("Z", "+00:00")),
    )


class _SQLiteSnapshotBackend(AsyncSqliteRepository):
    """Shared SQLite snapshot table access (internal).

    The base's idempotent ``_ensure_schema`` replaces the old per-connect
    ``_ensure_snapshots_table`` (both are ``IF NOT EXISTS``).
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        super().__init__(db_path, schema_ddl=_SNAPSHOTS_DDL)

    async def _save_impl(self, snapshot: StateSnapshot) -> None:
        await self.execute(_SAVE_SQL, _snapshot_to_row(snapshot))

    async def _get_impl(
        self,
        task_id: TaskID,
        version: int | None,
    ) -> StateSnapshot | None:
        if version is not None:
            row = await self.fetch_one(_GET_BY_VERSION_SQL, (task_id, version))
        else:
            row = await self.fetch_one(_GET_LATEST_SQL, (task_id,))
        return _row_to_snapshot(row) if row is not None else None

    async def _list_versions_impl(self, task_id: TaskID) -> list[int]:
        rows = await self.fetch_all(_LIST_VERSIONS_SQL, (task_id,))
        return [r[0] for r in rows]

    async def _delete_impl(self, task_id: TaskID, version: int | None) -> bool:
        if version is not None:
            affected = await self.execute(_DELETE_VERSION_SQL, (task_id, version))
        else:
            affected = await self.execute(_DELETE_TASK_SQL, (task_id,))
        return affected > 0

    async def initialize(self) -> None:
        """Create the snapshots table if it does not yet exist."""
        async with self._connect() as conn:
            await self._ensure_schema(conn)


class SQLiteAsyncSnapshotStore(_SQLiteSnapshotBackend):
    """SQLite :class:`~asap.state.snapshot.AsyncSnapshotStore` (``aiosqlite``)."""

    async def save(self, snapshot: StateSnapshot) -> None:
        """Persist a snapshot."""
        await _co_snapshot_save(self, snapshot)

    async def get(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> StateSnapshot | None:
        """Retrieve a snapshot; ``version`` None means latest."""
        return await _co_snapshot_get(self, task_id, version)

    async def list_versions(self, task_id: TaskID) -> list[int]:
        """List version numbers for ``task_id`` in ascending order."""
        return await _co_snapshot_list_versions(self, task_id)

    async def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete one version or all snapshots for ``task_id``."""
        return await _co_snapshot_delete(self, task_id, version)


class SQLiteSnapshotStore(_SQLiteSnapshotBackend):
    """SQLite :class:`~asap.state.snapshot.SnapshotStore`; sync methods use ``_run_sync``."""

    def save(self, snapshot: StateSnapshot) -> None:
        """Save a snapshot."""
        _run_sync(_co_snapshot_save(self, snapshot))

    def get(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> StateSnapshot | None:
        """Get snapshot by task and optional version."""
        return cast(
            StateSnapshot | None,
            _run_sync(_co_snapshot_get(self, task_id, version)),
        )

    def list_versions(self, task_id: TaskID) -> list[int]:
        """List versions for task."""
        return cast(list[int], _run_sync(_co_snapshot_list_versions(self, task_id)))

    def delete(self, task_id: TaskID, version: int | None = None) -> bool:
        """Delete snapshot(s) for task."""
        return cast(bool, _run_sync(_co_snapshot_delete(self, task_id, version)))

    async def save_async(self, snapshot: StateSnapshot) -> None:
        await _co_snapshot_save(self, snapshot)

    async def get_async(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> StateSnapshot | None:
        return await _co_snapshot_get(self, task_id, version)

    async def list_versions_async(self, task_id: TaskID) -> list[int]:
        return await _co_snapshot_list_versions(self, task_id)

    async def delete_async(
        self,
        task_id: TaskID,
        version: int | None = None,
    ) -> bool:
        return await _co_snapshot_delete(self, task_id, version)


class SQLiteMeteringStore(AsyncSqliteRepository):
    """SQLite-backed MeteringStore; usage events persist across restarts.

    ``schema_ddl=_USAGE_EVENTS_DDL`` makes the base's ``_ensure_schema`` install both
    indexes (agent + consumer) once per instance — preserving the S0 fix where the
    state store must not omit the consumer index. ``_ensure_usage_table`` delegates
    to the base so the DDL never runs twice on one instance.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        super().__init__(db_path, schema_ddl=_USAGE_EVENTS_DDL)

    async def _ensure_usage_table(self, conn: aiosqlite.Connection) -> None:
        await self._ensure_schema(conn)

    async def _record_impl(self, event: UsageEvent) -> None:
        event_id = f"evt_{generate_id()}"
        row = _event_to_row(event, event_id)
        await self.execute(_INSERT_EVENT_SQL, row)

    async def _query_impl(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[UsageEvent]:
        query = _QUERY_EVENTS_SQL
        params: list[Any] = [agent_id, start.isoformat(), end.isoformat()]
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        elif offset > 0:
            query += " LIMIT -1 OFFSET ?"
            params.append(offset)
        rows = await self.fetch_all(query, tuple(params))
        return [_row_to_event(r) for r in rows]

    async def _aggregate_impl(self, agent_id: str, period: str) -> UsageAggregate:
        row = await self.fetch_one(_AGGREGATE_SQL, (agent_id,))
        if row is None or (row[0] is None and row[1] is None):
            return UsageAggregate(agent_id=agent_id, period=period)
        return UsageAggregate(
            agent_id=agent_id,
            period=period,
            total_tokens=row[0] or 0,
            total_duration=row[1] or 0,
            total_tasks=row[2] or 0,
            total_api_calls=row[3] or 0,
        )

    async def record(self, event: UsageEvent) -> None:
        """Record a usage event."""
        await self._record_impl(event)

    async def query(
        self,
        agent_id: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[UsageEvent]:
        """Query events in range."""
        if offset < 0:
            raise ValueError("offset must be non-negative")
        return await self._query_impl(agent_id, start, end, limit, offset)

    async def aggregate(self, agent_id: str, period: str) -> UsageAggregate:
        """Aggregate usage for agent."""
        return await self._aggregate_impl(agent_id, period)

    async def initialize(self) -> None:
        """Create usage_events table if not exists."""
        async with self._connect() as conn:
            await self._ensure_usage_table(conn)


__all__ = [
    "DEFAULT_DB_PATH",
    "SQLiteAsyncSnapshotStore",
    "SQLiteMeteringStore",
    "SQLiteSnapshotStore",
    "_USAGE_EVENTS_DDL",
    "_ensure_usage_events_schema",
]
