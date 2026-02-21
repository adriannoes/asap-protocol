"""Delegation revocation storage (v1.3).

Persistent storage for revoked delegation token IDs. Used to enforce
immediate revocation: validation checks DelegationStorage.is_revoked(token_id)
before accepting a delegation token.

Table: revocations (id, revoked_at, reason). Persists across restarts.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiosqlite


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


# Same default DB path as metering for a single shared SQLite file.
_DEFAULT_DB_PATH = "asap_state.db"
_REVOCATIONS_TABLE = "revocations"
_ISSUED_TABLE = "issued_delegations"


# Maximum cascade depth to prevent stack overflow / DoS from circular chains.
_MAX_CASCADE_DEPTH = 50


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

        Uses a visited set to handle circular delegation chains and a
        depth limit (_MAX_CASCADE_DEPTH) to prevent DoS.
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
    """In-memory revocation store for tests. Not persistent across restarts."""

    def __init__(self) -> None:
        self._revoked: dict[str, tuple[datetime, str | None]] = {}
        self._issued: dict[str, tuple[str, str | None, datetime]] = {}

    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        self._revoked[token_id] = (datetime.now(timezone.utc), reason)

    async def is_revoked(self, token_id: str) -> bool:
        return token_id in self._revoked

    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
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


class SQLiteDelegationStorage(DelegationStorageBase):
    """SQLite-backed revocation storage. Survives restarts.

    Uses table revocations (id TEXT PRIMARY KEY, revoked_at TEXT, reason TEXT).
    Shares the same DB file as metering/state when using the default path.
    """

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._initialized = False

    async def _ensure_tables(self, conn: aiosqlite.Connection) -> None:
        if self._initialized:
            return
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_REVOCATIONS_TABLE} (
                id TEXT PRIMARY KEY,
                revoked_at TEXT NOT NULL,
                reason TEXT
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_revocations_revoked_at
            ON {_REVOCATIONS_TABLE} (revoked_at)
            """
        )
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_ISSUED_TABLE} (
                id TEXT PRIMARY KEY,
                delegator_urn TEXT NOT NULL,
                delegate_urn TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        await conn.execute(
            f"""
            CREATE INDEX IF NOT EXISTS idx_issued_delegator
            ON {_ISSUED_TABLE} (delegator_urn)
            """
        )
        # Migrate existing DBs: add delegate_urn if missing (for cascade).
        cursor = await conn.execute(f"PRAGMA table_info({_ISSUED_TABLE})")
        rows = await cursor.fetchall()
        columns = [row[1] for row in rows] if rows else []
        if "delegate_urn" not in columns:
            await conn.execute(f"ALTER TABLE {_ISSUED_TABLE} ADD COLUMN delegate_urn TEXT")
        await conn.commit()
        self._initialized = True

    async def revoke(
        self,
        token_id: str,
        reason: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            await conn.execute(
                f"""
                INSERT OR REPLACE INTO {_REVOCATIONS_TABLE} (id, revoked_at, reason)
                VALUES (?, ?, ?)
                """,
                (token_id, now, reason),
            )
            await conn.commit()

    async def is_revoked(self, token_id: str) -> bool:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT 1 FROM {_REVOCATIONS_TABLE} WHERE id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
            return row is not None

    async def register_issued(
        self,
        token_id: str,
        delegator_urn: str,
        delegate_urn: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            await conn.execute(
                f"""
                INSERT OR REPLACE INTO {_ISSUED_TABLE} (id, delegator_urn, delegate_urn, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (token_id, delegator_urn, delegate_urn, now),
            )
            await conn.commit()

    async def get_delegator(self, token_id: str) -> str | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT delegator_urn FROM {_ISSUED_TABLE} WHERE id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    async def get_delegate(self, token_id: str) -> str | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT delegate_urn FROM {_ISSUED_TABLE} WHERE id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    async def list_token_ids_issued_by(self, delegator_urn: str) -> list[str]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT id FROM {_ISSUED_TABLE} WHERE delegator_urn = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (delegator_urn,),
            )
            rows = await cursor.fetchall()
            return [str(r[0]) for r in rows] if rows else []

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if value is None or not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None

    async def list_issued_summaries(self, delegator_urn: str) -> list[IssuedSummary]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT id, delegate_urn, created_at FROM {_ISSUED_TABLE}
                WHERE delegator_urn = ?
                ORDER BY created_at DESC
                """,  # nosec B608 - table name is module constant, values parameterized
                (delegator_urn,),
            )
            rows = await cursor.fetchall()
        return [
            IssuedSummary(
                id=str(r[0]),
                delegate_urn=str(r[1]) if r[1] else None,
                created_at=self._parse_iso_datetime(str(r[2])) or datetime.now(timezone.utc),
            )
            for r in rows
        ]

    async def get_issued_at(self, token_id: str) -> datetime | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT created_at FROM {_ISSUED_TABLE} WHERE id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
        return self._parse_iso_datetime(str(row[0]) if row and row[0] else None)

    async def get_revoked_at(self, token_id: str) -> datetime | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT revoked_at FROM {_REVOCATIONS_TABLE} WHERE id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
        return self._parse_iso_datetime(str(row[0]) if row and row[0] else None)

    async def are_revoked(self, token_ids: list[str]) -> dict[str, bool]:
        """Batch revocation check in a single query."""
        if not token_ids:
            return {}
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            placeholders = ",".join("?" for _ in token_ids)
            cursor = await conn.execute(
                f"SELECT id FROM {_REVOCATIONS_TABLE} WHERE id IN ({placeholders})",  # nosec B608
                token_ids,
            )
            revoked_rows = await cursor.fetchall()
        revoked_ids = {str(r[0]) for r in revoked_rows}
        return {tid: tid in revoked_ids for tid in token_ids}

    async def get_token_detail(self, token_id: str) -> TokenDetail | None:
        """Fetch all token details in a single connection (LEFT JOIN)."""
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_tables(conn)
            cursor = await conn.execute(
                f"""
                SELECT i.id, i.delegator_urn, i.delegate_urn, i.created_at,
                       r.revoked_at
                FROM {_ISSUED_TABLE} i
                LEFT JOIN {_REVOCATIONS_TABLE} r ON i.id = r.id
                WHERE i.id = ?
                """,  # nosec B608 - table name is module constant, values parameterized
                (token_id,),
            )
            row = await cursor.fetchone()
        if not row:
            return None
        return TokenDetail(
            id=str(row[0]),
            delegator_urn=str(row[1]),
            delegate_urn=str(row[2]) if row[2] else None,
            created_at=self._parse_iso_datetime(str(row[3])) or datetime.now(timezone.utc),
            is_revoked=row[4] is not None,
            revoked_at=self._parse_iso_datetime(str(row[4])) if row[4] else None,
        )
