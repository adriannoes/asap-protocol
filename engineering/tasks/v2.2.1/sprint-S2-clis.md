# Sprint S2: Compliance & Audit CLIs + Maintenance

**PRD**: [v2.2.1 §4.2, §4.3, §4.4](../../../product/prd/prd-v2.2.1-patch.md) — CLI-COMP-001..005 (P1), CLI-AUD-001..005 (P1), MAINT-001..004 (P2)
**Branch**: `feat/cli-compliance-audit`
**PR Scope**: Two new CLI subcommands (`compliance-check`, `audit export`) plus dependency hygiene refresh.
**Depends on**: v2.2.0 (`testing/compliance.py::run_compliance_harness_v2`, `economics/audit.py::AuditStore`)

## Relevant Files

### New Files
- `src/asap/testing/asgi_factory.py` — `make_compliance_test_app()` for harness/CLI tests (loopback server)
- `tests/cli/__init__.py` — package marker for CLI tests
- `src/asap/cli/compliance_check.py` — `asap compliance-check` subcommand
- `src/asap/cli/audit_export.py` — `asap audit export` subcommand
- `tests/cli/test_compliance_check.py` — CLI tests via `click.testing.CliRunner` (or argparse harness)
- `tests/cli/test_audit_export.py` — CLI tests
- `docs/cli.md` — CLI reference (`compliance-check` + other commands)
- `docs/ci-compliance.md` — Example CI workflow using the new CLI
- `docs/audit.md` — Audit log usage and export guide
- `apps/example-agent/pyproject.toml` — Workspace path dep on `asap-protocol`; dev pytest deps (task 3.2)
- `apps/example-agent/uv.lock` — Reproducible env for example-agent CI (task 3.2)
- `apps/example-agent/tests/test_compliance.py` — Harness v2 baseline `score == 1.0` (task 3.2)
- `apps/example-agent/src/example_agent/__init__.py` — Minimal package for hatch build (task 3.2)
- `apps/example-agent/README.md` — Purpose of example-agent + baseline (task 3.2)

### Modified Files
- `.github/workflows/ci.yml` — Trigger paths + `test-python` step for example-agent harness (task 3.2)
- `apps/web/package.json` — Next.js / ESLint patch bumps + `npm overrides` (`micromatch.picomatch`) after CVE sweep (task 3.1)
- `apps/web/package-lock.json` — Lockfile refresh from `npm audit fix` / install (task 3.1)
- `src/asap/cli/__init__.py` — Main Typer app (migrated from `cli.py`); register `compliance-check` and later `audit export`
- `src/asap/testing/compliance.py` — `run_compliance_harness_with_client`, `run_compliance_harness_v2_from_url`
- `docs/index.md` — Cross-links to `cli.md` and `ci-compliance.md`
- `pyproject.toml` — Version `2.2.1` (task 4.1)
- `uv.lock` — Root lockfile after version bump (task 4.1)
- `src/asap/__init__.py` — `__version__` `2.2.1` (task 4.1)
- `CHANGELOG.md` — `[2.2.1] - 2026-04-21`; empty `[Unreleased]` (task 4.2)
- `README.md` — v2.2.1 release line; `compliance-check` + `asap audit export` in CLI snippet (task 4.3)
- `apps/example-agent/uv.lock` — Pins `asap-protocol` 2.2.1 after bump (task 4.1)

## Tasks

### [x] 1.0 `asap compliance-check` CLI

- [x] 1.1 Write failing CLI test (TDD)
  - **File**: `tests/cli/test_compliance_check.py` (create)
  - **What**: Spin up an in-process ASAP test app (`testing/asgi_factory.py`), call `asap compliance-check --url http://testserver`, assert exit code 0 and JSON report
  - **Verify**: `uv run pytest tests/cli/test_compliance_check.py` fails (red)

- [x] 1.2 Implement subcommand
  - **File**: `src/asap/cli/compliance_check.py` (create)
  - **What**: Flags `--url`, `--output {text,json}`, `--exit-on-fail`, `--timeout`, `--asap-version`. Internally calls `run_compliance_harness_v2` against a remote URL via `httpx.AsyncClient`. Renders text or JSON.
  - **Verify**: Test green; `--output json` produces valid JSON validated against `ComplianceReport.model_json_schema()`

- [x] 1.3 Register in `asap.cli` (package `src/asap/cli/`)
  - **File**: `src/asap/cli/__init__.py` + `src/asap/cli/compliance_check.py` (package split; former `cli.py`)
  - **What**: Add `compliance-check` to the subcommand dispatcher; preserve existing commands
  - **Verify**: `asap --help` lists the new subcommand; `asap compliance-check --help` shows flags

