"""WebAuthn credential storage backends (optional ``asap-protocol[webauthn]`` extra).

Split out of :mod:`asap.auth.webauthn` (Sprint S3) because the storage backend
and the ceremony spec have different change drivers: stores evolve with
persistence/operational needs (new backends, schema migrations) while the
ceremony follows the WebAuthn spec. Keeping them apart lets a deployment swap
the store without touching ceremony code.

This module owns:
    WebAuthnCredentialRecord  — stored credential material dataclass
    WebAuthnCredentialStore   — Protocol any backend must satisfy
    InMemoryWebAuthnCredentialStore  — per-process asyncio-locked backend
    SQLiteWebAuthnCredentialStore    — file-backed backend (aiosqlite)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

import aiosqlite


@dataclass(frozen=True, slots=True)
class WebAuthnCredentialRecord:
    """Stored credential material for a WebAuthn public key credential."""

    credential_id: bytes
    public_key: bytes
    sign_count: int


@runtime_checkable
class WebAuthnCredentialStore(Protocol):
    """Persist WebAuthn credentials keyed by host and credential id."""

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        """Insert or replace a credential for ``host_id``."""

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        """Return the stored row, or ``None`` if missing."""

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        """Persist the authenticator sign counter after a successful assertion."""

    async def list_credentials(self, host_id: str) -> list[bytes]:
        """Return credential ids for ``host_id``."""


class InMemoryWebAuthnCredentialStore:
    """In-memory :class:`WebAuthnCredentialStore` (asyncio.Lock, per-process only)."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._rows: dict[tuple[str, bytes], WebAuthnCredentialRecord] = {}

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        async with self._lock:
            self._rows[(host_id, credential_id)] = WebAuthnCredentialRecord(
                credential_id=credential_id,
                public_key=public_key,
                sign_count=sign_count,
            )

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        async with self._lock:
            return self._rows.get((host_id, credential_id))

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        async with self._lock:
            key = (host_id, credential_id)
            row = self._rows.get(key)
            if row is None:
                msg = f"no credential for host_id={host_id!r} credential_id={credential_id!r}"
                raise KeyError(msg)
            self._rows[key] = WebAuthnCredentialRecord(
                credential_id=row.credential_id,
                public_key=row.public_key,
                sign_count=new_count,
            )

    async def list_credentials(self, host_id: str) -> list[bytes]:
        async with self._lock:
            return [cid for (hid, cid) in self._rows if hid == host_id]


class SQLiteWebAuthnCredentialStore:
    """File-backed :class:`WebAuthnCredentialStore` using SQLite (``aiosqlite``)."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(Path(db_path))

    async def _ensure_schema(self, conn: aiosqlite.Connection) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webauthn_credentials (
                host_id TEXT NOT NULL,
                credential_id BLOB NOT NULL,
                public_key BLOB NOT NULL,
                sign_count INTEGER NOT NULL,
                PRIMARY KEY (host_id, credential_id)
            )
            """
        )

    async def save_credential(
        self,
        host_id: str,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            await conn.execute(
                """
                INSERT OR REPLACE INTO webauthn_credentials
                    (host_id, credential_id, public_key, sign_count)
                VALUES (?, ?, ?, ?)
                """,
                (host_id, credential_id, public_key, sign_count),
            )
            await conn.commit()

    async def get_credential(
        self,
        host_id: str,
        credential_id: bytes,
    ) -> WebAuthnCredentialRecord | None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                """
                SELECT credential_id, public_key, sign_count
                FROM webauthn_credentials
                WHERE host_id = ? AND credential_id = ?
                """,
                (host_id, credential_id),
            )
            row = await cur.fetchone()
            if row is None:
                return None
            return WebAuthnCredentialRecord(
                credential_id=row["credential_id"],
                public_key=row["public_key"],
                sign_count=int(row["sign_count"]),
            )

    async def update_sign_count(
        self,
        host_id: str,
        credential_id: bytes,
        new_count: int,
    ) -> None:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            cur = await conn.execute(
                """
                UPDATE webauthn_credentials
                SET sign_count = ?
                WHERE host_id = ? AND credential_id = ?
                """,
                (new_count, host_id, credential_id),
            )
            await conn.commit()
            if cur.rowcount != 1:
                msg = f"no credential for host_id={host_id!r} credential_id={credential_id!r}"
                raise KeyError(msg)

    async def list_credentials(self, host_id: str) -> list[bytes]:
        async with aiosqlite.connect(self._db_path) as conn:
            await self._ensure_schema(conn)
            cur = await conn.execute(
                """
                SELECT credential_id FROM webauthn_credentials
                WHERE host_id = ?
                """,
                (host_id,),
            )
            rows = await cur.fetchall()
            return [r[0] for r in rows]


__all__ = [
    "InMemoryWebAuthnCredentialStore",
    "SQLiteWebAuthnCredentialStore",
    "WebAuthnCredentialRecord",
    "WebAuthnCredentialStore",
]
