"""Tamper-evident audit logging with SHA-256 hash chain.

Provides append-only audit log storage where each entry's hash depends on the
previous entry, making any retroactive modification detectable via
``verify_chain()``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from asap.models.base import ASAPBaseModel
from asap.models.ids import generate_id


class AuditEntry(ASAPBaseModel):
    """A single tamper-evident audit log entry.

    Each entry stores a SHA-256 hash of (prev_hash + timestamp + operation +
    details), forming an append-only chain that detects retroactive tampering.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )

    id: str = Field(default_factory=generate_id)
    timestamp: datetime
    operation: str
    agent_urn: str
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = Field(default="")
    hash: str = Field(default="")


def compute_entry_hash(
    prev_hash: str,
    timestamp: datetime,
    operation: str,
    details: dict[str, Any],
) -> str:
    """Compute SHA-256 hash for audit chain integrity.

    The canonical form is ``prev_hash|ISO-timestamp|operation|sorted-JSON-details``.

    Args:
        prev_hash: Hash of the previous entry (empty string for first).
        timestamp: Entry creation time.
        operation: Operation identifier (e.g. ``"task.request"``).
        details: Arbitrary metadata dictionary.

    Returns:
        Hex-encoded SHA-256 digest.
    """
    canonical = (
        f"{prev_hash}|{timestamp.isoformat()}|{operation}"
        f"|{json.dumps(details, sort_keys=True, default=str)}"
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


@runtime_checkable
class AuditStore(Protocol):
    """Protocol for tamper-evident audit log storage."""

    async def append(self, entry: AuditEntry) -> AuditEntry:
        """Append an entry, sealing it with a hash chain link."""
        ...

    async def query(
        self,
        agent_urn: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Query entries with optional filters."""
        ...

    async def verify_chain(self) -> bool:
        """Verify hash chain integrity for all entries."""
        ...

    async def count(self) -> int:
        """Return total number of entries."""
        ...


class InMemoryAuditStore:
    """In-memory audit store for testing and development."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._lock = asyncio.Lock()

    async def append(self, entry: AuditEntry) -> AuditEntry:
        """Append an entry, computing and linking its hash to the chain."""
        async with self._lock:
            prev_hash = self._entries[-1].hash if self._entries else ""
            computed_hash = compute_entry_hash(
                prev_hash, entry.timestamp, entry.operation, entry.details
            )
            sealed = entry.model_copy(update={"prev_hash": prev_hash, "hash": computed_hash})
            self._entries.append(sealed)
        return sealed

    async def query(
        self,
        agent_urn: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Query entries with optional agent/time filters and pagination."""
        results = list(self._entries)
        if agent_urn:
            results = [e for e in results if e.agent_urn == agent_urn]
        if start:
            results = [e for e in results if e.timestamp >= start]
        if end:
            results = [e for e in results if e.timestamp <= end]
        return results[offset : offset + limit]

    async def verify_chain(self) -> bool:
        """Walk the full chain and verify every hash link."""
        prev_hash = ""
        for entry in self._entries:
            expected = compute_entry_hash(
                prev_hash, entry.timestamp, entry.operation, entry.details
            )
            if entry.hash != expected or entry.prev_hash != prev_hash:
                return False
            prev_hash = entry.hash
        return True

    async def count(self) -> int:
        """Return total number of stored entries."""
        return len(self._entries)


class SQLiteAuditStore:
    """SQLite-backed audit store with hash chain verification.

    Uses ``aiosqlite`` for async access. The table is lazily created on first
    use so the store can be instantiated synchronously.

    For ``:memory:`` databases a single persistent connection is kept alive
    (because each ``aiosqlite.connect(":memory:")`` creates a *new* empty
    database).  File-backed databases use per-call connections.  An
    ``asyncio.Lock`` serialises all writes so the hash-chain stays linear.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._initialized = False
        self._persistent_conn: Any | None = None

    async def _get_connection(self) -> Any:
        """Return an open ``aiosqlite`` connection.

        For ``:memory:`` databases the same connection is reused for the
        lifetime of the store; for file-backed databases a fresh connection
        is returned (caller must close it).
        """
        import aiosqlite

        if self._db_path == ":memory:":
            if self._persistent_conn is None:
                self._persistent_conn = await aiosqlite.connect(":memory:")
            return self._persistent_conn
        return await aiosqlite.connect(self._db_path)

    async def _release_connection(self, conn: Any) -> None:
        """Close *conn* unless it is the persistent in-memory connection."""
        if conn is not self._persistent_conn:
            await conn.close()

    async def _ensure_table(self, conn: Any) -> None:
        """Create the audit_log table and indexes if they don't exist yet."""
        if self._initialized:
            return
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                operation TEXT NOT NULL,
                agent_urn TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}',
                prev_hash TEXT NOT NULL DEFAULT '',
                hash TEXT NOT NULL DEFAULT ''
            )
            """
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_urn ON audit_log(agent_urn)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(timestamp)")
        await conn.commit()
        self._initialized = True

    async def append(self, entry: AuditEntry) -> AuditEntry:
        """Append an entry, linking it to the last stored hash."""
        async with self._lock:
            conn = await self._get_connection()
            try:
                await self._ensure_table(conn)
                cursor = await conn.execute(
                    "SELECT hash FROM audit_log ORDER BY rowid DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                prev_hash = row[0] if row else ""

                computed_hash = compute_entry_hash(
                    prev_hash, entry.timestamp, entry.operation, entry.details
                )
                sealed = entry.model_copy(update={"prev_hash": prev_hash, "hash": computed_hash})

                await conn.execute(
                    """
                    INSERT INTO audit_log (id, timestamp, operation, agent_urn, details, prev_hash, hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sealed.id,
                        sealed.timestamp.isoformat(),
                        sealed.operation,
                        sealed.agent_urn,
                        json.dumps(sealed.details, sort_keys=True, default=str),
                        sealed.prev_hash,
                        sealed.hash,
                    ),
                )
                await conn.commit()
            finally:
                await self._release_connection(conn)
        return sealed

    async def query(
        self,
        agent_urn: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Query entries with optional filters, ordered by insertion order."""
        clauses: list[str] = []
        params: list[str | int] = []
        if agent_urn:
            clauses.append("agent_urn = ?")
            params.append(agent_urn)
        if start:
            clauses.append("timestamp >= ?")
            params.append(start.isoformat())
        if end:
            clauses.append("timestamp <= ?")
            params.append(end.isoformat())

        select_from = (
            "SELECT id, timestamp, operation, agent_urn, details, prev_hash, hash FROM audit_log"
        )
        where_sql = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = select_from + where_sql + " ORDER BY rowid LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        entries: list[AuditEntry] = []
        conn = await self._get_connection()
        try:
            await self._ensure_table(conn)
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            for row in rows:
                entries.append(
                    AuditEntry(
                        id=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        operation=row[2],
                        agent_urn=row[3],
                        details=json.loads(row[4]),
                        prev_hash=row[5],
                        hash=row[6],
                    )
                )
        finally:
            await self._release_connection(conn)
        return entries

    async def verify_chain(self) -> bool:
        """Verify every hash link in insertion order."""
        prev_hash = ""
        conn = await self._get_connection()
        try:
            await self._ensure_table(conn)
            cursor = await conn.execute(
                "SELECT timestamp, operation, details, prev_hash, hash "
                "FROM audit_log ORDER BY rowid"
            )
            rows = await cursor.fetchall()
            for row in rows:
                ts = datetime.fromisoformat(row[0])
                operation = row[1]
                details = json.loads(row[2])
                stored_prev = row[3]
                stored_hash = row[4]

                expected = compute_entry_hash(prev_hash, ts, operation, details)
                if stored_hash != expected or stored_prev != prev_hash:
                    return False
                prev_hash = stored_hash
        finally:
            await self._release_connection(conn)
        return True

    async def count(self) -> int:
        """Return total number of stored entries."""
        conn = await self._get_connection()
        try:
            await self._ensure_table(conn)
            cursor = await conn.execute("SELECT COUNT(*) FROM audit_log")
            row = await cursor.fetchone()
            return row[0] if row else 0
        finally:
            await self._release_connection(conn)
