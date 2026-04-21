# Tasks: v2.2.1 Carry-over Patch — Sprint Index

**Status: 🟢 READY FOR CODE REVIEW** — S1 and S2 implementation tasks are marked complete in their sprint files; workspace carries **2.2.1** release prep (CHANGELOG, version, README). **S3** (tag / PyPI / GitHub Release / Docker) stays **pending merge to `main`**.

Targets the carry-over identified in the v2.2.0 audit (2026-04-17).

Based on [PRD v2.2.1 Patch](../../../product-specs/prd/prd-v2.2.1-patch.md). Strict carry-over scope: no new protocol surface area.

## Prerequisites

- [x] v2.2.0 released and stable (tag `v2.2.0`, 2026-04-15)
- [x] No active security incident
- [x] `pip-audit` and `npm audit` clean on integration branch — **S2 §3.1** (re-validate on `main` after merge; Dependabot remains continuous)

## Sprint Plan

| Sprint | Focus | PRD Sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S1** | [Real WebAuthn Verification](./sprint-S1-webauthn.md) | §4.1 (WAUTH-001..008) | P0 | 🟢 **Done** (all tasks `[x]` in sprint file) |
| **S2** | [Compliance & Audit CLIs + Maintenance](./sprint-S2-clis.md) | §4.2 (CLI-COMP), §4.3 (CLI-AUD), §4.4 (MAINT), §4.0 Release Prep | P1/P2 | 🟢 **Done** (incl. §4.0) |
| **S3** | [Release v2.2.1](./sprint-S3-release.md) | — | — | ⏳ **Pending** merge + tag + publish |

## Dependency Graph

```
S1 (WebAuthn) ──► S2 (CLIs + Maintenance) ──► S3 (Release)
```

**Development order**: S1 and S2 can be worked **in parallel** (separate branches/PRs). **Release order**: merge both (and any fixes), confirm CI on `main`, then run **S3** (tag, PyPI, GitHub Release, Docker).

## Definition of Done (v2.2.1)

### Implementation (expected before merge; spot-checks 2026-04-21 on integration branch)

- [x] WAUTH-001..008 implemented and tested with real `webauthn` library — see [S1](./sprint-S1-webauthn.md)
- [x] `asap compliance-check --url ...` CLI subcommand available and documented — see [S2](./sprint-S2-clis.md) §1
- [x] `asap audit export --since ... --format {json,csv,jsonl}` CLI subcommand available and documented — see [S2](./sprint-S2-clis.md) §2
- [ ] Test coverage ≥90% for **new CLI modules** (`compliance_check`, `audit_export`) — **gap** (~72–76% with current tests); widen tests or adjust DoD before calling patch “closed”
- [x] `uv run mypy src/` passes with zero errors — verified locally (`143` files)
- [x] `uv run ruff check .` passes — verified locally
- [ ] `uv run pytest` green on **full** suite — **confirm in PR CI / before merge** (spot: `tests/cli/`, `apps/example-agent` green)
- [x] `pip-audit` clean (or documented overrides in `pyproject.toml`) — S2 §3.1
- [x] `CHANGELOG.md` updated under **`[2.2.1]`** — S2 §4.2
- [x] `pyproject.toml` and `src/asap/__init__.py` bumped to **`2.2.1`** — S2 §4.1
- [x] `docs/migration.md` updated with WebAuthn extra installation note — S1 §4.2 + release notes
- [x] `docs/cli.md` updated with `compliance-check` and `audit export` subcommands — S2 §1.5 / §2.4
- [ ] Manual pass: **CLI help text** clarity (`asap compliance-check --help`, `asap audit export --help`) — [S2 acceptance](./sprint-S2-clis.md) still open

### Release (S3 — after merge to `main`)

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
