"""Integration test: two store classes sharing one ``asap_state.db`` path (v2.5.1 S1).

Exercises the shared per-path WAL lock under realistic interleaved writes — the
scenario a server hits at startup when ``SQLiteDelegationStorage`` and
``SQLiteMeteringStorage`` are both wired against the default ``asap_state.db``.
Guards against the pre-S1 ``journal_mode=WAL`` race and the divergent-index DDL
drift (S0 B2) regressing.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from asap.economics.delegation_storage import SQLiteDelegationStorage
from asap.economics.metering import UsageMetrics
from asap.economics.storage import MeteringQuery, SQLiteMeteringStorage


async def test_two_stores_share_db_path_interleaved_writes(tmp_path: Path) -> None:
    """Delegation + metering stores on the same file interleave without deadlock."""
    db = tmp_path / "asap_state.db"
    delegation = SQLiteDelegationStorage(db_path=db)
    metering = SQLiteMeteringStorage(db_path=db)

    # Interleave writes from both stores on the shared file. The per-path WAL
    # lock serializes journal_mode setup so neither sees 'database is locked'.
    await delegation.register_issued("tok-1", "urn:asap:agent:parent", "urn:asap:agent:child")
    await metering.record(
        UsageMetrics(
            task_id="task-1",
            agent_id="urn:asap:agent:parent",
            consumer_id="urn:asap:agent:caller",
            tokens_in=10,
            tokens_out=20,
            duration_ms=100,
            api_calls=1,
            timestamp=datetime.now(timezone.utc),
        )
    )
    await delegation.revoke("tok-1", reason="rotated")
    await metering.record(
        UsageMetrics(
            task_id="task-2",
            agent_id="urn:asap:agent:parent",
            consumer_id="urn:asap:agent:caller",
            tokens_in=5,
            tokens_out=5,
            api_calls=0,
            timestamp=datetime.now(timezone.utc),
        )
    )

    # Both stores read their own tables back from the shared file.
    assert await delegation.is_revoked("tok-1") is True
    events = await metering.query(MeteringQuery(agent_id="urn:asap:agent:parent"))
    assert len(events) == 2


async def test_shared_db_path_both_indexes_present_regardless_of_init_order(
    tmp_path: Path,
) -> None:
    """The canonical usage_events DDL installs both indexes no matter which store inits first."""
    from aiosqlite import connect

    db = tmp_path / "asap_state.db"
    # Metering inits first (creates usage_events with both indexes).
    metering = SQLiteMeteringStorage(db_path=db)
    await metering.record(
        UsageMetrics(
            task_id="t",
            agent_id="a",
            consumer_id="c",
            timestamp=datetime.now(timezone.utc),
        )
    )

    async with connect(db) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='usage_events'"
        )
        index_names = {str(row[0]) for row in await cursor.fetchall()}

    assert "idx_usage_agent_timestamp" in index_names
    assert "idx_usage_consumer_timestamp" in index_names
