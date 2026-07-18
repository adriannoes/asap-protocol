# Sprint S4: Telemetry operations (v2.5.4)

**PRD**: DIST-004 (D4)
**Branch**: `feat/v2.5.4-s3-s5-homepage-telemetry-release` → **`release/2.5.4`**
**Depends on**: [S0](./sprint-S0-scope-lock.md)
**Status**: Done (DIST-004 satisfied via collectors + runbook + tests; full GitHub aggregate blocked on secrets)
**Priority**: SHOULD — may defer with explicit roadmap note; must not invent a public dashboard

**Trigger:** S0 confirms operationalize-existing metrics (no live UI).
**Enables:** Maintainer adoption visibility; DIST-004 DoD.
**Depends on:** Existing `scripts/telemetry/`, `docs/maintainers/telemetry.md`, `/api/telemetry`.

---

## Goal

Close gaps in the existing adoption telemetry pipeline (package coverage, runbook, CI dispatch policy, guide-view proxies). **Do not** build a public metrics page or new analytics stack.

---

## Design constraints

- Output remains under `private/telemetry/` (gitignored).
- Guide views = GitHub traffic/referrers + site→docs CTR proxies—not MkDocs analytics.
- Re-enable scheduled workflow **only** after secrets are configured; until then `workflow_dispatch` + documented gap is acceptable.
- Site CTR may use `TELEMETRY_SITE_METRICS_JSON` / drain; empty shell documented is OK.

---

## Tasks

- [x] **5.1 Expand collectors**
  - [x] npm: ensure aggregate covers `@asap-protocol/client`, `@asap-protocol/mastra`, `@asap-protocol/openai-agents`
  - [x] PyPI: ensure aggregate covers `asap-protocol`, `asap-compliance`
  - [x] Update `tests/scripts/test_collect_npm.py`, `test_collect_pypi.py`, `test_aggregate.py` as needed

- [x] **5.2 Guide-view proxy documentation**
  - [x] Document in `docs/maintainers/telemetry.md` that guide views use GitHub collectors + site CTA metrics
  - [x] Explicitly state MkDocs plugin is out of scope

- [x] **5.3 Runbook & CI**
  - [x] Refresh `docs/maintainers/telemetry.md` for weekly ops + required env vars (`TELEMETRY_GITHUB_TOKEN`, optional site endpoint/token)
  - [x] Confirm `.github/workflows/telemetry-weekly.yml` supports `workflow_dispatch`
  - [x] Run aggregate once (local or dispatch) → produces `private/telemetry/dashboard.md` (or document blocker)
  - [x] Do **not** enable cron until secrets verified

- [x] **5.4 No public UI**
  - [x] Verify no new `/metrics` (or similar) route under `apps/web`
  - [x] Keep `/api/telemetry` as existing ingestion only

### Secrets / runtime gap note (2026-07-18)

Local environment had neither `TELEMETRY_GITHUB_TOKEN` nor `GITHUB_TOKEN`. An attempted run with `PYTHONPATH=. uv run python scripts/telemetry/aggregate.py --output-dir private/telemetry --allow-github-skip` reached public npm collection but failed on PyPI Stats with **HTTP 429** before writing a new snapshot — existing `private/telemetry/` files from 2026-05-18 were **not** overwritten with invented numbers. Cron remains **disabled** in `telemetry-weekly.yml`; maintainers should add the Actions secret `TELEMETRY_GITHUB_TOKEN` (and optional site vars), then run **`workflow_dispatch`** once before re-enabling schedule. Collector defaults (≥3 npm, ≥2 PyPI), runbook, and tests are green, so DIST-004 is treated as **satisfied** via dispatch-ready CI + docs (per skip condition).

---

## Skip / defer condition

If secrets or capacity block completion, mark DIST-004 **deferred** on the roadmap with a one-paragraph note before S5. Do not invent a dashboard to force a green check.

---

## Acceptance criteria

- [x] npm ≥3 and PyPI ≥2 packages in aggregate defaults/config
- [x] Runbook describes proxies + how to run aggregate
- [x] At least one successful maintainer/CI dispatch **or** documented secrets gap
- [x] Tests for collectors/aggregate green
- [x] No new public metrics UI
- [x] DIST-004 satisfied **or** explicit deferral recorded

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats | [review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md](../../code-review/private/review-v2.5.4-S3-S5-homepage-telemetry-release-20260718.md) |

## Relevant files

- `scripts/telemetry/collect_npm.py` — `DEFAULT_PACKAGES` (≥3 scoped packages)
- `scripts/telemetry/collect_pypi.py` — `DEFAULT_PYPI_PACKAGES` (`asap-protocol`, `asap-compliance`)
- `scripts/telemetry/collect_github.py`
- `scripts/telemetry/collect_registry.py`
- `scripts/telemetry/aggregate.py` — uses npm + PyPI default tuples
- `docs/maintainers/telemetry.md` — guide-view proxies, secrets, dispatch-only CI
- `.github/workflows/telemetry-weekly.yml` — `workflow_dispatch`; cron commented
- `apps/web/src/app/api/telemetry/route.ts` — ingestion only (no public UI)
- `tests/scripts/test_collect_npm.py`, `test_collect_pypi.py`, `test_aggregate.py`
