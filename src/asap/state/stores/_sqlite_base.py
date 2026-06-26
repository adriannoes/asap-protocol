"""Shared SQLite repository base for ASAP persistent stores (v2.5.1 S1).

One source of truth for aiosqlite connection lifecycle, WAL pragma setup,
idempotent schema init, WHERE-clause assembly, ISO timestamp parsing, and
IN-clause placeholders. Subclasses supply ``schema_ddl`` and per-method SQL.

The per-path WAL lock + LRU ``journal_mode`` metadata below serialize concurrent
openings on the same DB file (``journal_mode=WAL`` raced before the lock).

Example:
    >>> repo = AsyncSqliteRepository(":memory:", schema_ddl=DDL)
    >>> await repo.execute("INSERT INTO t(a) VALUES (?)", (1,))
    1
    >>> await repo.fetch_one("SELECT a FROM t")
    (1,)
"""

from __future__ import annotations

import asyncio
import threading
import weakref
from collections import OrderedDict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

# Single canonical default DB path (deletes the 5 copies across stores).
DEFAULT_DB_PATH = "asap_state.db"

# Per-DB asyncio lock: concurrent openings raced on journal_mode=WAL before the
# lock existed. Weak values drop entries when locks are collectable (limits
# growth in long test runs that spin many tmp_path DBs).
_PRAGMA_SETUP_LOCKS: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
_PRAGMA_DICT_GUARD = threading.Lock()

# journal_mode=WAL is persistent per DB file; skip redundant SET after first
# success. LRU-bounded so tmp_path-heavy suites do not grow this map without
# bound; eviction only loses the in-memory hint (next open may re-run
# journal_mode=WAL; harmless).
_MAX_WAL_METADATA_KEYS = 512
_WAL_INITIALIZED_LRU: OrderedDict[str, None] = OrderedDict()


def _pragma_setup_lock(db_path: Path) -> asyncio.Lock:
    """Per-DB asyncio lock keyed by resolved path (snapshot + metering share it)."""
    key = str(db_path.resolve())
    with _PRAGMA_DICT_GUARD:
        lock = _PRAGMA_SETUP_LOCKS.get(key)
        if lock is None:
            lock = asyncio.Lock()
            _PRAGMA_SETUP_LOCKS[key] = lock
        return lock


def _wal_mark_initialized(db_key: str) -> None:
    """Record that journal_mode=WAL was applied for this resolved path (LRU-bounded)."""
    with _PRAGMA_DICT_GUARD:
        if db_key in _WAL_INITIALIZED_LRU:
            _WAL_INITIALIZED_LRU.move_to_end(db_key)
        else:
            _WAL_INITIALIZED_LRU[db_key] = None
            while len(_WAL_INITIALIZED_LRU) > _MAX_WAL_METADATA_KEYS:
                _WAL_INITIALIZED_LRU.popitem(last=False)


async def _apply_wal_pragmas(conn: aiosqlite.Connection, db_key: str) -> None:
    """Apply WAL pragmas; busy_timeout runs before journal_mode to reduce lock errors."""
    await conn.execute("PRAGMA busy_timeout=15000")
    with _PRAGMA_DICT_GUARD:
        need_journal_mode = db_key not in _WAL_INITIALIZED_LRU
    if need_journal_mode:
        await conn.execute("PRAGMA journal_mode=WAL")
        _wal_mark_initialized(db_key)
    await conn.execute("PRAGMA synchronous=NORMAL")


def _assert_sql_in_placeholders(placeholders: str) -> str:
    """Fail closed when dynamic IN-clause placeholders are not ``?,?,…`` only."""
    if set(placeholders) - {"?", ","}:
        raise ValueError("placeholders must be `?,?,…` only")
    return placeholders


def _build_sql_in_placeholders(count: int) -> str:
    """Build ``?,?,…`` placeholders for SQLite ``IN`` clauses (value-bound)."""
    return _assert_sql_in_placeholders(",".join("?" for _ in range(count)))


def parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp stored in SQLite; ``None``/empty -> ``None``.

    Normalizes the trailing ``Z`` (UTC) to ``+00:00`` so ``datetime.fromisoformat``
    accepts it across Python versions. Returns ``None`` on malformed input rather
    than raising, so row mappers can treat missing/legacy timestamps uniformly.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def build_where(
    filters: dict[str, Any],
    allowed: dict[str, str],
) -> tuple[str, list[Any]]:
    """Assemble a WHERE clause from a filter dict against an allow-list.

    ``allowed`` maps a logical filter key to its SQL fragment (e.g.
    ``{"agent_id": "agent_id = ?", "start": "timestamp >= ?"}``). Filters whose
    value is ``None`` are skipped. Unknown keys raise ``ValueError`` — this is
    the allow-list guard that prevents unexpected fragments from leaking into
    dynamic SQL even if a future edit forgets to parameterize.

    Returns ``(where_sql, params)`` where ``where_sql`` is ``"1=1"`` when no
    filters apply, suitable for direct interpolation after ``WHERE``. Values are
    always returned in ``params`` for parameter binding; the SQL fragments in
    ``allowed`` are a compile-time allow-list, never user-controlled.
    """
    conditions: list[str] = []
    params: list[Any] = []
    for key, value in filters.items():
        if value is None:
            continue
        fragment = allowed.get(key)
        if fragment is None:
            raise ValueError(f"unknown filter {key!r}; allowed keys: {sorted(allowed)!r}")
        conditions.append(fragment)
        params.append(value)
    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


