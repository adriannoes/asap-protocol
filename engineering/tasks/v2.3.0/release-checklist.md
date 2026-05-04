# Release checklist — v2.3.0

Manual steps after the `release/2.3.0` PR merges to `main`. Automation references: `.github/workflows/release.yml`, `.github/workflows/publish-typescript.yml`.

## Pre-tag (maintainer)

- [ ] Confirm CI green on `main` at the merge commit (`ci.yml`).
- [ ] Re-run local gates from [SECURITY.md](../../../SECURITY.md): `uv run pytest`, `pnpm -r test` / root `pnpm test`, `uv run pip-audit …`, `npm audit` in `apps/web` (and repo root if applicable).
- [ ] Verify `CHANGELOG.md` contains `## [2.3.0]` with the release date.

## Tag and GitHub

- [ ] `git tag v2.3.0 <merge-commit-sha>` (or tag from `main` after merge) and `git push origin v2.3.0`.
- [ ] Confirm `release.yml` validates the tag, publishes **asap-protocol** wheels to PyPI, copies **asap-compliance** artifacts (`skip-existing` if unchanged), builds Docker (`ghcr.io/<repo>:v2.3.0` and `:latest`), and creates the GitHub Release notes from the changelog section.
- [ ] Confirm `publish-typescript.yml` publishes `@asap-protocol/client@2.3.0` with provenance (OIDC).

## Post-publish smoke

- [ ] Clean venv: `pip install asap-protocol==2.3.0` (and `'asap-protocol[openapi]==2.3.0'` if testing the adapter).
- [ ] Clean directory: `npm install @asap-protocol/client@2.3.0`.
- [ ] `docker pull ghcr.io/<owner>/asap-protocol:v2.3.0` (image name per workflow).

## Deferred (not blocking tag)

- [ ] Adoption metrics dashboard (Sprint S5 §4.5) — Grafana/GitHub Pages per product plan.
- [ ] GitHub issues for deferred backlog items (Registry API, Intent Search, Orchestration, DeepEval) with label `deferred`.
