# Tasks: ASAP v0.5.0 Sprint S5 (Detailed)

> **Sprint**: S5 - Release Preparation
> **Duration**: Flexible (2-3 days)
> **Goal**: Final testing, documentation, and v0.5.0 release

---

## Relevant Files

- `CHANGELOG.md` - v0.5.0 release notes
- `.github/release-notes-v0.5.0.md` - NEW: Detailed notes
- `README.md` - Version and feature updates
- All files in `src/asap/examples/` - Verify examples
- All files in `docs/` - Review documentation

---

## Task 5.1: Security Audit

- [ ] 5.1.1 Run pip-audit
  - Command: `uv run pip-audit`
  - Expected: No vulnerabilities
  - If issues: Update dependencies or document false positives

- [ ] 5.1.2 Run bandit security linter
  - Install: `uv add --dev bandit`
  - Command: `uv run bandit -r src/`
  - Expected: No high/medium severity issues
  - If issues: Fix or document rationale

- [ ] 5.1.3 Manual security checklist
  - [ ] All CRIT tasks completed (Task 1.0 ✅)
  - [ ] All HIGH tasks completed (Tasks 3.0-6.0)
  - [ ] Secure defaults enabled (HTTPS, auth, rate limiting)
  - [ ] Error messages sanitized (no sensitive data)
  - [ ] Authentication tested
  - [ ] Rate limiting tested
  - [ ] Timestamp validation tested

**Acceptance**: Zero critical vulnerabilities, checklist complete

---

## Task 5.2: Testing & Quality

- [ ] 5.2.1 Run full test suite
  - Command: `uv run pytest -v`
  - Expected: All tests pass (543+ original + new)
  - Coverage: Run `uv run pytest --cov=src`
  - Expected: ≥95% coverage

- [ ] 5.2.2 Run benchmarks
  - Command: `uv run pytest benchmarks/ -v`
  - Compare to v0.1.0 baseline (save results)
  - Expected: <5% regression

- [ ] 5.2.3 Run linters
  - Ruff: `uv run ruff check src/ tests/`
  - Format: `uv run ruff format src/ tests/`
  - Mypy: `uv run mypy --strict src/`
  - Expected: All pass with zero errors

**Acceptance**: All tests pass, coverage ≥95%, linters clean

---

## Task 5.3: Compatibility Testing

- [ ] 5.3.1 Test upgrade from v0.1.0
  - Create virtual env: `python -m venv /tmp/test-upgrade`
  - Install v0.1.0: `pip install asap-protocol==0.1.0`
  - Create simple agent using v0.1.0 API
  - Upgrade: `pip install --upgrade /path/to/v0.5.0/dist/*.whl`
  - Run agent: Should work without code changes
  - Verify: New security features are opt-in

- [ ] 5.3.2 Test all examples
  - Run: `uv run python -m asap.examples.echo_agent` (background)
  - Run: `uv run python -m asap.examples.coordinator` (background)
  - Run: `uv run python -m asap.examples.run_demo`
  - Expected: All examples work without errors

- [ ] 5.3.3 Update examples if needed
  - If breaking changes: Update example code
  - If new features: Add example usage
  - Update: `src/asap/examples/README.md`

**Acceptance**: Smooth upgrade path, all examples work

---

## Task 5.4: Documentation Review

- [ ] 5.4.1 Review and update README.md
  - Update version badge to v0.5.0
  - Add security features to "Why ASAP?" section
  - Update installation instructions if needed
  - Check all links work

- [ ] 5.4.2 Review docs/ directory
  - Check: docs/security.md (should be comprehensive)
  - Check: docs/transport.md (retry docs added)
  - Check: All other docs still accurate
  - Fix broken links or outdated info

