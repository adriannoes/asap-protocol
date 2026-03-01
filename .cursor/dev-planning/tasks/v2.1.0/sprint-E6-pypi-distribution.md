# Sprint E6: PyPI Distribution

> **Goal**: Publish asap-protocol 2.1.0 to PyPI; CI on tag
> **Prerequisite**: Sprints E1–E5 complete
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` — Version, optional deps
- `src/asap/__init__.py` — Runtime __version__ (kept in sync with pyproject.toml)
- `.github/workflows/release.yml` — Publish to PyPI on tag push (v*), Docker, GitHub Release
- `CHANGELOG.md` — Release notes

---

## Trigger / Enables / Depends on

**Trigger:** Maintainer tags release (e.g. `v2.1.0`) and pushes.

**Enables:** `pip install asap-protocol` and `pip install asap-protocol[mcp]` for end users.

**Depends on:** Sprints E1–E5 complete; pyproject.toml has optional deps (Sprint E3.1).

---

## [x] Setup (one-time)

- **PyPI authentication**: The publish workflow (`.github/workflows/release.yml`) uses **Trusted Publishing** (OIDC). Configure the publisher once on PyPI for this repo; no `PYPI_API_TOKEN` secret needed. Alternatively, you can use a repository secret **`PYPI_API_TOKEN`** and pass it to the action if not using Trusted Publishing.

---

## Acceptance Criteria

- [ ] `asap-protocol` 2.1.0 published to PyPI
- [ ] Optional groups `[mcp]`, `[langchain]`, `[crewai]`, `[llamaindex]`, `[smolagents]`, `[openclaw]` work
- [ ] CI publishes on tag push `v*`

---

## [x] Task 6.1: Bump version to 2.1.0

- [x] **6.1.1** Update version in pyproject.toml
  - **File**: `pyproject.toml` (modify)
  - **What**: Set `version = "2.1.0"` in `[project]`.
  - **Why**: PKG-002 — semantic versioning.
  - **Verify**: `uv run python -c "import asap; print(asap.__version__)"` or `hatch version` shows 2.1.0.

---

## [x] Task 6.2: Create PyPI publish GitHub Action

**Note:** Implemented in existing `.github/workflows/release.yml` (trigger on tags `v*`, uv build, pypa/gh-action-pypi-publish with Trusted Publishing). No separate `publish-pypi.yml` added to avoid duplicate publish.

- [x] **6.2.1** Create workflow file and trigger
  - **File**: `.github/workflows/release.yml` (existing)
  - **What**: Trigger on `push` tags matching `v*` (e.g. `v2.1.0`). Job: checkout, setup Python (uv), install deps.
  - **Why**: PKG-004 — CI auto-publish.
  - **Verify**: Push tag `v2.1.0` triggers workflow.

- [x] **6.2.2** Add build step
  - **File**: `.github/workflows/release.yml`
  - **What**: `uv build` produces wheel and sdist in `dist/`; asap-compliance built and copied to `dist/`.
  - **Verify**: Build step succeeds; dist/ contains .whl and .tar.gz.

- [x] **6.2.3** Add publish step
  - **File**: `.github/workflows/release.yml`
  - **What**: `pypa/gh-action-pypi-publish` with Trusted Publishing (`id-token: write`). No `PYPI_API_TOKEN` required when Trusted Publishing is configured on PyPI for asap-protocol (and asap-compliance).
  - **Verify**: Tag push triggers publish; configure Trusted Publishing on PyPI if not already done.

---

## [x] Task 6.3: Verify optional dependency groups

- [x] **6.3.1** Validate extras install
  - **File**: `pyproject.toml` (verify)
  - **What**: Ensure `[project.optional-dependencies]` has mcp, langchain, crewai, llamaindex, smolagents, openclaw. Run `uv pip install .[<extra>]` for each in a clean env. Fix any version conflicts.
  - **Why**: PKG-003 — `pip install asap-protocol[<extra>]` works safely.
  - **Verify**: `uv pip install .[mcp]`, `.[langchain]`, `.[llamaindex]`, `.[smolagents]`, `.[crewai]`, `.[openclaw]` all succeed.

---

## [x] Task 6.4: Update CHANGELOG and release notes

- [x] **6.4.1** Add v2.1.0 section to CHANGELOG
  - **File**: `CHANGELOG.md` (modify)
  - **What**: Add `## [2.1.0]` section with: Consumer SDK (MarketClient, ResolvedAgent), Framework Integrations (LangChain, CrewAI, LlamaIndex, SmolAgents, Vercel AI SDK, MCP, OpenClaw), Registry UX (category/tags, usage snippets), Agent Revocation, PyPI distribution. Follow Keep a Changelog format.
  - **Why**: Release documentation.
  - **Verify**: CHANGELOG reflects all v2.1 features; date and link to compare.

---

## Definition of Done

- [x] `pip install asap-protocol` works (verified from repo; PyPI after publish)
- [x] `pip install asap-protocol[<extra>]` works for all frameworks (verified in 6.3.1)
- [ ] Tag `v2.1.0` triggers publish workflow (verify after push + tag)
- [x] CHANGELOG updated
