"""Tests for delegation revocation storage."""

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from asap.economics.delegation_storage import (
    InMemoryDelegationStorage,
    SQLiteDelegationStorage,
    _assert_sql_in_placeholders,
    _build_sql_in_placeholders,
)

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


# ---------------------------------------------------------------------------
# InMemoryDelegationStorage
# ---------------------------------------------------------------------------


@pytest.fixture
def memory_storage() -> InMemoryDelegationStorage:
    """Fresh in-memory storage for tests."""
    return InMemoryDelegationStorage()


class TestInMemoryDelegationStorage:
    """In-memory revocation storage."""

    @pytest.mark.asyncio
    async def test_is_revoked_false_when_empty(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """is_revoked returns False for any token when none revoked."""
        assert await memory_storage.is_revoked("del_abc") is False
        assert await memory_storage.is_revoked("del_xyz") is False

    @pytest.mark.asyncio
    async def test_revoke_then_is_revoked(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """After revoke(token_id), is_revoked(token_id) returns True."""
        await memory_storage.revoke("del_123")
        assert await memory_storage.is_revoked("del_123") is True
        assert await memory_storage.is_revoked("del_other") is False

    @pytest.mark.asyncio
    async def test_revoke_with_reason(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """revoke accepts optional reason (stored; idempotent overwrite)."""
        await memory_storage.revoke("del_a", reason="compromised")
        assert await memory_storage.is_revoked("del_a") is True
        await memory_storage.revoke("del_a", reason="updated reason")
        assert await memory_storage.is_revoked("del_a") is True

    @pytest.mark.asyncio
    async def test_revoke_idempotent(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """Calling revoke twice for same id is idempotent."""
        await memory_storage.revoke("del_same")
        await memory_storage.revoke("del_same")
        assert await memory_storage.is_revoked("del_same") is True

    @pytest.mark.asyncio
    async def test_register_issued_and_get_delegator(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """register_issued stores token_id -> delegator; get_delegator returns it."""
        await memory_storage.register_issued("del_iss1", "urn:asap:agent:issuer")
        assert await memory_storage.get_delegator("del_iss1") == "urn:asap:agent:issuer"
        assert await memory_storage.get_delegator("del_unknown") is None

    @pytest.mark.asyncio
    async def test_revoke_cascade_revokes_children(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """Revoking a token also revokes tokens issued by its delegate (cascade)."""
        # Chain: P -> D1 (token_1), D1 -> D2 (token_2), D2 -> D3 (token_3)
        await memory_storage.register_issued(
            "del_p_d1",
            "urn:asap:agent:P",
            delegate_urn="urn:asap:agent:D1",
        )
        await memory_storage.register_issued(
            "del_d1_d2",
            "urn:asap:agent:D1",
            delegate_urn="urn:asap:agent:D2",
        )
        await memory_storage.register_issued(
            "del_d2_d3",
            "urn:asap:agent:D2",
            delegate_urn="urn:asap:agent:D3",
        )
        await memory_storage.revoke_cascade("del_p_d1", reason="cascade test")
        assert await memory_storage.is_revoked("del_p_d1") is True
        assert await memory_storage.is_revoked("del_d1_d2") is True
        assert await memory_storage.is_revoked("del_d2_d3") is True

    @pytest.mark.asyncio
    async def test_revoke_cascade_circular_chain_terminates(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """Circular delegation chains terminate without RecursionError."""
        await memory_storage.register_issued(
            "t1",
            "urn:asap:agent:A",
            delegate_urn="urn:asap:agent:B",
        )
        await memory_storage.register_issued(
            "t2",
            "urn:asap:agent:B",
            delegate_urn="urn:asap:agent:A",
        )
        await memory_storage.revoke_cascade("t1")
        assert await memory_storage.is_revoked("t1") is True
        assert await memory_storage.is_revoked("t2") is True

    @pytest.mark.asyncio
    async def test_revoke_cascade_stops_at_max_depth(
        self,
        memory_storage: InMemoryDelegationStorage,
    ) -> None:
        """Tokens beyond _MAX_CASCADE_DEPTH are not revoked (DoS guard)."""
        chain_len = 52
        for i in range(chain_len):
            delegator = f"urn:asap:agent:A{i}"
            delegate = f"urn:asap:agent:A{i + 1}"
            await memory_storage.register_issued(
                f"del_depth_{i}",
                delegator,
                delegate_urn=delegate,
            )
        await memory_storage.revoke_cascade("del_depth_0", reason="depth limit")
        for i in range(51):
            assert await memory_storage.is_revoked(f"del_depth_{i}") is True
        assert await memory_storage.is_revoked("del_depth_51") is False


# ---------------------------------------------------------------------------
# SQLiteDelegationStorage
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Unique SQLite path per test for isolation."""
    return tmp_path / "revocations.db"


@pytest.fixture
def sqlite_storage(temp_db_path: Path) -> SQLiteDelegationStorage:
    """SQLite storage backed by a temp file."""
    return SQLiteDelegationStorage(db_path=temp_db_path)


class TestSQLiteDelegationStorage:
    """SQLite revocation storage; persistence across restarts."""

    @pytest.mark.asyncio
    async def test_is_revoked_false_when_empty(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """is_revoked returns False when table empty."""
        assert await sqlite_storage.is_revoked("del_any") is False

    @pytest.mark.asyncio
    async def test_revoke_then_is_revoked(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """After revoke, is_revoked returns True."""
        await sqlite_storage.revoke("del_sqlite_1")
        assert await sqlite_storage.is_revoked("del_sqlite_1") is True
        assert await sqlite_storage.is_revoked("del_other") is False

    @pytest.mark.asyncio
    async def test_revoke_with_reason(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """revoke stores optional reason."""
        await sqlite_storage.revoke("del_r", reason="security")
        assert await sqlite_storage.is_revoked("del_r") is True

    @pytest.mark.asyncio
    async def test_persistence_survives_restart(
        self,
        temp_db_path: Path,
    ) -> None:
        """Revocations persist: new instance sees previously revoked id."""
        store1 = SQLiteDelegationStorage(db_path=temp_db_path)
        await store1.revoke("del_persist")
        assert await store1.is_revoked("del_persist") is True

        store2 = SQLiteDelegationStorage(db_path=temp_db_path)
        assert await store2.is_revoked("del_persist") is True

    @pytest.mark.asyncio
    async def test_revoke_idempotent(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """Re-calling revoke for same id overwrites (INSERT OR REPLACE)."""
        await sqlite_storage.revoke("del_idem")
        await sqlite_storage.revoke("del_idem", reason="again")
        assert await sqlite_storage.is_revoked("del_idem") is True

    @pytest.mark.asyncio
    async def test_register_issued_and_get_delegator(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """register_issued stores token_id -> delegator; get_delegator returns it."""
        await sqlite_storage.register_issued("del_sql_iss", "urn:asap:agent:sql_issuer")
        assert await sqlite_storage.get_delegator("del_sql_iss") == "urn:asap:agent:sql_issuer"
        assert await sqlite_storage.get_delegator("del_unknown") is None

    @pytest.mark.asyncio
    async def test_revoke_cascade_revokes_children(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """Revoking a token also revokes tokens issued by its delegate (cascade)."""
        await sqlite_storage.register_issued(
            "del_root_mid",
            "urn:asap:agent:root",
            delegate_urn="urn:asap:agent:mid",
        )
        await sqlite_storage.register_issued(
            "del_mid_leaf",
            "urn:asap:agent:mid",
            delegate_urn="urn:asap:agent:leaf",
        )
        await sqlite_storage.revoke_cascade("del_root_mid")
        assert await sqlite_storage.is_revoked("del_root_mid") is True
        assert await sqlite_storage.is_revoked("del_mid_leaf") is True

    @pytest.mark.asyncio
    async def test_revoke_cascade_circular_chain_terminates(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """Circular delegation chains terminate without RecursionError."""
        await sqlite_storage.register_issued(
            "t1",
            "urn:asap:agent:A",
            delegate_urn="urn:asap:agent:B",
        )
        await sqlite_storage.register_issued(
            "t2",
            "urn:asap:agent:B",
            delegate_urn="urn:asap:agent:A",
        )
        await sqlite_storage.revoke_cascade("t1")
        assert await sqlite_storage.is_revoked("t1") is True
        assert await sqlite_storage.is_revoked("t2") is True

    @pytest.mark.asyncio
    async def test_revoke_cascade_stops_at_max_depth(
        self,
        sqlite_storage: SQLiteDelegationStorage,
    ) -> None:
        """Tokens beyond _MAX_CASCADE_DEPTH are not revoked (DoS guard on SQLite path)."""
        chain_len = 52
        for i in range(chain_len):
            delegator = f"urn:asap:agent:A{i}"
            delegate = f"urn:asap:agent:A{i + 1}"
            await sqlite_storage.register_issued(
                f"del_depth_{i}",
                delegator,
                delegate_urn=delegate,
            )
        await sqlite_storage.revoke_cascade("del_depth_0", reason="depth limit")
        for i in range(51):
            assert await sqlite_storage.is_revoked(f"del_depth_{i}") is True
        assert await sqlite_storage.is_revoked("del_depth_51") is False


# ---------------------------------------------------------------------------
# InMemoryDelegationStorage — additional coverage
# ---------------------------------------------------------------------------


class TestInMemoryDelegationStorageCoverage:
    """Cover list_issued_summaries, get_issued_at, get_revoked_at,
    are_revoked, get_token_detail."""

    @pytest.mark.asyncio
    async def test_list_issued_summaries(self, memory_storage: InMemoryDelegationStorage) -> None:
        await memory_storage.register_issued("t1", "urn:delegator:a", delegate_urn="urn:delegate:x")
        await memory_storage.register_issued("t2", "urn:delegator:a")
        await memory_storage.register_issued("t3", "urn:delegator:b")

        summaries = await memory_storage.list_issued_summaries("urn:delegator:a")
        assert len(summaries) == 2
        ids = {s.id for s in summaries}
        assert ids == {"t1", "t2"}
        # Check delegate_urn populated
        by_id = {s.id: s for s in summaries}
        assert by_id["t1"].delegate_urn == "urn:delegate:x"
        assert by_id["t2"].delegate_urn is None

    @pytest.mark.asyncio
    async def test_list_issued_summaries_empty(
        self, memory_storage: InMemoryDelegationStorage
    ) -> None:
        summaries = await memory_storage.list_issued_summaries("urn:delegator:nobody")
        assert summaries == []

    @pytest.mark.asyncio
    async def test_get_issued_at(self, memory_storage: InMemoryDelegationStorage) -> None:
        await memory_storage.register_issued("tok1", "urn:d:a")
        issued_at = await memory_storage.get_issued_at("tok1")
        assert issued_at is not None
        # Nonexistent token
        assert await memory_storage.get_issued_at("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_revoked_at(self, memory_storage: InMemoryDelegationStorage) -> None:
        await memory_storage.revoke("tok1", reason="test")
        revoked_at = await memory_storage.get_revoked_at("tok1")
        assert revoked_at is not None
        # Not revoked
        assert await memory_storage.get_revoked_at("tok2") is None

    @pytest.mark.asyncio
    async def test_are_revoked(self, memory_storage: InMemoryDelegationStorage) -> None:
        await memory_storage.revoke("tok1")
        result = await memory_storage.are_revoked(["tok1", "tok2", "tok3"])
        assert result == {"tok1": True, "tok2": False, "tok3": False}

    @pytest.mark.asyncio
    async def test_are_revoked_empty_list(self, memory_storage: InMemoryDelegationStorage) -> None:
        result = await memory_storage.are_revoked([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_token_detail_existing(
        self, memory_storage: InMemoryDelegationStorage
    ) -> None:
        await memory_storage.register_issued("tok1", "urn:d:a", delegate_urn="urn:del:b")
        detail = await memory_storage.get_token_detail("tok1")
        assert detail is not None
        assert detail.id == "tok1"
        assert detail.delegator_urn == "urn:d:a"
        assert detail.delegate_urn == "urn:del:b"
        assert detail.is_revoked is False
        assert detail.revoked_at is None

    @pytest.mark.asyncio
    async def test_get_token_detail_revoked(
        self, memory_storage: InMemoryDelegationStorage
    ) -> None:
        await memory_storage.register_issued("tok1", "urn:d:a")
        await memory_storage.revoke("tok1", reason="expired")
        detail = await memory_storage.get_token_detail("tok1")
        assert detail is not None
        assert detail.is_revoked is True
        assert detail.revoked_at is not None

    @pytest.mark.asyncio
    async def test_get_token_detail_not_found(
        self, memory_storage: InMemoryDelegationStorage
    ) -> None:
        detail = await memory_storage.get_token_detail("nonexistent")
        assert detail is None


# ---------------------------------------------------------------------------
# SQLiteDelegationStorage — additional coverage
# ---------------------------------------------------------------------------


class TestSQLiteDelegationStorageCoverage:
    """Cover list_token_ids_issued_by, list_issued_summaries, get_issued_at,
    get_revoked_at, are_revoked, get_token_detail in SQLite backend."""

    @pytest.mark.asyncio
    async def test_list_token_ids_issued_by(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.register_issued("t1", "urn:d:a")
        await sqlite_storage.register_issued("t2", "urn:d:a")
        await sqlite_storage.register_issued("t3", "urn:d:b")

        ids = await sqlite_storage.list_token_ids_issued_by("urn:d:a")
        assert set(ids) == {"t1", "t2"}
        assert await sqlite_storage.list_token_ids_issued_by("urn:d:nobody") == []

    @pytest.mark.asyncio
    async def test_list_issued_summaries(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.register_issued("t1", "urn:d:a", delegate_urn="urn:del:x")
        await sqlite_storage.register_issued("t2", "urn:d:a")
        await sqlite_storage.register_issued("t3", "urn:d:b")

        summaries = await sqlite_storage.list_issued_summaries("urn:d:a")
        assert len(summaries) == 2
        ids = {s.id for s in summaries}
        assert ids == {"t1", "t2"}
        by_id = {s.id: s for s in summaries}
        assert by_id["t1"].delegate_urn == "urn:del:x"
        assert by_id["t2"].delegate_urn is None
        assert by_id["t1"].created_at is not None

    @pytest.mark.asyncio
    async def test_list_issued_summaries_empty(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        summaries = await sqlite_storage.list_issued_summaries("urn:d:nobody")
        assert summaries == []

    @pytest.mark.asyncio
    async def test_get_issued_at(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.register_issued("tok1", "urn:d:a")
        issued_at = await sqlite_storage.get_issued_at("tok1")
        assert issued_at is not None
        assert await sqlite_storage.get_issued_at("nonexistent") is None

    @pytest.mark.asyncio
    async def test_get_revoked_at(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.revoke("tok1", reason="test")
        revoked_at = await sqlite_storage.get_revoked_at("tok1")
        assert revoked_at is not None
        assert await sqlite_storage.get_revoked_at("not_revoked") is None

    @pytest.mark.asyncio
    async def test_are_revoked(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.revoke("tok1")
        await sqlite_storage.revoke("tok3")
        result = await sqlite_storage.are_revoked(["tok1", "tok2", "tok3"])
        assert result == {"tok1": True, "tok2": False, "tok3": True}

    @pytest.mark.asyncio
    async def test_are_revoked_empty_list(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        result = await sqlite_storage.are_revoked([])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_token_detail_existing(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.register_issued("tok1", "urn:d:a", delegate_urn="urn:del:b")
        detail = await sqlite_storage.get_token_detail("tok1")
        assert detail is not None
        assert detail.id == "tok1"
        assert detail.delegator_urn == "urn:d:a"
        assert detail.delegate_urn == "urn:del:b"
        assert detail.is_revoked is False
        assert detail.revoked_at is None
        assert detail.created_at is not None

    @pytest.mark.asyncio
    async def test_get_token_detail_revoked(self, sqlite_storage: SQLiteDelegationStorage) -> None:
        await sqlite_storage.register_issued("tok1", "urn:d:a")
        await sqlite_storage.revoke("tok1", reason="compromised")
        detail = await sqlite_storage.get_token_detail("tok1")
        assert detail is not None
        assert detail.is_revoked is True
        assert detail.revoked_at is not None

    @pytest.mark.asyncio
    async def test_get_token_detail_not_found(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        detail = await sqlite_storage.get_token_detail("nonexistent")
        assert detail is None

    @pytest.mark.asyncio
    async def test_get_delegate_returns_value(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        await sqlite_storage.register_issued("tok1", "urn:d:a", delegate_urn="urn:del:x")
        delegate = await sqlite_storage.get_delegate("tok1")
        assert delegate == "urn:del:x"

    @pytest.mark.asyncio
    async def test_get_delegate_returns_none_when_absent(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        await sqlite_storage.register_issued("tok1", "urn:d:a")
        delegate = await sqlite_storage.get_delegate("tok1")
        assert delegate is None

    @pytest.mark.asyncio
    async def test_get_delegator_returns_none_for_unknown(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        delegator = await sqlite_storage.get_delegator("unknown_tok")
        assert delegator is None

    @pytest.mark.asyncio
    async def test_parse_iso_datetime_edge_cases(
        self, sqlite_storage: SQLiteDelegationStorage
    ) -> None:
        """_parse_iso_datetime handles None and invalid values."""
        assert sqlite_storage._parse_iso_datetime(None) is None
        assert sqlite_storage._parse_iso_datetime("") is None
        assert sqlite_storage._parse_iso_datetime("not-a-date") is None
        # Z suffix handled
        result = sqlite_storage._parse_iso_datetime("2026-01-01T00:00:00Z")
        assert result is not None

    def test_build_sql_in_placeholders_formats_question_marks(self) -> None:
        assert _build_sql_in_placeholders(3) == "?,?,?"
        assert _build_sql_in_placeholders(0) == ""

    def test_assert_sql_in_placeholders_rejects_malformed(self) -> None:
        with pytest.raises(ValueError, match="placeholders must be"):
            _assert_sql_in_placeholders("id=1; DROP TABLE revocations; --")


# ---------------------------------------------------------------------------
# Task 1.0 (B1) — Atomic cascade revocation regression tests
# ---------------------------------------------------------------------------


class TestRevokeCascadeAtomic:
    """Atomic cascade revocation: SQLite rollback + InMemory lock parity.

    Covers the two regression scenarios from the v2.5.1 Thermo-Nuclear Patch:
    1. SQLite mid-cascade crash must roll back atomically (no partial state).
    2. InMemory concurrent ``register_issued`` during a cascade must not lose a
       newly-issued child (cascade holds an ``asyncio.Lock``).
    """

    @pytest.mark.asyncio
    async def test_revoke_cascade_atomic_rollback(
        self,
        sqlite_storage: SQLiteDelegationStorage,
        monkeypatch: "MonkeyPatch",
    ) -> None:
        """A failing mid-cascade revoke must leave NO token revoked (atomic rollback).

        Tree seeded (two branches off the root):
            parent      -> child1      (delegate urn:mid1) -> grandchild1 (leaf1)
            child_extra -> (issued by root, delegate urn:mid2)
            child2      -> (issued by mid2) -> grandchild2 (leaf2)
        The cascade from `parent` reaches child1, grandchild1, child_extra,
        child2, grandchild2.
        """
        await sqlite_storage.register_issued(
            "parent", "urn:asap:agent:root", delegate_urn="urn:asap:agent:mid1"
        )
        await sqlite_storage.register_issued(
            "child1", "urn:asap:agent:mid1", delegate_urn="urn:asap:agent:leaf1"
        )
        await sqlite_storage.register_issued(
            "child_extra", "urn:asap:agent:root", delegate_urn="urn:asap:agent:mid2"
        )
        await sqlite_storage.register_issued(
            "child2", "urn:asap:agent:mid2", delegate_urn="urn:asap:agent:leaf2"
        )
        await sqlite_storage.register_issued(
            "grandchild1", "urn:asap:agent:leaf1", delegate_urn="urn:asap:agent:end1"
        )
        await sqlite_storage.register_issued(
            "grandchild2", "urn:asap:agent:leaf2", delegate_urn="urn:asap:agent:end2"
        )
        all_ids = [
            "parent",
            "child1",
            "child_extra",
            "child2",
            "grandchild1",
            "grandchild2",
        ]

        # Fail exactly once, on the 2nd per-id revoke the cascade performs.
        # Patch the per-id hook the atomic path uses when present, and also the
        # public ``revoke`` (used by the legacy non-atomic path) so the test is
        # valid both before and after the refactor.
        call_count = {"n": 0}

        def _should_fail() -> bool:
            call_count["n"] += 1
            return call_count["n"] == 2

        original_revoke = sqlite_storage.revoke

        async def _failing_revoke(token_id: str, reason: str | None = None) -> None:
            if _should_fail():
                raise RuntimeError("simulated mid-cascade crash")
            await original_revoke(token_id, reason)

        monkeypatch.setattr(sqlite_storage, "revoke", _failing_revoke)

        if hasattr(sqlite_storage, "_revoke_on_conn"):
            from datetime import datetime, timezone

            async def _failing_revoke_on_conn(
                conn: object, token_id: str, reason: str | None
            ) -> None:
                if _should_fail():
                    raise RuntimeError("simulated mid-cascade crash")
                now_iso = datetime.now(timezone.utc).isoformat()
                await conn.execute(
                    "INSERT OR REPLACE INTO revocations (id, revoked_at, reason) VALUES (?, ?, ?)",
                    (token_id, now_iso, reason),
                )

            monkeypatch.setattr(sqlite_storage, "_revoke_on_conn", _failing_revoke_on_conn)

        with pytest.raises(RuntimeError, match="simulated mid-cascade crash"):
            await sqlite_storage.revoke_cascade("parent", reason="rollback test")

        # Atomic rollback: nothing should be persisted.
        revoked = await sqlite_storage.are_revoked(all_ids)
        assert revoked == dict.fromkeys(all_ids, False), (
            f"expected no revocations after rollback, got {revoked}"
        )

    @pytest.mark.asyncio
    async def test_revoke_cascade_concurrent_inmemory_no_lost_child(
        self,
        memory_storage: InMemoryDelegationStorage,
        monkeypatch: "MonkeyPatch",
    ) -> None:
        """A child issued mid-cascade must not be lost (cascade holds a lock).

        Invariant: the cascade and a concurrent ``register_issued`` must be
        serialized by an ``asyncio.Lock`` — the issue must not interleave
        *inside* the cascade's critical section. We detect non-serialization
        by recording the relative order of ``register_issued(child_new)``
        completing vs. the cascade revoking the root's delegate branch. Without
        a lock the issue completes mid-cascade (recorded before the cascade
        finishes revoking); with the lock the issue is delayed until the
        cascade releases, so it completes only after the cascade's final revoke.

        The "not lost" check (``get_delegator(child_new)`` is observable) holds
        in both worlds; the ordering check is what the lock guarantees.
        """
        await memory_storage.register_issued(
            "parent", "urn:asap:agent:root", delegate_urn="urn:asap:agent:mid"
        )
        await memory_storage.register_issued(
            "child", "urn:asap:agent:mid", delegate_urn="urn:asap:agent:leaf"
        )

        events: list[str] = []
        yielded_once = {"done": False}
        original_list = memory_storage.list_token_ids_issued_by
        original_revoke = memory_storage.revoke

        async def _yielding_list(delegator_urn: str) -> list[str]:
            # Yield exactly once, while walking the root's delegate ("mid"),
            # so the concurrent register_issued races the cascade's snapshot.
            if delegator_urn == "urn:asap:agent:mid" and not yielded_once["done"]:
                await asyncio.sleep(0)
                yielded_once["done"] = True
            return await original_list(delegator_urn)

        async def _recording_revoke(token_id: str, reason: str | None = None) -> None:
            events.append(f"revoke:{token_id}:start")
            await original_revoke(token_id, reason)
            events.append(f"revoke:{token_id}:end")

        monkeypatch.setattr(memory_storage, "list_token_ids_issued_by", _yielding_list)
        monkeypatch.setattr(memory_storage, "revoke", _recording_revoke)

        async def _issue_new_child() -> None:
            await memory_storage.register_issued(
                "child_new",
                "urn:asap:agent:mid",
                delegate_urn="urn:asap:agent:leaf_new",
            )
            events.append("issue:child_new")

        cascade_task = asyncio.create_task(
            memory_storage.revoke_cascade("parent", reason="concurrent test")
        )
        issue_task = asyncio.create_task(_issue_new_child())
        await asyncio.gather(cascade_task, issue_task)

        # The new child was issued and is observable in the store (not lost).
        delegator = await memory_storage.get_delegator("child_new")
        assert delegator == "urn:asap:agent:mid", (
            f"concurrent register_issued was lost during cascade (get_delegator={delegator!r})"
        )
        # Serialization: the issue must not complete while the cascade is
        # mid-revoke. With the lock, every "revoke:*:end" for the cascade
        # precedes "issue:child_new". Without the lock, "issue:child_new"
        # appears between the yield and the first revoke (interleaved).
        issue_idx = events.index("issue:child_new")
        last_revoke_end = max(
            (i for i, e in enumerate(events) if e.startswith("revoke:") and e.endswith(":end")),
            default=-1,
        )
        assert issue_idx > last_revoke_end, (
            f"register_issued interleaved inside the cascade critical section (events={events})"
        )
        # And the originally-seeded tree was revoked consistently.
        assert await memory_storage.is_revoked("parent") is True
        assert await memory_storage.is_revoked("child") is True