- [ ] 5.4.3 Update CHANGELOG.md
  - Add section: `## [0.5.0] - 2026-MM-DD`
  - Subsections: Added, Changed, Security
  - List all security improvements from S1-S4
  - List issues closed (#7, #9, #10, #13)
  - Note: Zero breaking changes

- [ ] 5.4.4 Create migration guide
  - File: `docs/migration.md` (might exist, extend it)
  - Section: "## Upgrading from v0.1.0 to v0.5.0"
  - Content: New config options, opt-in features
  - Note: Fully backward compatible

**Acceptance**: All docs reviewed, CHANGELOG complete, migration guide exists

---

## Task 5.5: Release Preparation

- [ ] 5.5.1 Create detailed release notes
  - File: `.github/release-notes-v0.5.0.md`
  - Sections:
    - Security Hardening Highlights
    - New Features (rate limiting, HTTPS, timestamps)
    - Upgrade Instructions
    - Breaking Changes (should be none)
    - Contributors (thank everyone)

- [ ] 5.5.2 Review open PRs
  - Check: https://github.com/adriannoes/asap-protocol/pulls
  - Merge: Ready PRs that should be in v0.5.0
  - Defer: Non-critical PRs to v0.6.0 or v1.0.0
  - Close: Stale PRs with comment

- [ ] 5.5.3 Verify pyproject.toml metadata
  - Version: Should still be "0.1.0" (will update for release)
  - Description: Accurate?
  - Keywords: Complete?
  - Classifiers: Still "Alpha"

- [ ] 5.5.4 Update version to 0.5.0
  - File: `pyproject.toml` → `version = "0.5.0"`
  - File: `src/asap/__init__.py` → `__version__ = "0.5.0"`

- [ ] 5.5.5 Final commit before tag
  - Command: `git add pyproject.toml src/asap/__init__.py CHANGELOG.md`
  - Command: `git commit -m "chore(release): prepare v0.5.0 release"`

**Acceptance**: Release notes ready, version updated, metadata correct

---

## Task 5.6: Build and Publish

- [ ] 5.6.1 Build distribution
  - Command: `uv build`
  - Expected: Creates dist/ with .whl and .tar.gz
  - Verify: Files exist and sizes reasonable

- [ ] 5.6.2 Test build locally
  - Install in clean env: `pip install dist/*.whl`
  - Import: `python -c "import asap; print(asap.__version__)"`
  - Expected: Prints "0.5.0"

- [ ] 5.6.3 Tag release
  - Command: `git tag v0.5.0`
  - Push: `git push origin v0.5.0`

- [ ] 5.6.4 Publish to PyPI
  - Command: `uv publish`
  - Verify: https://pypi.org/project/asap-protocol/0.5.0/
  - Check: Package page loads, metadata correct

- [ ] 5.6.5 Create GitHub release
  - Visit: https://github.com/adriannoes/asap-protocol/releases/new
  - Tag: v0.5.0
  - Title: "v0.5.0 - Security-Hardened Release"
  - Body: Paste from `.github/release-notes-v0.5.0.md`
  - Assets: Attach dist/*.whl and dist/*.tar.gz
  - Check: "This is a pre-release" (still alpha)
  - Publish

**Acceptance**: Built, published to PyPI, GitHub release created

---

## Task 5.7: Communication

- [ ] 5.7.1 Update README badges
  - Update version badge (if exists)
  - Update PyPI link

- [ ] 5.7.2 Announce on GitHub
  - Post to: GitHub Discussions (Announcements)
  - Title: "v0.5.0 Released - Security Hardening"
  - Content: Highlight security improvements
  - Link to release notes

- [ ] 5.7.3 Close resolved issues
  - Comment on #7, #9, #10, #13
  - Message: "Fixed in v0.5.0"
  - Close issues

- [ ] 5.7.4 Thank contributors
  - Comment on merged PRs
  - Thank everyone who reported issues

**Acceptance**: Announcement posted, issues closed, contributors thanked

---

**Sprint S5 Definition of Done**:
- [ ] All CRIT+HIGH tasks completed
- [ ] Zero breaking changes
- [ ] CI passes
- [ ] v0.5.0 on PyPI
- [ ] GitHub release published
- [ ] Coverage ≥95%
- [ ] Performance regression <5%

**Total Sub-tasks**: ~30
