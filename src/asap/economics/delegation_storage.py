"""Delegation revocation storage (v1.3).

Persistent storage for revoked delegation token IDs. Used to enforce
immediate revocation: validation checks DelegationStorage.is_revoked(token_id)
before accepting a delegation token.

Tables: ``revocations`` (id, revoked_at, reason) and ``issued_delegations``
(id, delegator_urn, delegate_urn, created_at). Both persist across restarts
and share the canonical SQLite plumbing from :class:`AsyncSqliteRepository`.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiosqlite

from asap.state.stores import DEFAULT_DB_PATH, AsyncSqliteRepository, parse_iso
from asap.state.stores._sqlite_base import _build_sql_in_placeholders

# Maximum cascade depth to prevent stack overflow / DoS from circular chains.
_MAX_CASCADE_DEPTH = 50

_SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS revocations (
    id TEXT PRIMARY KEY,
    revoked_at TEXT NOT NULL,
    reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_revocations_revoked_at
    ON revocations (revoked_at);
CREATE TABLE IF NOT EXISTS issued_delegations (
    id TEXT PRIMARY KEY,
    delegator_urn TEXT NOT NULL,
    delegate_urn TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_issued_delegator
    ON issued_delegations (delegator_urn);
"""


@dataclass(frozen=True)
class IssuedSummary:
    id: str
    delegate_urn: str | None
    created_at: datetime


@dataclass(frozen=True)
class TokenDetail:
    id: str
    delegator_urn: str
    delegate_urn: str | None
    created_at: datetime
    is_revoked: bool
    revoked_at: datetime | None


