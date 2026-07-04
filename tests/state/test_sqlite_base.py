"""Unit tests for the shared :class:`AsyncSqliteRepository` base (v2.5.1 S1).

Covers the four contract guarantees the migrations depend on:
- ``execute`` / ``fetch_all`` / ``fetch_one`` round-trip;
- ``transaction`` commits on success and rolls back on exception;
- ``parse_iso`` handles valid/invalid/None uniformly;
- ``build_where`` rejects unknown filter keys (allow-list guard).

Tests use ``:memory:`` so no temp files are needed and runs are deterministic.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import pytest
from _pytest.monkeypatch import MonkeyPatch

from asap.state.stores._sqlite_base import (
    AsyncSqliteRepository,
    _build_sql_in_placeholders,
    build_where,
    parse_iso,
)

_DDL = """
CREATE TABLE IF NOT EXISTS sample (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL
)
"""


def _repo() -> AsyncSqliteRepository:
    return AsyncSqliteRepository(":memory:", schema_ddl=_DDL)


async def test_execute_fetch_one_round_trip() -> None:
    repo = _repo()
    inserted = await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "alpha"))
    assert inserted == 1
    row = await repo.fetch_one("SELECT id, name FROM sample WHERE id = ?", (1,))
    assert row == (1, "alpha")


async def test_fetch_all_returns_all_rows_as_tuples() -> None:
    repo = _repo()
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "a"))
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (2, "b"))
    rows = await repo.fetch_all("SELECT id, name FROM sample ORDER BY id")
    assert rows == [(1, "a"), (2, "b")]


async def test_fetch_one_none_when_empty() -> None:
    repo = _repo()
    assert await repo.fetch_one("SELECT id FROM sample WHERE id = ?", (999,)) is None


async def test_fetch_all_empty() -> None:
    repo = _repo()
    assert await repo.fetch_all("SELECT id FROM sample") == []


async def test_transaction_commits_on_success() -> None:
    repo = _repo()
    async with repo.transaction() as conn:
        await conn.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "x"))
    row = await repo.fetch_one("SELECT name FROM sample WHERE id = ?", (1,))
    assert row == ("x",)


async def test_transaction_rolls_back_on_exception() -> None:
    repo = _repo()

    with pytest.raises(RuntimeError, match="boom"):
        async with repo.transaction() as conn:
            await conn.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "x"))
            raise RuntimeError("boom")

    # The row must NOT persist after the rollback.
    assert await repo.fetch_one("SELECT id FROM sample") is None


async def test_schema_ensure_is_idempotent() -> None:
    """Multiple operations on one repo must not re-run the DDL or deadlock."""
    repo = _repo()
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "a"))
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (2, "b"))
    assert await repo.fetch_all("SELECT id FROM sample ORDER BY id") == [(1,), (2,)]


def test_parse_iso_valid_with_z() -> None:
    assert parse_iso("2026-06-25T01:50:00Z") == datetime(2026, 6, 25, 1, 50, 0, tzinfo=timezone.utc)


def test_parse_iso_valid_with_offset() -> None:
    assert parse_iso("2026-06-25T01:50:00+00:00") == datetime(
        2026, 6, 25, 1, 50, 0, tzinfo=timezone.utc
    )


def test_parse_iso_none_and_empty() -> None:
    assert parse_iso(None) is None
    assert parse_iso("") is None


def test_parse_iso_invalid_returns_none() -> None:
    assert parse_iso("not-a-timestamp") is None


def test_build_where_no_filters() -> None:
    where, params = build_where({}, {"agent_id": "agent_id = ?"})
    assert where == "1=1"
    assert params == []


def test_build_where_skips_none_values() -> None:
    where, params = build_where(
        {"agent_id": None, "task_id": "t1"},
        {"agent_id": "agent_id = ?", "task_id": "task_id = ?"},
    )
    assert where == "task_id = ?"
    assert params == ["t1"]


def test_build_where_assembles_multiple_conditions() -> None:
    where, params = build_where(
        {"agent_id": "a1", "start": "2026-06-25"},
        {"agent_id": "agent_id = ?", "start": "timestamp >= ?"},
    )
    assert where == "agent_id = ? AND timestamp >= ?"
    assert params == ["a1", "2026-06-25"]


def test_build_where_rejects_unknown_key() -> None:
    with pytest.raises(ValueError, match="unknown filter"):
        build_where(
            {"evil": "DROP TABLE"},
            {"agent_id": "agent_id = ?"},
        )


def test_build_where_passes_typed_values_through() -> None:
    where, params = build_where(
        {"agent_id": "a1", "limit": 5},
        {"agent_id": "agent_id = ?", "limit": "LIMIT ?"},
    )
    assert params == ["a1", 5]
    assert where == "agent_id = ? AND LIMIT ?"


# ---------------------------------------------------------------------------
# _build_sql_in_placeholders / _assert_sql_in_placeholders — fail-closed guard
# ---------------------------------------------------------------------------


def test_build_sql_in_placeholders_single() -> None:
    assert _build_sql_in_placeholders(1) == "?"


def test_build_sql_in_placeholders_multiple() -> None:
    assert _build_sql_in_placeholders(3) == "?,?,?"


def test_build_sql_in_placeholders_zero() -> None:
    assert _build_sql_in_placeholders(0) == ""


def test_build_sql_in_placeholders_rejects_non_placeholder_chars() -> None:
    """The fail-closed guard rejects anything that is not ``?``/``,``.

    ``_build_sql_in_placeholders`` itself can only ever produce ``?``/``,`` from
    ``len(count)``, so this asserts the guard at the boundary it protects: if a
    future edit fed an attacker-influenced string here, it would raise instead of
    leaking into dynamic SQL.
    """
    from asap.state.stores._sqlite_base import _assert_sql_in_placeholders

    with pytest.raises(ValueError, match="placeholders must be"):
        _assert_sql_in_placeholders("?; DROP TABLE t; --")


# ---------------------------------------------------------------------------
# File-backed _connect path (WAL pragmas + per-path lock)
# ---------------------------------------------------------------------------


async def test_file_backed_connect_applies_wal_and_round_trips(
    tmp_path: Path,
) -> None:
    """A file-backed repo runs WAL pragmas and persists rows across connections."""
    db = tmp_path / "wal_test.db"
    repo = AsyncSqliteRepository(db, schema_ddl=_DDL)
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "a"))

    # A fresh repo on the same file must see the persisted row (proves the file
    # path is used, not a transient :memory: DB) and must not deadlock on the
    # per-path WAL lock when opened a second time.
    repo2 = AsyncSqliteRepository(db, schema_ddl=_DDL)
    row = await repo2.fetch_one("SELECT id, name FROM sample WHERE id = ?", (1,))
    assert row == (1, "a")


async def test_file_backed_transaction_rolls_back(tmp_path: Path) -> None:
    """A file-backed transaction rolls back on exception (no partial write)."""
    db = tmp_path / "txn_rollback.db"
    repo = AsyncSqliteRepository(db, schema_ddl=_DDL)

    with pytest.raises(RuntimeError, match="boom"):
        async with repo.transaction() as conn:
            await conn.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "x"))
            raise RuntimeError("boom")

    assert await repo.fetch_one("SELECT id FROM sample") is None


async def test_two_repos_share_wal_lock_without_deadlock(tmp_path: Path) -> None:
    """Concurrent openings on the same path share the per-path WAL lock safely."""
    db = tmp_path / "shared.db"
    repo_a = AsyncSqliteRepository(db, schema_ddl=_DDL)
    repo_b = AsyncSqliteRepository(db, schema_ddl=_DDL)

    # Interleaved operations from two repos on the same file must both succeed;
    # the per-path lock serializes WAL setup so neither sees 'database is locked'.
    await repo_a.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "a"))
    await repo_b.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (2, "b"))
    rows = await repo_a.fetch_all("SELECT id FROM sample ORDER BY id")
    assert rows == [(1,), (2,)]


async def test_file_backed_transaction_serializes_same_repo_execute_before_begin_immediate(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Issue #245: ``execute()`` must wait during the transaction setup window.

    ``transaction()`` performs connection/WAL/schema setup before issuing
    ``BEGIN IMMEDIATE``. Without the shared per-instance write lock, a
    same-instance ``execute()`` can commit during that pre-BEGIN window and
    escape the transaction's intended critical section.
    """
    db = tmp_path / "issue_245_setup_window.db"
    repo = AsyncSqliteRepository(db, schema_ddl=_DDL)
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "seed"))

    transaction_in_setup = asyncio.Event()
    allow_transaction_to_begin = asyncio.Event()
    events: list[str] = []
    original_ensure_schema = repo._ensure_schema  # noqa: SLF001
    setup_call_count = 0

    async def _gated_ensure_schema(conn: aiosqlite.Connection) -> None:
        nonlocal setup_call_count
        setup_call_count += 1
        if setup_call_count == 1:
            transaction_in_setup.set()
            await asyncio.wait_for(allow_transaction_to_begin.wait(), timeout=5.0)
        await original_ensure_schema(conn)

    monkeypatch.setattr(repo, "_ensure_schema", _gated_ensure_schema)

    async def _run_transaction() -> None:
        async with repo.transaction() as conn:
            await conn.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (2, "txn"))
        events.append("transaction:committed")

    async def _run_execute() -> None:
        await asyncio.wait_for(transaction_in_setup.wait(), timeout=5.0)
        await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (3, "execute"))
        events.append("execute:committed")

    transaction_task = asyncio.create_task(_run_transaction())
    execute_task = asyncio.create_task(_run_execute())
    try:
        await asyncio.wait_for(transaction_in_setup.wait(), timeout=5.0)
        await asyncio.sleep(0.05)
        assert "execute:committed" not in events, (
            "same-instance execute() committed before transaction() reached "
            "BEGIN IMMEDIATE; write serialization did not cover the setup window"
        )
    finally:
        allow_transaction_to_begin.set()

    await asyncio.gather(transaction_task, execute_task)

    rows = await repo.fetch_all("SELECT id, name FROM sample ORDER BY id")
    assert rows == [(1, "seed"), (2, "txn"), (3, "execute")]
    assert events.index("transaction:committed") < events.index("execute:committed")


