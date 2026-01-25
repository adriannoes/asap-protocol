# Tasks: ASAP v1.0.0 Release (P13) - Detailed

> **Sprint**: P13 - v1.0.0 Release Preparation
> **Duration**: Flexible (5-7 days)
> **Goal**: Final testing, polish, and production release

---

## Relevant Files

- `CHANGELOG.md` - v1.0.0 release notes
- `.github/release-notes-v1.0.0.md` - NEW: Comprehensive release notes
- `README.md` - Update to "Stable" status
- `pyproject.toml` - Update version and classifiers
- `.cursor/dev-planning/retrospectives/v1.0.0-retro.md` - NEW: Retrospective
- All docs/ - Final review

---

## Task 13.1: Comprehensive Testing

- [ ] 13.1.1 Run full test suite
  - Command: `uv run pytest -v`
  - Expected: 800+ tests all pass
  - Coverage: ≥95%

- [ ] 13.1.2 Run all benchmarks
  - Load: `uv run locust -f benchmarks/load_test.py`
  - Property: `uv run pytest tests/properties/`
  - Chaos: `uv run pytest tests/chaos/`
  - Verify: All performance targets met

- [ ] 13.1.3 Run security audit
  - Pip-audit: `uv run pip-audit`
  - Bandit: `uv run bandit -r src/`
  - Expected: Zero critical vulnerabilities

- [ ] 13.1.4 Run linters
  - Ruff: `uv run ruff check src/ tests/`
  - Mypy: `uv run mypy --strict src/`
  - Expected: Zero errors

**Acceptance**: All quality checks pass

---

## Task 13.2: Documentation Review

- [ ] 13.2.1 Review all documentation files
  - README, CHANGELOG, CONTRIBUTING, SECURITY
  - docs/ directory (all files)
  - Fix: Broken links, outdated info

- [ ] 13.2.2 Test all examples
  - Run: All 10+ examples
  - Verify: No errors, output correct

- [ ] 13.2.3 Test upgrade paths
  - Test: v0.1.0 → v1.0.0
  - Test: v0.5.0 → v1.0.0
  - Verify: Smooth upgrades

**Acceptance**: All docs accurate, examples work, upgrades smooth

---

## Task 13.3: Release Preparation

- [ ] 13.3.1 Update CHANGELOG.md
  - Section: `## [1.0.0] - YYYY-MM-DD`
  - List: All changes since v0.5.0
  - Format: Keep a Changelog

- [ ] 13.3.2 Create comprehensive release notes
  - File: `.github/release-notes-v1.0.0.md`
  - Sections:
    - Major features (security, performance, DX)
    - Performance improvements (benchmarks)
    - Breaking changes (if any)
    - Migration guide
    - Contributors

- [ ] 13.3.3 Review and merge open PRs
  - Merge: Ready PRs for v1.0.0
  - Defer: Non-critical to v1.1.0
  - Close: Stale PRs

- [ ] 13.3.4 Update version
  - File: `pyproject.toml` → version = "1.0.0"
  - File: `src/asap/__init__.py` → __version__ = "1.0.0"
  - Classifier: "Development Status :: 5 - Production/Stable"

**Acceptance**: CHANGELOG complete, version updated

---

## Task 13.4: Build and Publish

- [ ] 13.4.1 Build distribution
  - Command: `uv build`
  - Verify: dist/ contains .whl and .tar.gz

- [ ] 13.4.2 Test build
  - Install in clean env
  - Import and verify version

- [ ] 13.4.3 Tag release
  - Command: `git tag v1.0.0 && git push origin v1.0.0`

- [ ] 13.4.4 Publish to PyPI
  - Command: `uv publish`
  - Verify: https://pypi.org/project/asap-protocol/1.0.0/

- [ ] 13.4.5 Create GitHub release
  - Tag: v1.0.0
  - Title: "v1.0.0 - Production-Ready Release"
  - Assets: Wheel and source dist
  - Status: **Stable** (not pre-release)

- [ ] 13.4.6 Publish Docker images
  - Push to ghcr.io
  - Tags: latest, v1.0.0, v1.0, v1

**Acceptance**: Published to PyPI, GitHub release, Docker images

---

## Task 13.5: Communication

- [ ] 13.5.1 Announce release
  - GitHub Discussions
  - Update README status
  - Social media (if applicable)

- [ ] 13.5.2 Update project status
  - README: "Alpha" → "Stable"
  - Badges: Update version

- [ ] 13.5.3 Close resolved issues
  - Comment: "Fixed in v1.0.0"
  - Thank contributors

**Acceptance**: Announcement posted, status updated

---

## Task 13.6: PRD Review & Retrospective

- [ ] 13.6.1 Final PRD review
  - Review: All remaining open questions (Q1-Q12)
  - Document: Decisions or defer to v1.1.0
  - Update: PRD Section 10 with all decisions

- [ ] 13.6.2 Create retrospective
  - File: `.cursor/dev-planning/retrospectives/v1.0.0-retro.md`
  - Content:
    - What went well
    - What could improve
    - Lessons learned
    - Metrics vs targets
    - Recommendations for v1.1.0

- [ ] 13.6.3 Schedule post-release review
  - Timeline: 2 weeks after release
  - Calendar: Set reminder
  - Agenda: Review Q7, Q9, Q10 based on community feedback

**Acceptance**: PRD complete, retrospective created, review scheduled

---

## Task 13.7: Mark Sprint P13 and v1.0.0 Complete

- [ ] 13.7.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P13 tasks (13.1-13.6) as complete `[x]`
  - Mark: Overall v1.0.0 as 38/38 (100%)

- [ ] 13.7.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion date

- [ ] 13.7.3 Update main tracking
  - File: `../../README.md`
  - Update: v1.0.0 status to "Released"
  - Add: Release date and PyPI link

- [ ] 13.7.4 Archive v1.0.0 milestone
  - Document: v1.0.0 completion
  - Update: Parent README

**Acceptance**: All tracking complete, v1.0.0 milestone closed

---

**P13 Definition of Done**:
- [ ] All tasks 13.1-13.7 completed
- [ ] All success metrics met
- [ ] 800+ tests passing
- [ ] v1.0.0 on PyPI
- [ ] GitHub release published
- [ ] Documentation 100% complete
- [ ] PRD fully reviewed
- [ ] Retrospective created
- [ ] Post-release review scheduled
- [ ] Progress tracked everywhere
- [ ] v1.0.0 marked as complete milestone

**Total Sub-tasks**: ~55
