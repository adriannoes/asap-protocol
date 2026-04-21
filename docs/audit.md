# Tamper-evident audit log

ASAP v2.2+ can record **append-only, hash-chained** audit entries when the transport is configured with an `AuditStore`. Each row links to the previous row’s digest so offline tampering (changing history without rewriting hashes) is detectable.

Implementation: `asap.economics.audit` (`AuditEntry`, `InMemoryAuditStore`, `SQLiteAuditStore`, `compute_entry_hash`).

## `AuditEntry` model

| Field | Role |
|--------|------|
| `id` | Unique row id (generated if omitted on append). |
| `timestamp` | When the event occurred (UTC-aware in normal use). |
| `operation` | Short operation label (e.g. `task.request`). |
| `agent_urn` | Agent identity for filtering and attribution. |
| `details` | JSON object with arbitrary metadata (sorted keys used in the hash). |
| `prev_hash` | Digest of the previous entry (`""` for the first row). |
| `hash` | SHA-256 over a canonical string: `prev_hash`, ISO `timestamp`, `operation`, and sorted JSON `details`. |

The server seals each append by recomputing `hash` from the tail of the chain; mutating an old `details` or `hash` without updating the whole suffix breaks verification.

## Verifying the chain

- **In code**: `await store.verify_chain()` returns `True` if every row matches `compute_entry_hash` in insertion order.
- **CLI**: [`asap audit export`](cli.md#asap-audit-export) with `--verify-chain` runs the same check on the **entire** store before printing results (filters such as `--urn` apply only to the export, not to verification).

## Exporting entries

Use the CLI to dump stdout for archiving or SIEM ingestion:

```bash
asap audit export --store sqlite --db ./asap_state.db --format json
```

Redirect to a file when needed:

```bash
asap audit export --store sqlite --db ./asap_state.db --format jsonl > audit.jsonl
```

Formats:

- **`json`**: A single JSON **array** of entry objects (good for small logs and jq).
- **`jsonl`**: One JSON object per line (streaming-friendly).
- **`csv`**: Header row plus one line per entry; the `details` column is a **JSON string** (nested structures are not split into extra columns). Prefer **jsonl** for machine pipelines.

See [CLI reference: `audit export`](cli.md#asap-audit-export) for all flags (`--since`, `--until`, `--urn`, `--limit`, `--verify-chain`).

## Tamper detection example

After a good export, suppose someone edits the SQLite file and changes `details` on an old row without updating `hash` and all following rows. The chain no longer matches:

```bash
asap audit export --store sqlite --db ./asap_state.db --format json --verify-chain
# stderr: Audit hash chain verification failed (possible tampering).
# exit code: 1
```

Without `--verify-chain`, the CLI still prints rows (which may be internally inconsistent); use `--verify-chain` in compliance or forensic checks when you need a hard gate.

## Related

- [CLI reference](cli.md) — `audit export` option table and exit codes.
- [CHANGELOG](../CHANGELOG.md) — release notes when audit or CLI behaviour changes.
