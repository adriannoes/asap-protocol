"""Tests for `asap audit export` CLI (Sprint S2 — TDD).

Contract for ``--format json`` (stdout): a JSON **array** of audit entry objects,
each with ``id``, ``timestamp`` (ISO-8601), ``operation``, ``agent_urn``,
``details`` (object), ``prev_hash``, ``hash`` — matching ``AuditEntry`` fields.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from asap.cli import app
from asap.economics.audit import AuditEntry, SQLiteAuditStore, compute_entry_hash


@pytest.fixture(autouse=True)
def _stable_typer_rich_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fix Typer/Rich width so ``CliRunner`` captures full help and errors on CI."""
    import typer.rich_utils as tr

    monkeypatch.setattr(tr, "MAX_WIDTH", 120)


def _assert_json_chain_valid(entries: list[dict[str, object]]) -> None:
    """Re-verify SHA-256 chain from exported JSON (same rules as ``verify_chain``)."""
    prev_hash = ""
    for raw in entries:
        ts = datetime.fromisoformat(str(raw["timestamp"]))
        operation = str(raw["operation"])
        details = raw["details"]
        assert isinstance(details, dict)
        stored_prev = str(raw["prev_hash"])
        stored_hash = str(raw["hash"])
        expected = compute_entry_hash(prev_hash, ts, operation, details)
        assert stored_prev == prev_hash
        assert stored_hash == expected
        prev_hash = stored_hash


async def _seed_sqlite_audit_store(db_path: Path) -> list[AuditEntry]:
    """Append a small linear chain of entries; return sealed rows in order."""
    store = SQLiteAuditStore(db_path=str(db_path))
    base = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    sealed: list[AuditEntry] = []
    for i in range(3):
        entry = AuditEntry(
            timestamp=base + timedelta(minutes=i),
            operation=f"fixture.op.{i}",
            agent_urn="urn:asap:agent:cli-fixture",
            details={"seq": i, "label": "audit-export-test"},
        )
        sealed.append(await store.append(entry))
    assert await store.verify_chain() is True
    return sealed


@pytest.fixture
def sqlite_audit_db(tmp_path: Path) -> Path:
    """Path to a SQLite DB file with a pre-seeded audit chain."""
    db_file = tmp_path / "audit_export.db"
    asyncio.run(_seed_sqlite_audit_store(db_file))
    return db_file


def test_audit_export_json_stdout_contains_valid_hash_chain(sqlite_audit_db: Path) -> None:
    """``asap audit export`` prints all rows and preserves a valid hash chain."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout + result.stderr

    payload = json.loads(result.stdout.strip())
    assert isinstance(payload, list)
    assert len(payload) == 3

    for i in range(3):
        assert any(str(e.get("operation", "")) == f"fixture.op.{i}" for e in payload)

    _assert_json_chain_valid(payload)


def test_audit_export_csv_has_header_and_one_row_per_entry(sqlite_audit_db: Path) -> None:
    """CSV format: header row plus one data row per audit entry."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "csv",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    lines = [ln for ln in result.stdout.strip().splitlines() if ln.strip()]
    assert lines[0].startswith("id,")
    assert "timestamp" in lines[0] and "hash" in lines[0]
    assert len(lines) == 4


def test_audit_export_jsonl_one_object_per_line(sqlite_audit_db: Path) -> None:
    """JSONL: each line is a JSON object with required audit fields."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "jsonl",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    raw_lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert len(raw_lines) == 3
    for ln in raw_lines:
        obj = json.loads(ln)
        required = {"id", "timestamp", "operation", "agent_urn", "details", "prev_hash", "hash"}
        assert required.issubset(obj.keys())


def test_audit_export_verify_chain_exits_nonzero_when_tampered(tmp_path: Path) -> None:
    """``--verify-chain`` fails after a direct SQLite tamper (hash no longer matches)."""
    import sqlite3

    db_file = tmp_path / "audit_tamper.db"
    asyncio.run(_seed_sqlite_audit_store(db_file))
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        "UPDATE audit_log SET details = ? WHERE rowid = 1",
        (json.dumps({"tampered": True}),),
    )
    conn.commit()
    conn.close()

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(db_file),
            "--format",
            "json",
            "--verify-chain",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 1
    assert "verification" in result.stderr.lower()


def test_audit_export_help_lists_flags() -> None:
    """``asap audit export --help`` exposes store, db, and format options."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["audit", "export", "--help"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "--store" in result.stdout
    assert "--db" in result.stdout
    assert "--format" in result.stdout
    assert "--verify-chain" in result.stdout


