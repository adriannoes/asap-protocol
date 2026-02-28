# Sprint E6: PyPI Distribution

> **Goal**: Publish asap-protocol 2.1.0 to PyPI; CI on tag
> **Prerequisite**: Sprints E1–E5 complete
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

**Depends on:** Sprints E1–E5 complete; pyproject.toml has optional deps (Sprint E3.1).

---

## [x] Setup (one-time)

- **GitHub Repository secret for PyPI**: The publish workflow needs a token to upload to PyPI. Create it once in the repo:
  - Go to **GitHub → Repository → Settings → Secrets and variables → Actions**.
  - Click **Secrets** (not Variables — the token is sensitive).
  - Use **Repository secrets** (not Environment secrets unless you use a dedicated environment).
  - Add a secret named **`PYPI_API_TOKEN`** with the value of your PyPI API token (create at [pypi.org/manage/account/token/](https://pypi.org/manage/account/token/)).
  - The workflow references it as `${{ secrets.PYPI_API_TOKEN }}`.

---

## Acceptance Criteria

- [ ] `asap-protocol` 2.1.0 published to PyPI
- [ ] Optional groups `[mcp]`, `[langchain]`, `[crewai]`, `[llamaindex]`, `[smolagents]`, `[openclaw]` work
- [ ] CI publishes on tag push `v*`

---

## Task 6.1: Bump version to 2.1.0

- [ ] **6.1.1** Update version in pyproject.toml
  - **File**: `pyproject.toml` (modify)
  - **What**: Set `version = "2.1.0"` in `[project]`.
  - **Why**: PKG-002 — semantic versioning.
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` or `hatch version` shows 2.1.0.

---

## Task 6.2: Create PyPI publish GitHub Action

- [ ] **6.2.1** Create workflow file and trigger
  - **File**: `.github/workflows/publish-pypi.yml` (create new)
  - **What**: Trigger on `push` tags matching `v*` (e.g. `v2.1.0`). Job: checkout, setup Python (uv), install deps.
  - **Why**: PKG-004 — CI auto-publish.
  - **Pattern**: Standard PyPI workflow; see pypa/gh-action-pypi-publish docs.
  - **Verify**: Push tag `v2.1.0-test`; workflow triggers (can skip publish step for dry-run).

- [ ] **6.2.2** Add build step
  - **File**: `.github/workflows/publish-pypi.yml`
  - **What**: Run `uv build` or `hatch build` to produce wheel and sdist in `dist/`. Artifact or pass to publish step.
  - **Why**: Build artifacts for PyPI.
  - **Verify**: Build step succeeds; dist/ contains .whl and .tar.gz.

- [ ] **6.2.3** Add publish step
  - **File**: `.github/workflows/publish-pypi.yml`
  - **What**: Use `pypa/gh-action-pypi-publish` with the **Repository secret** `PYPI_API_TOKEN` (see [Setup (one-time)](#setup-one-time) above). Or `twine upload dist/*` passing the token. Only run on tags (not PRs).
  - **Why**: PKG-004 — publish to PyPI.
  - **Verify**: Actual publish requires `PYPI_API_TOKEN` in repo Secrets; dry-run: workflow completes without token error on non-publish jobs.

---

## Task 6.3: Verify optional dependency groups

- [ ] **6.3.1** Validate extras install
  - **File**: `pyproject.toml` (verify)
  - **What**: Ensure `[project.optional-dependencies]` has mcp, langchain, crewai, llamaindex, smolagents, openclaw. Run `uv pip install .[<extra>]` for each in a clean env. Fix any version conflicts.
  - **Why**: PKG-003 — `pip install asap-protocol[<extra>]` works safely.
  - **Verify**: `uv pip install .[mcp]`, `.[langchain]`, `.[llamaindex]`, `.[smolagents]`, `.[crewai]`, `.[openclaw]` all succeed.

---

## Task 6.4: Update CHANGELOG and release notes

- [ ] **6.4.1** Add v2.1.0 section to CHANGELOG
  - **File**: `CHANGELOG.md` (modify)
  - **What**: Add `## [2.1.0]` section with: Consumer SDK (MarketClient, ResolvedAgent), Framework Integrations (LangChain, CrewAI, LlamaIndex, SmolAgents, Vercel AI SDK, MCP, OpenClaw), Registry UX (category/tags, usage snippets), Agent Revocation, PyPI distribution. Follow Keep a Changelog format.
  - **Why**: Release documentation.
  - **Verify**: CHANGELOG reflects all v2.1 features; date and link to compare.

---

## Definition of Done

- [ ] `pip install asap-protocol` works
- [ ] `pip install asap-protocol[<extra>]` works for all frameworks
- [ ] Tag `v2.1.0` triggers publish workflow
- [ ] CHANGELOG updated
