"""Tests for delegation revocation storage (Task 2.4.1)."""

from pathlib import Path

import pytest

from asap.economics.delegation_storage import (
    InMemoryDelegationStorage,
    SQLiteDelegationStorage,
)


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
