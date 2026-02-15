# Manual Release Testing Checklist (v1.2.0)

Simulates a real user validating the ASAP Protocol before release.

**Last run**: 2026-02-15 — All checks passed ✅

## 1. Installation & Environment

- [x] `uv sync` succeeds
- [x] `asap --version` shows 1.2.0
- [x] Python 3.13+ detected

## 2. CLI Commands

- [x] `asap --help` works
- [x] `asap list-schemas` lists schemas
- [x] `asap keys generate -o /tmp/test-key.pem` creates Ed25519 keypair
- [x] `asap manifest sign` / `verify` / `info` work with sample manifest

## 3. Quick Demo

- [x] `uv run python -m asap.examples.run_demo` completes successfully (echo agent + coordinator)

## 4. Examples (smoke)

- [x] `uv run python -m asap.examples.echo_agent` starts (Ctrl+C to stop)
- [x] `run_demo` covers coordinator flow
- [x] Orchestration example available

## 5. Server + Client Flow

- [x] Start echo agent in background
- [x] Send task via ASAPClient (or coordinator)
- [x] Receive valid TaskResponse

## 6. Compliance Harness

- [x] asap-compliance in workspace (pythonpath)
- [x] `PYTHONPATH=src:.:asap-compliance uv run pytest asap-compliance/tests/` — 54 passed
- [x] Live handshake: `validate_handshake(ComplianceConfig(agent_url="http://127.0.0.1:8001"))` — PASS

## 7. Full Test Suite

- [x] `uv run pytest -n auto --tb=short` — 1940 passed, 5 skipped
- [ ] `uv run pytest --cov=src/asap --cov-report=term-missing` (optional)

## 8. Lint & Type Check

- [x] `uv run ruff check .` — All checks passed
- [x] `uv run ruff format --check .` — 258 files formatted
- [ ] `uv run mypy src/` (if applicable)