class AsyncSqliteRepository:
    """Shared aiosqlite plumbing for ASAP SQLite-backed stores.

    Wraps connection lifecycle (WAL pragmas, per-path lock), idempotent schema
    init, and the three common query shapes (execute / fetch_all / fetch_one).
    Subclasses supply ``schema_ddl`` (one ``CREATE TABLE IF NOT EXISTS`` block)
    and per-method SQL + row mappers; the boilerplate lives here once.

    Atomic multi-step operations use :meth:`transaction`, which opens one
    connection, issues ``BEGIN``, yields it, and ``COMMIT``s on success or
    ``ROLLBACK``s on any exception (so a mid-step crash leaves no partial state).
    """

    def __init__(
        self,
        db_path: str | Path = DEFAULT_DB_PATH,
        schema_ddl: str | None = None,
    ) -> None:
        self._db_path = Path(db_path)
        self._schema_ddl = schema_ddl
        self._initialized = False
        self._init_lock = asyncio.Lock()
        # ``:memory:`` creates a *new* empty DB on every connect, so keep one
        # persistent connection alive and serialise access to it. File-backed
        # DBs use per-call connections (handled in ``_connect``). This mirrors
        # the SQLiteAuditStore pattern and makes ``:memory:`` usable in tests
        # without each store re-implementing it.
        self._is_memory = str(db_path) == ":memory:"
        self._persistent_conn: aiosqlite.Connection | None = None
        self._memory_lock = asyncio.Lock()

    async def _acquire_connection(self) -> aiosqlite.Connection:
        """Return an open connection (persistent for ``:memory:``).

        Caller must hold ``_memory_lock`` when ``_is_memory`` is set, so this
        method does not re-acquire it (``asyncio.Lock`` is non-reentrant).
        """
        if self._is_memory:
            if self._persistent_conn is None:
                self._persistent_conn = await aiosqlite.connect(":memory:")
            return self._persistent_conn
        return await aiosqlite.connect(self._db_path, timeout=15.0)

    async def _release_connection(self, conn: aiosqlite.Connection) -> None:
        """Close *conn* unless it is the persistent in-memory connection."""
        if conn is not self._persistent_conn:
            await conn.close()

    @asynccontextmanager
    async def _connect(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yield a connection with WAL pragmas applied (file-backed path only).

        For ``:memory:`` the persistent connection is yielded under
        ``_memory_lock``; WAL pragmas are skipped (in-memory DBs have no WAL).
        The caller is released from managing close lifecycle in both cases.
        """
        if self._is_memory:
            async with self._memory_lock:
                conn = await self._acquire_connection()
                try:
                    await self._ensure_schema(conn)
                    yield conn
                finally:
                    # Never close the persistent in-memory connection here.
                    pass
            return
        db_key = str(self._db_path.resolve())
        conn = await aiosqlite.connect(self._db_path, timeout=15.0)
        try:
            async with _pragma_setup_lock(self._db_path):
                await _apply_wal_pragmas(conn, db_key)
            await self._ensure_schema(conn)
            yield conn
        finally:
            await conn.close()

    async def _ensure_schema(self, conn: aiosqlite.Connection) -> None:
        """Apply ``schema_ddl`` once, idempotently, under the per-instance lock."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            if self._schema_ddl:
                await conn.executescript(self._schema_ddl)
                await conn.commit()
            self._initialized = True

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        """Run a write query; commit; return affected row count (0 if unknown)."""
        async with self._connect() as conn:
            cursor = await conn.execute(sql, params)
            await conn.commit()
            return cursor.rowcount if cursor.rowcount is not None else 0

    async def fetch_all(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[tuple[Any, ...]]:
        """Run a read query; return all rows as tuples."""
        async with self._connect() as conn:
            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()
            return [tuple(r) for r in rows]

    async def fetch_one(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> tuple[Any, ...] | None:
        """Run a read query; return the first row as a tuple, or ``None``."""
        async with self._connect() as conn:
            cursor = await conn.execute(sql, params)
            row = await cursor.fetchone()
            return tuple(row) if row else None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Yield one connection inside BEGIN IMMEDIATE/COMMIT; ROLLBACK on any exception.

        Use for atomic multi-step operations (e.g. cascade revocation). The
        caller runs reads/writes directly on the yielded ``conn``; the context
        manager owns the transaction boundary. For ``:memory:`` the persistent
        connection is reused (so the transaction sees prior writes).

        ``BEGIN IMMEDIATE`` acquires the SQLite write lock at transaction start
        (rather than deferring it to the first write). This serializes the
        transaction against concurrent ``execute()`` writes on separate
        connections (e.g. ``register_issued`` during a ``revoke_cascade``), so a
        concurrent issuer cannot insert a child that escapes the cascade's
        snapshot (CR#6). ``busy_timeout=15000`` (set in ``_apply_wal_pragmas``)
        makes a contended ``BEGIN IMMEDIATE`` wait instead of failing fast.
        """
        async with self._connect() as conn:
            await conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                await conn.commit()
            except BaseException:
                await conn.rollback()
                raise


__all__ = [
    "DEFAULT_DB_PATH",
    "AsyncSqliteRepository",
    "build_where",
    "parse_iso",
]
