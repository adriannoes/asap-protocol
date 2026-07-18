# Sprint S4: Telemetry operations (v2.5.4)

**PRD**: DIST-004 (D4)  
**Branch**: `feat/v2.5.4-s4-telemetry` → **`release/2.5.4`**  
**Depends on**: [S0](./sprint-S0-scope-lock.md)  
**Status**: Planned  
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

- [ ] **5.1 Expand collectors**
  - [ ] npm: ensure aggregate covers `@asap-protocol/client`, `@asap-protocol/mastra`, `@asap-protocol/openai-agents`
  - [ ] PyPI: ensure aggregate covers `asap-protocol`, `asap-compliance`
  - [ ] Update `tests/scripts/test_collect_npm.py`, `test_collect_pypi.py`, `test_aggregate.py` as needed

- [ ] **5.2 Guide-view proxy documentation**
  - [ ] Document in `docs/maintainers/telemetry.md` that guide views use GitHub collectors + site CTA metrics
  - [ ] Explicitly state MkDocs plugin is out of scope

- [ ] **5.3 Runbook & CI**
  - [ ] Refresh `docs/maintainers/telemetry.md` for weekly ops + required env vars (`TELEMETRY_GITHUB_TOKEN`, optional site endpoint/token)
  - [ ] Confirm `.github/workflows/telemetry-weekly.yml` supports `workflow_dispatch`
  - [ ] Run aggregate once (local or dispatch) → produces `private/telemetry/dashboard.md` (or document blocker)
  - [ ] Do **not** enable cron until secrets verified

- [ ] **5.4 No public UI**
  - [ ] Verify no new `/metrics` (or similar) route under `apps/web`
  - [ ] Keep `/api/telemetry` as existing ingestion only

---

## Skip / defer condition

If secrets or capacity block completion, mark DIST-004 **deferred** on the roadmap with a one-paragraph note before S5. Do not invent a dashboard to force a green check.

---

## Acceptance criteria

- [ ] npm ≥3 and PyPI ≥2 packages in aggregate defaults/config
- [ ] Runbook describes proxies + how to run aggregate
- [ ] At least one successful maintainer/CI dispatch **or** documented secrets gap
- [ ] Tests for collectors/aggregate green
- [ ] No new public metrics UI
- [ ] DIST-004 satisfied **or** explicit deferral recorded

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| — | — | — | — |

## Relevant files

- `scripts/telemetry/collect_npm.py`
- `scripts/telemetry/collect_pypi.py`
- `scripts/telemetry/collect_github.py`
- `scripts/telemetry/collect_registry.py`
- `scripts/telemetry/aggregate.py`
- `docs/maintainers/telemetry.md`
- `.github/workflows/telemetry-weekly.yml`
- `apps/web/src/app/api/telemetry/route.ts`
- `tests/scripts/test_collect_npm.py`, `test_collect_pypi.py`, `test_aggregate.py`
