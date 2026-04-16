"""Tests for tamper-evident audit logging."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

import pytest

from asap.economics.audit import (
    AuditEntry,
    AuditStore,
    InMemoryAuditStore,
    SQLiteAuditStore,
    compute_entry_hash,
)


@pytest.fixture()
def sqlite_audit_store(tmp_path: Path) -> SQLiteAuditStore:
    """Fresh SQLiteAuditStore per test (isolated DB)."""
    return SQLiteAuditStore(db_path=str(tmp_path / "audit.db"))


class TestComputeEntryHash:
    """Tests for the deterministic hash computation function."""

    def test_deterministic(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        h1 = compute_entry_hash("", ts, "task.request", {"key": "value"})
        h2 = compute_entry_hash("", ts, "task.request", {"key": "value"})
        assert h1 == h2

    def test_different_inputs_different_hash(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        h1 = compute_entry_hash("", ts, "task.request", {})
        h2 = compute_entry_hash("", ts, "task.completed", {})
        assert h1 != h2

    def test_prev_hash_affects_output(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        h1 = compute_entry_hash("", ts, "op", {})
        h2 = compute_entry_hash("abc123", ts, "op", {})
        assert h1 != h2

    def test_details_order_independent(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        h1 = compute_entry_hash("", ts, "op", {"a": 1, "b": 2})
        h2 = compute_entry_hash("", ts, "op", {"b": 2, "a": 1})
        assert h1 == h2

    def test_returns_hex_sha256(self) -> None:
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        result = compute_entry_hash("", ts, "op", {})
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)


class TestAuditEntryModel:
    """Tests for the AuditEntry Pydantic model."""

    def test_create_with_defaults(self) -> None:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            operation="task.request",
            agent_urn="urn:asap:agent:test",
        )
        assert entry.id != ""
        assert entry.prev_hash == ""
        assert entry.hash == ""
        assert entry.details == {}

    def test_immutable(self) -> None:
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            operation="op",
            agent_urn="urn:asap:agent:test",
        )
        with pytest.raises(ValueError):
            entry.operation = "changed"  # type: ignore[misc]

    def test_conforms_to_protocol(self) -> None:
        assert isinstance(InMemoryAuditStore(), AuditStore)
        assert isinstance(SQLiteAuditStore(), AuditStore)


class TestInMemoryAuditStore:
    """Tests for the in-memory audit store implementation."""

    async def test_append_and_query(self) -> None:
        store = InMemoryAuditStore()
        entry = AuditEntry(
            timestamp=datetime.now(timezone.utc),
            operation="task.request",
            agent_urn="urn:asap:agent:test",
        )
        result = await store.append(entry)
        assert result.hash != ""
        assert result.prev_hash == ""

        entries = await store.query()
        assert len(entries) == 1

    async def test_hash_chain_integrity(self) -> None:
        store = InMemoryAuditStore()
        for i in range(5):
            entry = AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation=f"op.{i}",
                agent_urn="urn:asap:agent:test",
                details={"index": i},
            )
            await store.append(entry)
        assert await store.verify_chain() is True

    async def test_chain_links_prev_hash(self) -> None:
        store = InMemoryAuditStore()
        e1 = await store.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation="op.0",
                agent_urn="urn:asap:agent:test",
            )
        )
        e2 = await store.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation="op.1",
                agent_urn="urn:asap:agent:test",
            )
        )
        assert e2.prev_hash == e1.hash

    async def test_tamper_detection(self) -> None:
        store = InMemoryAuditStore()
        for i in range(3):
            entry = AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation=f"op.{i}",
                agent_urn="urn:asap:agent:test",
            )
            await store.append(entry)
        store._entries[1] = store._entries[1].model_copy(update={"details": {"tampered": True}})
        assert await store.verify_chain() is False

    async def test_query_by_urn(self) -> None:
        store = InMemoryAuditStore()
        for urn in ["urn:asap:agent:a", "urn:asap:agent:b", "urn:asap:agent:a"]:
            await store.append(
                AuditEntry(
                    timestamp=datetime.now(timezone.utc),
                    operation="op",
                    agent_urn=urn,
                )
            )
        results = await store.query(agent_urn="urn:asap:agent:a")
        assert len(results) == 2

    async def test_query_with_time_window(self) -> None:
        store = InMemoryAuditStore()
        t1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 1, tzinfo=timezone.utc)
        t3 = datetime(2026, 12, 1, tzinfo=timezone.utc)
        for t in [t1, t2, t3]:
            await store.append(
                AuditEntry(
                    timestamp=t,
                    operation="op",
                    agent_urn="urn:asap:agent:test",
                )
            )
        results = await store.query(
            start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        assert len(results) == 1

    async def test_query_pagination(self) -> None:
        store = InMemoryAuditStore()
        for i in range(10):
            await store.append(
                AuditEntry(
                    timestamp=datetime.now(timezone.utc),
                    operation=f"op.{i}",
                    agent_urn="urn:asap:agent:test",
                )
            )
        page1 = await store.query(limit=3, offset=0)
        page2 = await store.query(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0].operation != page2[0].operation

    async def test_count(self) -> None:
        store = InMemoryAuditStore()
        assert await store.count() == 0
        await store.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation="op",
                agent_urn="urn:asap:agent:test",
            )
        )
        assert await store.count() == 1

    async def test_empty_chain_is_valid(self) -> None:
        store = InMemoryAuditStore()
        assert await store.verify_chain() is True


class TestSQLiteAuditStore:
    """Tests for the SQLite-backed audit store implementation."""

    async def test_append_and_verify(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        for i in range(5):
            await sqlite_audit_store.append(
                AuditEntry(
                    timestamp=datetime.now(timezone.utc),
                    operation=f"op.{i}",
                    agent_urn="urn:asap:agent:test",
                    details={"index": i},
                )
            )
        assert await sqlite_audit_store.verify_chain() is True
        assert await sqlite_audit_store.count() == 5

    async def test_query_filters(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        await sqlite_audit_store.append(
            AuditEntry(
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
                operation="op.a",
                agent_urn="urn:asap:agent:a",
            )
        )
        await sqlite_audit_store.append(
            AuditEntry(
                timestamp=datetime(2026, 6, 1, tzinfo=timezone.utc),
                operation="op.b",
                agent_urn="urn:asap:agent:b",
            )
        )
        results = await sqlite_audit_store.query(agent_urn="urn:asap:agent:a")
        assert len(results) == 1
        assert results[0].agent_urn == "urn:asap:agent:a"

    async def test_query_time_window(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        for ts in [
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 6, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 1, tzinfo=timezone.utc),
        ]:
            await sqlite_audit_store.append(
                AuditEntry(
                    timestamp=ts,
                    operation="op",
                    agent_urn="urn:asap:agent:test",
                )
            )
        results = await sqlite_audit_store.query(
            start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            end=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        assert len(results) == 1

    async def test_pagination(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        for i in range(10):
            await sqlite_audit_store.append(
                AuditEntry(
                    timestamp=datetime.now(timezone.utc),
                    operation=f"op.{i}",
                    agent_urn="urn:asap:agent:test",
                )
            )
        page = await sqlite_audit_store.query(limit=3, offset=2)
        assert len(page) == 3
        assert page[0].operation == "op.2"

    async def test_empty_chain_is_valid(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        assert await sqlite_audit_store.verify_chain() is True

    async def test_count_empty(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        assert await sqlite_audit_store.count() == 0

    async def test_chain_links_correct(self, sqlite_audit_store: SQLiteAuditStore) -> None:
        e1 = await sqlite_audit_store.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation="op.0",
                agent_urn="urn:asap:agent:test",
            )
        )
        e2 = await sqlite_audit_store.append(
            AuditEntry(
                timestamp=datetime.now(timezone.utc),
                operation="op.1",
                agent_urn="urn:asap:agent:test",
            )
        )
        assert e2.prev_hash == e1.hash
        assert e1.prev_hash == ""