async def test_file_backed_execute_serializes_concurrent_same_repo_writes(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Issue #245: concurrent same-instance ``execute()`` calls must serialize.

    The per-instance write lock is acquired before ``_connect()``. If that lock
    regresses, a second ``execute()`` can enter connection/schema setup on the
    same repository instance while the first write is still in flight.
    """
    db = tmp_path / "issue_245_execute_serialize.db"
    repo = AsyncSqliteRepository(db, schema_ddl=_DDL)
    await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (1, "seed"))

    first_execute_in_setup = asyncio.Event()
    allow_first_execute_to_continue = asyncio.Event()
    events: list[str] = []
    original_ensure_schema = repo._ensure_schema  # noqa: SLF001
    setup_call_count = 0

    async def _gated_ensure_schema(conn: aiosqlite.Connection) -> None:
        nonlocal setup_call_count
        setup_call_count += 1
        if setup_call_count == 1:
            first_execute_in_setup.set()
            await asyncio.wait_for(allow_first_execute_to_continue.wait(), timeout=5.0)
        await original_ensure_schema(conn)

    monkeypatch.setattr(repo, "_ensure_schema", _gated_ensure_schema)

    async def _run_first_execute() -> None:
        await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (2, "first"))
        events.append("execute:first")

    async def _run_second_execute() -> None:
        await asyncio.wait_for(first_execute_in_setup.wait(), timeout=5.0)
        await repo.execute("INSERT INTO sample(id, name) VALUES (?, ?)", (3, "second"))
        events.append("execute:second")

    first_execute_task = asyncio.create_task(_run_first_execute())
    second_execute_task = asyncio.create_task(_run_second_execute())
    try:
        await asyncio.wait_for(first_execute_in_setup.wait(), timeout=5.0)
        await asyncio.sleep(0.05)
        assert setup_call_count == 1, (
            "same-instance execute() reached connection/schema setup while the "
            "first execute() still held the per-instance write lock"
        )
        assert "execute:second" not in events, (
            "same-instance execute() committed before the first execute() "
            "released the per-instance write lock"
        )
    finally:
        allow_first_execute_to_continue.set()

    await asyncio.gather(first_execute_task, second_execute_task)

    rows = await repo.fetch_all("SELECT id, name FROM sample ORDER BY id")
    assert rows == [(1, "seed"), (2, "first"), (3, "second")]
    assert events.index("execute:first") < events.index("execute:second")


# ---------------------------------------------------------------------------
# parse_iso — boundary coverage
# ---------------------------------------------------------------------------


def test_parse_iso_naive_datetime_preserved() -> None:
    """Naive ISO timestamps (no tz) parse without forcing UTC.

    Naive datetime is the condition under test (parse_iso must preserve a stored
    naive timestamp rather than inventing a tz), so DTZ001 is intentional here.
    """
    assert parse_iso("2026-06-25T01:50:00") == datetime(2026, 6, 25, 1, 50, 0)  # noqa: DTZ001


def test_parse_iso_whitespace_only_returns_none() -> None:
    assert parse_iso("   ") is None


def test_parse_iso_typeerror_on_non_str_returns_none() -> None:
    """A non-string/None input (e.g. an int row value) returns None, not a crash.

    Passing an int exercises the ``except (ValueError, TypeError)`` branch of
    ``parse_iso``; the call is intentionally ill-typed to mimic a corrupted row.
    """
    result: object = parse_iso(12345)
    assert result is None