- [x] 1.4 Exit code semantics
  - **What**: 0 if score == 1.0 OR `--exit-on-fail` not set; 1 if any check fails AND `--exit-on-fail` set; 2 if transport/connection error
  - **Verify**: Three test cases covering each exit-code branch

- [x] 1.5 Documentation + example CI
  - **Files**: `docs/cli.md` (modify), `docs/ci-compliance.md` (create)
  - **What**: Subcommand reference + GitHub Actions example using `--exit-on-fail` to gate deployments
  - **Verify**: Cross-link from CHANGELOG and README

### [x] 2.0 `asap audit export` CLI

- [x] 2.1 Write failing CLI test (TDD)
  - **File**: `tests/cli/test_audit_export.py` (create)
  - **What**: Pre-seed a `SQLiteAuditStore` with fixtures, call `asap audit export --store sqlite --db <path> --format json`, assert output contains all entries with valid hash chain
  - **Verify**: Red (`No such command 'audit'`)

- [x] 2.2 Implement subcommand
  - **File**: `src/asap/cli/audit_export.py` (create)
  - **What**: Flags `--store {sqlite,memory}`, `--db <path>`, `--since`, `--until`, `--urn`, `--limit`, `--format {json,csv,jsonl}`, `--verify-chain`. Output to stdout (use `>` for file).
  - **Verify**: Three formats produce expected shapes; `--verify-chain` exits non-zero on tampered fixture

- [x] 2.3 Register in Typer CLI package
  - **File**: `src/asap/cli/__init__.py` (modify; package replaces legacy `cli.py`)
  - **What**: Add `audit` group with `export` subcommand
  - **Verify**: `asap audit export --help` (see `tests/cli/test_audit_export.py::test_audit_export_help_lists_flags`)

- [x] 2.4 Documentation
  - **Files**: `docs/cli.md`, `docs/audit.md` (create)
  - **What**: Reference table + audit log model overview + tamper-detection example
  - **Verify**: Cross-link from CHANGELOG ([Unreleased] bullet + `docs/index.md`)

### [x] 3.0 Maintenance

- [x] 3.1 Refresh dependency CVE sweep
  - **File**: `pyproject.toml` (modify if needed)
  - **What**: Run `uv run pip-audit`. If any unresolved CVE: bump dependency or document override. Same for `apps/web/package.json` via `npm audit`.
  - **Verify**: Both audits clean (or overrides documented in `pyproject.toml [tool.uv.overrides]`)

- [x] 3.2 Re-run Compliance Harness v2 baseline
  - **File**: `apps/example-agent/tests/test_compliance.py` (modify if exists; else create)
  - **What**: Pin Compliance Harness v2 baseline to score 1.0; fail CI if regression
  - **Verify**: Test green on `apps/example-agent`

- [x] 3.3 Refresh `docs/error-codes.md` if any code added/changed
  - **What**: No-op if no codes changed; otherwise sync the registry table with `errors.py`
  - **Verify**: Manual diff vs `errors.py` (registry matches `errors.py` RPC_* band; no doc edit)

### [x] 4.0 Release Prep

- [x] 4.1 Bump version
  - **Files**: `pyproject.toml`, `src/asap/__init__.py`
  - **What**: `2.2.0` → `2.2.1`
  - **Verify**: `uv sync` regenerates lock; `uv run python -c "import asap; print(asap.__version__)"` prints `2.2.1`

- [x] 4.2 CHANGELOG entry
  - **File**: `CHANGELOG.md`
  - **What**: Move `[Unreleased]` content to new `## [2.2.1] - <date>` section; group Added/Security/Changed
  - **Verify**: Markdown lint clean; cross-links to PRs

- [x] 4.3 README CLI table update
  - **File**: `README.md`
  - **What**: Two new rows: `compliance-check`, `audit export`
  - **Verify**: Visual review

## Acceptance Criteria

- [x] All tests pass (TDD red → green) — `tests/cli/` + `apps/example-agent` verified this session
- [ ] Coverage ≥90% on new CLI modules (`compliance_check` / `audit_export` ~72–76%; widen tests or narrow scope)
- [x] `uv run mypy src/asap/cli/` clean
- [x] `uv run ruff check src/asap/cli/` clean
- [x] `pip-audit` clean (or overrides documented)
- [x] `npm audit` clean for `apps/web` (or overrides documented)
- [ ] CLI help text reviewed manually for clarity
- [x] Docs cross-linked

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Existing CLI uses argparse, new code might prefer click | Match existing style — inspect `src/asap/cli.py` first; do not introduce a new framework |
| `audit export --format csv` ambiguity for nested `details` field | Document: nested dicts JSON-stringified inline in CSV; use `--format jsonl` for machine consumption |
| `compliance-check` against remote agent could leak secrets in error output | Sanitize headers in error messages; never echo Authorization values |
