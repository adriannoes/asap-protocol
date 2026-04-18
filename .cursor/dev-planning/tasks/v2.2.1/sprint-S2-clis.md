# Sprint S2: Compliance & Audit CLIs + Maintenance

**PRD**: [v2.2.1 §4.2, §4.3, §4.4](../../../product-specs/prd/prd-v2.2.1-patch.md) — CLI-COMP-001..005 (P1), CLI-AUD-001..005 (P1), MAINT-001..004 (P2)
**Branch**: `feat/cli-compliance-audit`
**PR Scope**: Two new CLI subcommands (`compliance-check`, `audit export`) plus dependency hygiene refresh.
**Depends on**: v2.2.0 (`testing/compliance.py::run_compliance_harness_v2`, `economics/audit.py::AuditStore`)

## Relevant Files

### New Files
- `src/asap/cli/compliance_check.py` — `asap compliance-check` subcommand
- `src/asap/cli/audit_export.py` — `asap audit export` subcommand
- `tests/cli/test_compliance_check.py` — CLI tests via `click.testing.CliRunner` (or argparse harness)
- `tests/cli/test_audit_export.py` — CLI tests
- `docs/ci-compliance.md` — Example CI workflow using the new CLI
- `docs/audit.md` — Audit log usage and export guide

### Modified Files
- `src/asap/cli.py` — Register new subcommands `compliance-check` and `audit export`
- `docs/cli.md` — Document the new subcommands
- `pyproject.toml` — Bump version to `2.2.1`; refresh dependency overrides if any new CVEs surfaced
- `src/asap/__init__.py` — Bump `__version__` to `2.2.1`
- `CHANGELOG.md` — `[Unreleased]` → `[2.2.1]` section with grouped Added/Security/Changed
- `README.md` — Mention the two new subcommands in the CLI table

## Tasks

### 1.0 `asap compliance-check` CLI

- [ ] 1.1 Write failing CLI test (TDD)
  - **File**: `tests/cli/test_compliance_check.py` (create)
  - **What**: Spin up an in-process ASAP test app (`testing/asgi_factory.py`), call `asap compliance-check --url http://testserver`, assert exit code 0 and JSON report
  - **Verify**: `uv run pytest tests/cli/test_compliance_check.py` fails (red)

- [ ] 1.2 Implement subcommand
  - **File**: `src/asap/cli/compliance_check.py` (create)
  - **What**: Flags `--url`, `--output {text,json}`, `--exit-on-fail`, `--timeout`, `--asap-version`. Internally calls `run_compliance_harness_v2` against a remote URL via `httpx.AsyncClient`. Renders text or JSON.
  - **Verify**: Test green; `--output json` produces valid JSON validated against `ComplianceReport.model_json_schema()`

- [ ] 1.3 Register in `src/asap/cli.py`
  - **File**: `src/asap/cli.py` (modify)
  - **What**: Add `compliance-check` to the subcommand dispatcher; preserve existing commands
  - **Verify**: `asap --help` lists the new subcommand; `asap compliance-check --help` shows flags

- [ ] 1.4 Exit code semantics
  - **What**: 0 if score == 1.0 OR `--exit-on-fail` not set; 1 if any check fails AND `--exit-on-fail` set; 2 if transport/connection error
  - **Verify**: Three test cases covering each exit-code branch

- [ ] 1.5 Documentation + example CI
  - **Files**: `docs/cli.md` (modify), `docs/ci-compliance.md` (create)
  - **What**: Subcommand reference + GitHub Actions example using `--exit-on-fail` to gate deployments
  - **Verify**: Cross-link from CHANGELOG and README

### 2.0 `asap audit export` CLI

- [ ] 2.1 Write failing CLI test (TDD)
  - **File**: `tests/cli/test_audit_export.py` (create)
  - **What**: Pre-seed a `SQLiteAuditStore` with fixtures, call `asap audit export --store sqlite --db <path> --format json`, assert output contains all entries with valid hash chain
  - **Verify**: Red

- [ ] 2.2 Implement subcommand
  - **File**: `src/asap/cli/audit_export.py` (create)
  - **What**: Flags `--store {sqlite,memory}`, `--db <path>`, `--since`, `--until`, `--urn`, `--limit`, `--format {json,csv,jsonl}`, `--verify-chain`. Output to stdout (use `>` for file).
  - **Verify**: Three formats produce expected shapes; `--verify-chain` exits non-zero on tampered fixture

- [ ] 2.3 Register in `src/asap/cli.py`
  - **File**: `src/asap/cli.py` (modify)
  - **What**: Add `audit` group with `export` subcommand
  - **Verify**: `asap audit export --help`

- [ ] 2.4 Documentation
  - **Files**: `docs/cli.md`, `docs/audit.md` (create)
  - **What**: Reference table + audit log model overview + tamper-detection example
  - **Verify**: Cross-link from CHANGELOG

### 3.0 Maintenance

- [ ] 3.1 Refresh dependency CVE sweep
  - **File**: `pyproject.toml` (modify if needed)
  - **What**: Run `uv run pip-audit`. If any unresolved CVE: bump dependency or document override. Same for `apps/web/package.json` via `npm audit`.
  - **Verify**: Both audits clean (or overrides documented in `pyproject.toml [tool.uv.overrides]`)

- [ ] 3.2 Re-run Compliance Harness v2 baseline
  - **File**: `apps/example-agent/tests/test_compliance.py` (modify if exists; else create)
  - **What**: Pin Compliance Harness v2 baseline to score 1.0; fail CI if regression
  - **Verify**: Test green on `apps/example-agent`

- [ ] 3.3 Refresh `docs/error-codes.md` if any code added/changed
  - **What**: No-op if no codes changed; otherwise sync the registry table with `errors.py`
  - **Verify**: Manual diff vs `errors.py`

### 4.0 Release Prep

- [ ] 4.1 Bump version
  - **Files**: `pyproject.toml`, `src/asap/__init__.py`
  - **What**: `2.2.0` → `2.2.1`
  - **Verify**: `uv sync` regenerates lock; `uv run python -c "import asap; print(asap.__version__)"` prints `2.2.1`

- [ ] 4.2 CHANGELOG entry
  - **File**: `CHANGELOG.md`
  - **What**: Move `[Unreleased]` content to new `## [2.2.1] - <date>` section; group Added/Security/Changed
  - **Verify**: Markdown lint clean; cross-links to PRs

- [ ] 4.3 README CLI table update
  - **File**: `README.md`
  - **What**: Two new rows: `compliance-check`, `audit export`
  - **Verify**: Visual review

## Acceptance Criteria

- [ ] All tests pass (TDD red → green)
- [ ] Coverage ≥90% on new CLI modules
- [ ] `uv run mypy src/asap/cli/` clean
- [ ] `uv run ruff check src/asap/cli/` clean
- [ ] `pip-audit` clean (or overrides documented)
- [ ] `npm audit` clean for `apps/web` (or overrides documented)
- [ ] CLI help text reviewed manually for clarity
- [ ] Docs cross-linked

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing CLI uses argparse, new code might prefer click | Match existing style — inspect `src/asap/cli.py` first; do not introduce a new framework |
| `audit export --format csv` ambiguity for nested `details` field | Document: nested dicts JSON-stringified inline in CSV; use `--format jsonl` for machine consumption |
| `compliance-check` against remote agent could leak secrets in error output | Sanitize headers in error messages; never echo Authorization values |
