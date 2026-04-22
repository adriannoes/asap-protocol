# ASAP CLI reference

The `asap` command-line interface ships with the `asap-protocol` package. It covers JSON schema export, validation, observability helpers, Ed25519 keys and manifests, delegation tokens, **Compliance Harness v2** checks over HTTP(S), and **audit log export** (SQLite or in-memory store).

Run `asap --help` or `asap <command> --help` for the canonical flag list for your installed version.

## `asap compliance-check`

Runs [Compliance Harness v2](guides/compliance-testing.md) against a deployed ASAP agent by calling its HTTP(S) base URL (same checks as `run_compliance_harness_v2` in-process, but remote).

### Usage

```bash
asap compliance-check --url https://your-agent.example.com
```

### Options

| Option | Description |
|--------|-------------|
| `--url` | **Required.** Agent base URL (scheme + host, optional port), e.g. `http://127.0.0.1:8000`. |
| `--output` | `text` (default) or `json`. JSON output matches `ComplianceReport` and is validated against its JSON Schema before printing. |
| `--exit-on-fail` | If set, exit with code **1** when any harness check fails (score &lt; 1.0). Without it, the process exits **0** even when checks fail (report still shows failures). |
| `--timeout` | HTTP client timeout in seconds (default: `60`). Must be positive. |
| `--asap-version` | If set, sent as the `ASAP-Version` header on requests. |

### Exit codes

| Code | Meaning |
|------|--------|
| `0` | Success: score is 1.0, **or** `--exit-on-fail` is not set (even if some checks failed). |
| `1` | Harness reported failures and `--exit-on-fail` is set (score &lt; 1.0). |
| `2` | Transport error: connection refused, timeout, or other HTTP client / OS errors. |

Use `--exit-on-fail` in CI to block deploys or merges when the agent no longer passes the harness. See [CI example: compliance gate](ci-compliance.md).

### Related

- [Compliance testing guide](guides/compliance-testing.md) — what the harness validates.
- [CI: compliance gate](ci-compliance.md) — GitHub Actions pattern.

## `asap audit export`

Exports [tamper-evident audit](audit.md) rows from a `SQLiteAuditStore` file or an empty in-process `InMemoryAuditStore`. Output goes to **stdout**; redirect with `>` to write a file.

### Usage

```bash
asap audit export --store sqlite --db ./asap_state.db --format json
asap audit export --store sqlite --db ./asap_state.db --format jsonl > audit.jsonl
```

### Options

| Option | Description |
|--------|-------------|
| `--store` | **Required.** `sqlite` (file-backed) or `memory` (empty store for a one-off process). |
| `--db` | **Required** when `--store sqlite`: path to the SQLite database file. |
| `--since` | Include entries with `timestamp` ≥ this ISO-8601 instant (`Z` suffix allowed). |
| `--until` | Include entries with `timestamp` ≤ this ISO-8601 instant. |
| `--urn` | Filter by `agent_urn`. |
| `--limit` | Max rows to export, in insertion order (default: `10000`). |
| `--format` / `-f` | `json` (default): JSON **array** of entries. `jsonl`: one JSON object per line. `csv`: header + rows; `details` is a JSON **string** in the cell. |
| `--verify-chain` | Before exporting, verify the **full** store hash chain; exit **1** if any row fails (e.g. tampered DB). |

### Exit codes

| Code | Meaning |
|------|--------|
| `0` | Export completed (verification passed if `--verify-chain` was set). |
| `1` | `--verify-chain` was set and the chain is broken. |
| `2` | I/O error reading the database (e.g. permission denied). |

### Related

- [Audit log guide](audit.md) — model, formats, and tamper-detection workflow.

## Other commands (summary)

| Area | Commands |
|------|----------|
| Schemas | `export-schemas`, `list-schemas`, `show-schema`, `validate-schema` |
| Keys & manifests | `keys generate`, `manifest sign`, `manifest verify`, `manifest info` |
| Delegation | `delegation create`, `delegation revoke` |
| Compliance / audit | `compliance-check`, `audit export` |
| Dev / ops | `trace`, `repl` |

Ed25519 and manifest workflows are also described in [Identity Signing](guides/identity-signing.md).
