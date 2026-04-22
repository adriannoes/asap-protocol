"""`asap audit export` — export tamper-evident audit entries from a store."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional

import typer

from asap.economics.audit import (
    AuditChainBroken,
    AuditEntry,
    InMemoryAuditStore,
    SQLiteAuditStore,
)


def _parse_iso_datetime(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def _make_store(store: str, db: Optional[Path]) -> InMemoryAuditStore | SQLiteAuditStore:
    normalized = store.strip().lower()
    if normalized == "sqlite":
        if db is None:
            raise typer.BadParameter("--db is required when --store is sqlite")
        return SQLiteAuditStore(db_path=str(db))
    if normalized == "memory":
        return InMemoryAuditStore()
    raise typer.BadParameter("--store must be 'sqlite' or 'memory'")


def _entry_payloads(entries: list[AuditEntry]) -> list[dict[str, object]]:
    return [e.model_dump(mode="json") for e in entries]


def _render_json(entries: list[AuditEntry]) -> str:
    return json.dumps(_entry_payloads(entries), indent=2)


def _render_jsonl(entries: list[AuditEntry]) -> str:
    lines = [json.dumps(row, separators=(",", ":")) for row in _entry_payloads(entries)]
    return "\n".join(lines) + ("\n" if lines else "")


def _render_csv(entries: list[AuditEntry]) -> str:
    buf = io.StringIO()
    fieldnames = ("id", "timestamp", "operation", "agent_urn", "details", "prev_hash", "hash")
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in _entry_payloads(entries):
        line = {
            "id": str(row["id"]),
            "timestamp": str(row["timestamp"]),
            "operation": str(row["operation"]),
            "agent_urn": str(row["agent_urn"]),
            "details": json.dumps(row["details"], sort_keys=True, default=str),
            "prev_hash": str(row["prev_hash"]),
            "hash": str(row["hash"]),
        }
        writer.writerow(line)
    return buf.getvalue()


async def _run_export(
    store: InMemoryAuditStore | SQLiteAuditStore,
    *,
    agent_urn: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
    limit: int,
    output_format: str,
    verify_chain: bool,
) -> str:
    if verify_chain:
        ok = await store.verify_chain()
        if not ok:
            raise AuditChainBroken("audit hash chain verification failed")

    entries = await store.query(
        agent_urn=agent_urn,
        start=since,
        end=until,
        limit=limit,
        offset=0,
    )
    fmt = output_format.strip().lower()
    if fmt == "json":
        return _render_json(entries)
    if fmt == "jsonl":
        return _render_jsonl(entries)
    if fmt == "csv":
        return _render_csv(entries)
    raise RuntimeError(f"unexpected format: {fmt!r}")


def register_audit_export_commands(root: typer.Typer) -> None:
    audit_app = typer.Typer(help="Tamper-evident audit log operations.")
    root.add_typer(audit_app, name="audit")

    @audit_app.command(
        "export",
        help="Export audit log entries to stdout (JSON, JSONL, or CSV).",
    )
    def audit_export(
        store: str = typer.Option(
            ...,
            "--store",
            help="Backing store: sqlite (file) or memory (empty in-process).",
        ),
        db: Annotated[
            Optional[Path],
            typer.Option("--db", help="SQLite database path (required for --store sqlite)."),
        ] = None,
        since: Annotated[
            Optional[str],
            typer.Option(
                "--since", help="Include entries with timestamp >= this ISO-8601 instant."
            ),
        ] = None,
        until: Annotated[
            Optional[str],
            typer.Option(
                "--until", help="Include entries with timestamp <= this ISO-8601 instant."
            ),
        ] = None,
        urn: Annotated[
            Optional[str],
            typer.Option("--urn", help="Filter by agent URN (agent_urn column)."),
        ] = None,
        limit: int = typer.Option(
            10_000,
            "--limit",
            help="Maximum number of entries to export (ordered by insertion).",
        ),
        output_format: str = typer.Option(
            "json",
            "--format",
            "-f",
            help="Output format: json (array), jsonl (one object per line), or csv.",
        ),
        verify_chain: bool = typer.Option(
            False,
            "--verify-chain",
            help="Verify full-store hash chain before export; exit 1 if tampered.",
        ),
    ) -> None:
        if limit < 1:
            raise typer.BadParameter("--limit must be at least 1")

        fmt = output_format.strip().lower()
        if fmt not in ("json", "csv", "jsonl"):
            raise typer.BadParameter("--format must be 'json', 'csv', or 'jsonl'")

        try:
            since_dt = _parse_iso_datetime(since) if since else None
            until_dt = _parse_iso_datetime(until) if until else None
        except ValueError as exc:
            raise typer.BadParameter(f"invalid ISO-8601 timestamp: {exc}") from exc
        agent_urn = urn.strip() if urn and urn.strip() else None

        backing = _make_store(store, db)

        async def _run() -> str:
            return await _run_export(
                backing,
                agent_urn=agent_urn,
                since=since_dt,
                until=until_dt,
                limit=limit,
                output_format=fmt,
                verify_chain=verify_chain,
            )

        try:
            text = asyncio.run(_run())
        except AuditChainBroken as exc:
            typer.echo("Audit hash chain verification failed (possible tampering).", err=True)
            raise typer.Exit(1) from exc
        except ValueError as exc:
            raise typer.BadParameter(str(exc)) from exc
        except OSError as exc:
            typer.echo(f"Could not read audit database: {exc}", err=True)
            raise typer.Exit(2) from exc

        typer.echo(text, nl=not text.endswith("\n"))
