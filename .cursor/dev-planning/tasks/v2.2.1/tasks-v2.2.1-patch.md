# Tasks: v2.2.1 Carry-over Patch — Sprint Index

**Status: 🟡 PLANNED** — Targets the carry-over identified in the v2.2.0 audit (2026-04-17).

Based on [PRD v2.2.1 Patch](../../../product-specs/prd/prd-v2.2.1-patch.md). Strict carry-over scope: no new protocol surface area.

## Prerequisites
- [x] v2.2.0 released and stable (tag `v2.2.0`, 2026-04-15)
- [x] No active security incident
- [ ] `pip-audit` and `npm audit` clean on `main` (continuous)

## Sprint Plan

| Sprint | Focus | PRD Sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S1** | [Real WebAuthn Verification](./sprint-S1-webauthn.md) | §4.1 (WAUTH-001..008) | P0 | 🟡 |
| **S2** | [Compliance & Audit CLIs + Maintenance](./sprint-S2-clis.md) | §4.2 (CLI-COMP), §4.3 (CLI-AUD), §4.4 (MAINT) | P1/P2 | 🟡 |
| **S3** | Release v2.2.1 | — | — | 🟡 |

## Dependency Graph

```
S1 (WebAuthn) ──► S2 (CLIs + Maintenance) ──► S3 (Release)
```

S1 and S2 are independent and may run in parallel if two contributors are available.

## Definition of Done (v2.2.1)

- [ ] WAUTH-001..008 implemented and tested with real `webauthn` library
- [ ] `asap compliance-check --url ...` CLI subcommand available and documented
- [ ] `asap audit export --since ... --format {json,csv,jsonl}` CLI subcommand available and documented
- [ ] Test coverage ≥90% for new modules
- [ ] `uv run mypy src/` passes with zero errors
- [ ] `uv run ruff check .` passes
- [ ] `uv run pytest` green (no flakes)
- [ ] `pip-audit` clean (or documented overrides in `pyproject.toml`)
- [ ] CHANGELOG.md updated under `[2.2.1]`
- [ ] `pyproject.toml` and `src/asap/__init__.py` bumped to `2.2.1`
- [ ] `docs/migration.md` updated with WebAuthn extra installation note
- [ ] `docs/cli.md` updated with `compliance-check` and `audit export` subcommands
- [ ] Tag `v2.2.1` created on `main`
- [ ] `asap-protocol==2.2.1` published to PyPI
- [ ] GitHub Release v2.2.1 published with notes
- [ ] Docker `ghcr.io/adriannoes/asap-protocol:v2.2.1` and `:latest` rebuilt

## Estimated Effort

| Sprint | Effort |
|--------|--------|
| S1 WebAuthn | 3–5 days (1 contributor) |
| S2 CLIs + Maintenance | 2–3 days (1 contributor) |
| S3 Release | 0.5 day |

Total target: **1–2 weeks** end-to-end.

## Carry-over Source

- **SELF-002** (PRD v2.2 §4.5): WebAuthn placeholder → real implementation
- **COMP-006** (PRD v2.2 §4.12): `asap compliance-check` CLI
- **AUD-005** (PRD v2.2 §4.13): Audit export CLI
- Routine dependency CVE sweep (continuation of pip-audit/Dependabot triage)
