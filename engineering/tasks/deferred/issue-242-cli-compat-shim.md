# Issue #242: CLI `_compat.py` shim

**Issue**: [#242](https://github.com/adriannoes/asap-protocol/issues/242)
**Branch**: `refactor/cli-compat-shim-242`
**Depends on**: PR #241 merged (v2.5.1 S3 cli split)

## Relevant Files

### New Files
- `src/asap/cli/_compat.py` — Legacy public-symbol re-exports (`DEFAULT_SCHEMAS_DIR`, `export_all_schemas`, `_repl_namespace`)
- `tests/cli/test_compat.py` — Contract tests for shim + trimmed `cli/__init__.py` surface

### Modified Files
- `src/asap/cli/__init__.py` — Remove legacy re-exports; `__all__` = `["app", "main"]`; ≤80 LOC
- `tests/test_cli.py` — Repoint legacy imports to `asap.cli._compat` (L14, L1099, L1109)

## Tasks

### [x] 1.0 Contract tests (TDD red)

- [x] 1.1 Write `tests/cli/test_compat.py` (7 cases)
  - **What**: `__all__` on `_compat` and `cli/__init__`; canonical object identity; legacy symbols absent from `asap.cli`; LOC ceiling; REPL namespace smoke
  - **Verify**: `uv run pytest tests/cli/test_compat.py -v --tb=short` fails until implementation lands

### [x] 2.0 Implement shim

- [x] 2.1 Create `src/asap/cli/_compat.py`
  - **What**: Docstring + 3 re-exports from canonical modules + `__all__`
  - **Verify**: `test_compat_all_exports`, `test_compat_symbols_are_canonical_objects` green

- [x] 2.2 Trim `src/asap/cli/__init__.py`
  - **What**: Remove legacy imports/re-exports; keep Typer wiring only
  - **Verify**: `test_cli_init_line_count_within_ceiling`, `test_cli_init_does_not_export_legacy_symbols` green

### [x] 3.0 Update consumers

- [x] 3.1 Repoint `tests/test_cli.py` imports to `asap.cli._compat`
  - **Verify**: `tests/test_cli.py` + `tests/cli/` + `tests/test_cli_edge_cases.py` green

### [x] 4.0 Verification gates

- [x] 4.1 Full CLI pytest suite
- [x] 4.2 `ruff check src/asap/cli/ tests/cli/test_compat.py`
- [x] 4.3 `mypy src/asap/cli/`
- [x] 4.4 Smoke: `asap --version`, `asap --help`

## Acceptance Checklist

- [x] `src/asap/cli/_compat.py` with docstring + `__all__`
- [x] `src/asap/cli/__init__.py` ≤ 80 LOC
- [x] `from asap.cli._compat import DEFAULT_SCHEMAS_DIR, export_all_schemas, _repl_namespace` resolves
- [x] `asap.cli` does **not** export legacy symbols at root
- [x] Re-exports are canonical objects (`is` identity)
- [x] `tests/cli/test_compat.py` green (7 cases)
- [x] CLI test suites green; `ruff` + `mypy` clean
- [x] `asap --version` / `asap --help` OK