@runtime_checkable
class DelegationStorage(Protocol):
    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None: ...
    async def is_revoked(self, token_id: str) -> bool: ...
    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None: ...
    async def get_delegator(self, token_id: str) -> str | None: ...
    async def get_delegate(self, token_id: str) -> str | None: ...
    async def list_token_ids_issued_by(self, delegator_urn: str) -> list[str]: ...
    async def list_issued_summaries(self, delegator_urn: str) -> list[IssuedSummary]: ...
    async def get_issued_at(self, token_id: str) -> datetime | None: ...
    async def get_revoked_at(self, token_id: str) -> datetime | None: ...
    async def revoke_cascade(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None: ...
    async def are_revoked(self, token_ids: list[str]) -> dict[str, bool]: ...
    async def get_token_detail(self, token_id: str) -> TokenDetail | None: ...


class DelegationStorageBase(ABC):
    @abstractmethod
    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def is_revoked(self, token_id: str) -> bool: ...

    @abstractmethod
    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None: ...

    @abstractmethod
    async def get_delegator(self, token_id: str) -> str | None: ...

    @abstractmethod
    async def get_delegate(self, token_id: str) -> str | None: ...

    @abstractmethod
    async def list_token_ids_issued_by(self, delegator_urn: str) -> list[str]: ...

    @abstractmethod
    async def list_issued_summaries(self, delegator_urn: str) -> list[IssuedSummary]: ...

    @abstractmethod
    async def get_issued_at(self, token_id: str) -> datetime | None: ...

    @abstractmethod
    async def get_revoked_at(self, token_id: str) -> datetime | None: ...

    @abstractmethod
    async def are_revoked(self, token_ids: list[str]) -> dict[str, bool]: ...

    @abstractmethod
    async def get_token_detail(self, token_id: str) -> TokenDetail | None: ...

    async def revoke_cascade(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        """Revoke a token and all child delegations (iterative BFS).

        Delegates the tree-walk + revocation to :meth:`_revoke_cascade_atomic`
        so each backend controls its own transaction/lock boundary. Public
        signature is stable.
        """
        await self._revoke_cascade_atomic(token_id, reason)

    async def _revoke_cascade_atomic(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        """Default BFS cascade using public per-id methods.

        Uses a visited set to handle circular delegation chains and a
        depth limit (_MAX_CASCADE_DEPTH) to prevent DoS. Subclasses override
        this to wrap the walk in a single transaction/lock for atomicity.
        """
        visited: set[str] = set()
        stack: list[tuple[str, int]] = [(token_id, 0)]
        while stack:
            tid, depth = stack.pop()
            if tid in visited or depth > _MAX_CASCADE_DEPTH:
                continue
            visited.add(tid)
            delegate_urn = await self.get_delegate(tid)
            if delegate_urn:
                child_ids = await self.list_token_ids_issued_by(delegate_urn)
                for child_id in child_ids:
                    stack.append((child_id, depth + 1))
            await self.revoke(tid, reason)


class InMemoryDelegationStorage(DelegationStorageBase):
    """In-memory revocation store for tests. Not persistent across restarts.

    Async-safe via ``asyncio.Lock`` (parity with ``InMemorySLAStorage`` /
    ``InMemoryMeteringStorage``). The lock is held across the whole cascade so
    concurrent ``register_issued`` cannot interleave and lose/split children.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._revoked: dict[str, tuple[datetime, str | None]] = {}
        self._issued: dict[str, tuple[str, str | None, datetime]] = {}

    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        async with self._lock:
            self._revoked[token_id] = (datetime.now(timezone.utc), reason)

    async def is_revoked(self, token_id: str) -> bool:
        # Read-only snapshot; a concurrent writer cannot corrupt a dict lookup
        # under the GIL, so no lock is required here.
        return token_id in self._revoked

    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        async with self._lock:
            self._issued[token_id] = (delegator_urn, delegate_urn, now)

    async def get_delegator(self, token_id: str) -> str | None:
        entry = self._issued.get(token_id)
        return entry[0] if entry else None

    async def get_delegate(self, token_id: str) -> str | None:
        entry = self._issued.get(token_id)
        return entry[1] if entry and entry[1] is not None else None

    async def list_token_ids_issued_by(self, delegator_urn: str) -> list[str]:
        return [tid for tid, (d, _, _) in self._issued.items() if d == delegator_urn]

    async def list_issued_summaries(self, delegator_urn: str) -> list[IssuedSummary]:
        return [
            IssuedSummary(id=tid, delegate_urn=entry[1], created_at=entry[2])
            for tid, entry in self._issued.items()
            if entry[0] == delegator_urn
        ]

    async def get_issued_at(self, token_id: str) -> datetime | None:
        entry = self._issued.get(token_id)
        return entry[2] if entry else None

    async def get_revoked_at(self, token_id: str) -> datetime | None:
        t = self._revoked.get(token_id)
        return t[0] if t else None

    async def are_revoked(self, token_ids: list[str]) -> dict[str, bool]:
        return {tid: tid in self._revoked for tid in token_ids}

    async def get_token_detail(self, token_id: str) -> TokenDetail | None:
        entry = self._issued.get(token_id)
        if not entry:
            return None
        rev = self._revoked.get(token_id)
        return TokenDetail(
            id=token_id,
            delegator_urn=entry[0],
            delegate_urn=entry[1],
            created_at=entry[2],
            is_revoked=rev is not None,
            revoked_at=rev[0] if rev else None,
        )

    async def _revoke_cascade_atomic(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        """Hold the lock across the whole BFS walk so concurrent mutations
        (``register_issued`` / ``revoke``) cannot interleave and split the
        cascade. The tree-walk reuses the base BFS logic on a consistent
        in-memory snapshot.
        """
        async with self._lock:
            visited: set[str] = set()
            stack: list[tuple[str, int]] = [(token_id, 0)]
            while stack:
                tid, depth = stack.pop()
                if tid in visited or depth > _MAX_CASCADE_DEPTH:
                    continue
                visited.add(tid)
                entry = self._issued.get(tid)
                delegate_urn = entry[1] if entry and entry[1] is not None else None
                if delegate_urn:
                    for child_id, (d, _, _) in self._issued.items():
                        if d == delegate_urn:
                            stack.append((child_id, depth + 1))
                self._revoked[tid] = (datetime.now(timezone.utc), reason)


class SQLiteDelegationStorage(AsyncSqliteRepository, DelegationStorageBase):
    """SQLite-backed revocation storage. Survives restarts.

    Subclasses :class:`AsyncSqliteRepository` for connection lifecycle, WAL
    pragmas, idempotent schema init, and the ``transaction()`` context manager
    used by the atomic cascade. Shares the same DB file as metering/state when
    using the default path.
    """

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        super().__init__(db_path, schema_ddl=_SCHEMA_DDL)
        # Guard for the one-time delegate_urn back-migration; the base's
        # ``_initialized`` only covers the CREATE TABLE/INDEX DDL.
        self._migration_done = False

    async def _ensure_schema(self, conn: aiosqlite.Connection) -> None:
        """Run the shared DDL, then back-migrate ``delegate_urn`` once.

        ``executescript`` cannot mix ``PRAGMA table_info`` with a conditional
        ``ALTER``, so the CREATE/INDEX DDL goes through the base and the
        legacy-column migration runs once under the same per-instance lock.
        """
        await super()._ensure_schema(conn)
        if self._migration_done:
            return
        async with self._init_lock:
            if self._migration_done:
                return
            await self._migrate_issued_delegations(conn)
            self._migration_done = True

    @staticmethod
    async def _migrate_issued_delegations(conn: aiosqlite.Connection) -> None:
        """Add ``delegate_urn`` to legacy DBs that predate the column."""
        cursor = await conn.execute("PRAGMA table_info(issued_delegations)")
        rows = await cursor.fetchall()
        columns = [row[1] for row in rows] if rows else []
        if "delegate_urn" not in columns:
            await conn.execute("ALTER TABLE issued_delegations ADD COLUMN delegate_urn TEXT")
            await conn.commit()

    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.execute(
            "INSERT OR REPLACE INTO revocations (id, revoked_at, reason) VALUES (?, ?, ?)",
            (token_id, now, reason),
        )

    async def _revoke_on_conn(
        self,
        conn: aiosqlite.Connection,
        token_id: str,
        reason: str | None,
    ) -> None:
        """Insert a revocation row on a shared connection (no commit).

        Used by :meth:`_revoke_cascade_atomic` so every per-id revoke in a
        cascade shares one transaction boundary owned by ``self.transaction()``.
        """
        now = datetime.now(timezone.utc).isoformat()
        await conn.execute(
            "INSERT OR REPLACE INTO revocations (id, revoked_at, reason) VALUES (?, ?, ?)",
            (token_id, now, reason),
        )

    async def _revoke_cascade_atomic(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        """Single-transaction cascade using the shared ``transaction()`` base.

        Walks the delegation tree with conn-scoped reads and inserts every
        revocation on that one connection. The base commits on success and
        rolls back on any exception, so a mid-cascade crash leaves no partial
        revocation state (the S0 B1 atomicity invariant).
        """
        async with self.transaction() as conn:
            visited: set[str] = set()
            stack: list[tuple[str, int]] = [(token_id, 0)]
            while stack:
                tid, depth = stack.pop()
                if tid in visited or depth > _MAX_CASCADE_DEPTH:
                    continue
                visited.add(tid)
                cursor = await conn.execute(
                    "SELECT delegate_urn FROM issued_delegations WHERE id = ?",
                    (tid,),
                )
                row = await cursor.fetchone()
                delegate_urn = str(row[0]) if row and row[0] else None
                if delegate_urn:
                    cursor = await conn.execute(
                        "SELECT id FROM issued_delegations WHERE delegator_urn = ?",
                        (delegate_urn,),
                    )
                    for child_row in await cursor.fetchall():
                        stack.append((str(child_row[0]), depth + 1))
                await self._revoke_on_conn(conn, tid, reason)

    async def is_revoked(self, token_id: str) -> bool:
        row = await self.fetch_one("SELECT 1 FROM revocations WHERE id = ?", (token_id,))
        return row is not None

    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.execute(
            "INSERT OR REPLACE INTO issued_delegations "
            "(id, delegator_urn, delegate_urn, created_at) VALUES (?, ?, ?, ?)",
            (token_id, delegator_urn, delegate_urn, now),
        )

    async def get_delegator(self, token_id: str) -> str | None:
        row = await self.fetch_one(
            "SELECT delegator_urn FROM issued_delegations WHERE id = ?", (token_id,)
        )
        return str(row[0]) if row and row[0] else None

    async def get_delegate(self, token_id: str) -> str | None:
        row = await self.fetch_one(
            "SELECT delegate_urn FROM issued_delegations WHERE id = ?", (token_id,)
        )
        return str(row[0]) if row and row[0] else None

    async def list_token_ids_issued_by(self, delegator_urn: str) -> list[str]:
        rows = await self.fetch_all(
            "SELECT id FROM issued_delegations WHERE delegator_urn = ?", (delegator_urn,)
        )
        return [str(r[0]) for r in rows]

    async def list_issued_summaries(self, delegator_urn: str) -> list[IssuedSummary]:
        rows = await self.fetch_all(
            "SELECT id, delegate_urn, created_at FROM issued_delegations "
            "WHERE delegator_urn = ? ORDER BY created_at DESC",
            (delegator_urn,),
        )
        return [
            IssuedSummary(
                id=str(r[0]),
                delegate_urn=str(r[1]) if r[1] else None,
                created_at=parse_iso(str(r[2])) or datetime.now(timezone.utc),
            )
            for r in rows
        ]

    async def get_issued_at(self, token_id: str) -> datetime | None:
        row = await self.fetch_one(
            "SELECT created_at FROM issued_delegations WHERE id = ?", (token_id,)
        )
        return parse_iso(str(row[0]) if row and row[0] else None)

    async def get_revoked_at(self, token_id: str) -> datetime | None:
        row = await self.fetch_one("SELECT revoked_at FROM revocations WHERE id = ?", (token_id,))
        return parse_iso(str(row[0]) if row and row[0] else None)

    async def are_revoked(self, token_ids: list[str]) -> dict[str, bool]:
        """Batch revocation check in a single query."""
        if not token_ids:
            return {}
        # ``placeholders`` is built from ``len(token_ids)`` and can only contain ``?`` and
        # ``,``; every value comes through the tuple passed to ``execute``. SQLite does
        # not support binding a list to a single parameter, so dynamic SQL is required.
        placeholders = _build_sql_in_placeholders(len(token_ids))
        rows = await self.fetch_all(
            f"SELECT id FROM revocations WHERE id IN ({placeholders})",  # nosec B608 - placeholders asserted to be `?,?,…`; values parameterized
            tuple(token_ids),
        )
        revoked_ids = {str(r[0]) for r in rows}
        return {tid: tid in revoked_ids for tid in token_ids}

    async def get_token_detail(self, token_id: str) -> TokenDetail | None:
        """Fetch all token details in a single connection (LEFT JOIN)."""
        row = await self.fetch_one(
            "SELECT i.id, i.delegator_urn, i.delegate_urn, i.created_at, r.revoked_at "
            "FROM issued_delegations i "
            "LEFT JOIN revocations r ON i.id = r.id WHERE i.id = ?",
            (token_id,),
        )
        if not row:
            return None
        return TokenDetail(
            id=str(row[0]),
            delegator_urn=str(row[1]),
            delegate_urn=str(row[2]) if row[2] else None,
            created_at=parse_iso(str(row[3])) or datetime.now(timezone.utc),
            is_revoked=row[4] is not None,
            revoked_at=parse_iso(str(row[4])) if row[4] else None,
        )
