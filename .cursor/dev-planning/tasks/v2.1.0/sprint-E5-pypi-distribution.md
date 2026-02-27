# Sprint E5: PyPI Distribution

> **Goal**: Publish asap-protocol 2.1.0 to PyPI; CI on tag
> **Prerequisite**: Sprints E1–E4 complete
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` — Version, optional deps
- `.github/workflows/publish-pypi.yml` — Publish workflow
- `CHANGELOG.md` — Release notes

---

## Trigger / Enables / Depends on

**Trigger:** Maintainer tags release (e.g. `v2.1.0`) and pushes.

**Enables:** `pip install asap-protocol` and `pip install asap-protocol[mcp]` for end users.

**Depends on:** Sprints E1–E4 complete; pyproject.toml has optional deps (Sprint E3.1).

---

## Acceptance Criteria

- [ ] `asap-protocol` 2.1.0 published to PyPI
- [ ] Optional groups `[mcp]`, `[langchain]`, `[crewai]` work
- [ ] CI publishes on tag push `v*`

---

## Task 5.1: Bump version to 2.1.0

- [ ] **5.1.1** Update version in pyproject.toml
  - **File**: `pyproject.toml` (modify)
  - **What**: Set `version = "2.1.0"` in `[project]`.
  - **Why**: PKG-002 — semantic versioning.
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` or `hatch version` shows 2.1.0.

---

## Task 5.2: Create PyPI publish GitHub Action

- [ ] **5.2.1** Create workflow file and trigger
  - **File**: `.github/workflows/publish-pypi.yml` (create new)
  - **What**: Trigger on `push` tags matching `v*` (e.g. `v2.1.0`). Job: checkout, setup Python (uv), install deps.
  - **Why**: PKG-004 — CI auto-publish.
  - **Pattern**: Standard PyPI workflow; see pypa/gh-action-pypi-publish docs.
  - **Verify**: Push tag `v2.1.0-test`; workflow triggers (can skip publish step for dry-run).

- [ ] **5.2.2** Add build step
  - **File**: `.github/workflows/publish-pypi.yml`
  - **What**: Run `uv build` or `hatch build` to produce wheel and sdist in `dist/`. Artifact or pass to publish step.
  - **Why**: Build artifacts for PyPI.
  - **Verify**: Build step succeeds; dist/ contains .whl and .tar.gz.

- [ ] **5.2.3** Add publish step
  - **File**: `.github/workflows/publish-pypi.yml`
  - **What**: Use `pypa/gh-action-pypi-publish` with `PYPI_API_TOKEN` secret. Or `twine upload dist/*`. Only run on tags (not PRs).
  - **Why**: PKG-004 — publish to PyPI.
  - **Verify**: Actual publish requires token; dry-run: workflow completes without token error on non-publish jobs.

---

## Task 5.3: Verify optional dependency groups

- [ ] **5.3.1** Validate extras install
  - **File**: `pyproject.toml` (verify)
  - **What**: Ensure `[project.optional-dependencies]` has mcp, langchain, crewai. Run `uv pip install .[mcp]`, `.[langchain]`, `.[crewai]` in clean env. Fix any version conflicts.
  - **Why**: PKG-003 — `pip install asap-protocol[mcp]` works.
  - **Verify**: `uv pip install .[mcp]` and `uv pip install .[langchain]` succeed.

---

## Task 5.4: Update CHANGELOG and release notes

- [ ] **5.4.1** Add v2.1.0 section to CHANGELOG
  - **File**: `CHANGELOG.md` (modify)
  - **What**: Add `## [2.1.0]` section with: Consumer SDK (MarketClient, ResolvedAgent), Framework Integrations (LangChain, CrewAI, MCP), Registry UX (category/tags), Agent Revocation, PyPI distribution. Follow Keep a Changelog format.
  - **Why**: Release documentation.
  - **Verify**: CHANGELOG reflects all v2.1 features; date and link to compare.

---

## Definition of Done

- [ ] `pip install asap-protocol` works
- [ ] `pip install asap-protocol[mcp]` works
- [ ] Tag `v2.1.0` triggers publish workflow
- [ ] CHANGELOG updated