def test_audit_export_invalid_format_rejected(sqlite_audit_db: Path) -> None:
    """``--format xml`` is rejected up-front with a BadParameter exit."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "xml",
        ],
    )
    assert result.exit_code != 0
    assert "must be 'json', 'csv', or 'jsonl'" in (result.stderr + result.stdout)


def test_audit_export_invalid_limit_rejected(sqlite_audit_db: Path) -> None:
    """``--limit 0`` fails validation before any IO."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--limit",
            "0",
        ],
    )
    assert result.exit_code != 0
    assert "at least 1" in (result.stderr + result.stdout)


def test_audit_export_unknown_store_rejected(tmp_path: Path) -> None:
    """``--store postgres`` surfaces a BadParameter (only sqlite/memory are supported)."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "postgres",
            "--db",
            str(tmp_path / "x.db"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code != 0
    assert "sqlite" in (result.stderr + result.stdout).lower()


def test_audit_export_sqlite_requires_db(tmp_path: Path) -> None:
    """``--store sqlite`` without ``--db`` is a configuration error."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["audit", "export", "--store", "sqlite", "--format", "json"],
    )
    assert result.exit_code != 0
    assert "--db" in (result.stderr + result.stdout)


def test_audit_export_memory_store_returns_empty_list() -> None:
    """``--store memory`` prints an empty JSON array (fresh per-process store)."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["audit", "export", "--store", "memory", "--format", "json"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert json.loads(result.stdout.strip()) == []


def test_audit_export_since_until_trailing_z_parsed(sqlite_audit_db: Path) -> None:
    """``--since`` / ``--until`` accept trailing-Z ISO-8601 (treated as UTC)."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "json",
            "--since",
            "2026-04-01T12:00:00Z",
            "--until",
            "2026-04-01T12:00:00Z",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout.strip())
    assert len(data) == 1
    assert data[0]["operation"] == "fixture.op.0"


def test_audit_export_filter_by_urn_returns_matching_entries(sqlite_audit_db: Path) -> None:
    """``--urn`` filters rows to a single agent."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "json",
            "--urn",
            "urn:asap:agent:cli-fixture",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout.strip())
    assert len(data) == 3
    assert all(row["agent_urn"] == "urn:asap:agent:cli-fixture" for row in data)


def test_audit_export_csv_uses_unix_line_endings(sqlite_audit_db: Path) -> None:
    """CSV output is deterministic on Linux/mac CI — no embedded CRLF."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "csv",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert "\r\n" not in result.stdout


def test_audit_export_invalid_since_rejected(sqlite_audit_db: Path) -> None:
    """Unparseable ISO-8601 in ``--since`` fails with a ValueError surfaced as BadParameter."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(sqlite_audit_db),
            "--format",
            "json",
            "--since",
            "not-a-date",
        ],
    )
    assert result.exit_code != 0


def test_audit_export_fixture_ids_match_store(tmp_path: Path) -> None:
    """Exported ``id`` values match the sealed entries from the fixture."""
    db_file = tmp_path / "audit_ids.db"
    sealed = asyncio.run(_seed_sqlite_audit_store(db_file))
    expected_ids = {e.id for e in sealed}

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "audit",
            "export",
            "--store",
            "sqlite",
            "--db",
            str(db_file),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.stdout + result.stderr
    data = json.loads(result.stdout.strip())
    exported_ids = {str(e["id"]) for e in data}
    assert exported_ids == expected_ids
