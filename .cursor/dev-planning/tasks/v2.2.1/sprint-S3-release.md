# Sprint S3: Release v2.2.1

**PRD**: [v2.2.1 Patch](../../../product-specs/prd/prd-v2.2.1-patch.md) — ship carry-over; no new protocol surface.
**Depends on**: S1 (WebAuthn) and S2 (CLIs + maintenance) **merged to `main`** and green on CI.

S2 §4.0 *Release Prep* covers **version bump**, **CHANGELOG**, and **README** in-repo — **completed in the integration workspace** (see [S2 sprint](./sprint-S2-clis.md) §4.0). This sprint is the **post-merge release operation**: tag, package publish, distribution images, and public release notes.

## Status for code review

| Gate | State |
|------|--------|
| S2 §4.0 (version / CHANGELOG / README) | **Done** on branch — re-verify no conflicts after S1 + S2 merge order you choose |
| S3 (tag / PyPI / GitHub / Docker) | **Not started** — run only after `main` contains the release commit |

## Checklist (maps to [Definition of Done](./tasks-v2.2.1-patch.md#definition-of-done-v221))

### A — Before tagging (reviewer / merge)

- [ ] **`main` green** after merge: PR CI passes (quality + tests), or locally `uv run pytest`, `uv run ruff check .`, `uv run mypy src/` on the merged result
- [x] **`pip-audit` / `npm audit`** clean or overrides documented — satisfied per S2 §3.1; **re-run once on `main`** post-merge
- [x] **Release artefacts in tree**: `pyproject.toml` + `src/asap/__init__.py` at **2.2.1**, `CHANGELOG.md` has **`## [2.2.1]`**, README CLI snippet includes **`compliance-check`** and **`audit export`**

### B — S3 execution (release operator, on `main` only)

- [ ] Tag **`v2.2.1`** on the release commit on `main`
- [ ] **`asap-protocol==2.2.1`** published to **PyPI**
- [ ] **GitHub Release** `v2.2.1` with notes (link CHANGELOG section)
- [ ] **Docker**: `ghcr.io/adriannoes/asap-protocol:v2.2.1` and `:latest` rebuilt per project release process

## Notes

- If S1 and S2 land as separate PRs, complete S2 §4.0 *before* tagging so `pyproject.toml` / `__version__` / CHANGELOG match the published artifact (already aligned in current workspace; resolve any merge conflict on CHANGELOG).
- Do not duplicate version-bump steps in S3; single source of truth is S2 task **4.1** unless you intentionally defer bumps to a dedicated “release only” PR after both features merge.
