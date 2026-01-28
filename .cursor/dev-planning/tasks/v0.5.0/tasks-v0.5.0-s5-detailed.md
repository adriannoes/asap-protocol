# Tasks: ASAP v0.5.0 Sprint S5 (Detailed)

> **Sprint**: S5 - Release Preparation
> **Duration**: Flexible (2-3 days)
> **Goal**: Final testing, documentation, and v0.5.0 release

---

## Relevant Files

- `CHANGELOG.md` - v0.5.0 release notes
- `.github/release-notes-v0.5.0.md` - NEW: Detailed notes
- `README.md` - Version and feature updates
- `src/asap/transport/validators.py` - S3 follow-up improvements
- `src/asap/models/constants.py` - Nonce TTL configuration
- All files in `src/asap/examples/` - Verify examples
- All files in `docs/` - Review documentation

---

## S3 Code Review Follow-ups

> These items were identified in PR #19 Code Review as Post-Merge improvements.
> Priority: Low - nice-to-have before release.

### Task 5.0.1: Add Empty Nonce String Validation

**Source**: [Sprint S3 Code Review - Section 3.2](../code-review/v0.5.0/sprint-s3-code-review.md)

- [ ] 5.0.1.1 Update nonce validation in validators.py
  - File: `src/asap/transport/validators.py`
  - Change: Reject empty string nonces
  - Current: `if not isinstance(nonce, str):`
  - Updated: `if not isinstance(nonce, str) or not nonce:`
  - Error message: "Nonce must be a non-empty string"

- [ ] 5.0.1.2 Add test for empty nonce rejection
  - File: `tests/transport/unit/test_validators.py`
  - Test: Empty string nonce raises InvalidNonceError
  - Verify: Error message indicates empty string issue

- [ ] 5.0.1.3 Commit
  - Command: `git commit -m "fix(validators): reject empty nonce strings"`

**Acceptance**: Empty nonce strings rejected with clear error message

---

### Task 5.0.2: Make Nonce TTL Configurable

**Source**: [Sprint S3 Code Review - Section 3.4](../code-review/v0.5.0/sprint-s3-code-review.md)

- [ ] 5.0.2.1 Add nonce TTL constant to constants.py
  - File: `src/asap/models/constants.py`
  - Add: `NONCE_TTL_SECONDS = MAX_ENVELOPE_AGE_SECONDS * 2  # 10 minutes`
  - Docstring: Explain relationship with envelope age

- [ ] 5.0.2.2 Update validate_envelope_nonce to use constant
  - File: `src/asap/transport/validators.py`
  - Import: `from asap.models.constants import NONCE_TTL_SECONDS`
  - Change: `mark_used(nonce, ttl_seconds=600)` → `mark_used(nonce, ttl_seconds=NONCE_TTL_SECONDS)`

- [ ] 5.0.2.3 Add test for TTL configuration
  - Verify: TTL matches expected value (2x envelope age)
  - Document: Why 2x provides safety margin

- [ ] 5.0.2.4 Commit
  - Command: `git commit -m "refactor(validators): derive nonce TTL from envelope age constant"`

**Acceptance**: Nonce TTL derived from `MAX_ENVELOPE_AGE_SECONDS`, documented

---

### Task 5.0.3: Implement Log Sanitization

**Issue**: [#12](https://github.com/adriannoes/asap-protocol/issues/12) - Security hardening - Sensitive data protection
**Priority**: MEDIUM (Security Review Task 7.0)

- [ ] 5.0.3.1 Identify sensitive data in logs
  - Review: `src/asap/transport/middleware.py` - token logging
  - Review: `src/asap/transport/server.py` - error logging (nonces, credentials)
  - Review: `src/asap/transport/client.py` - connection logging
  - List: All places where sensitive data could leak

- [ ] 5.0.3.2 Implement log sanitization utility
  - File: `src/asap/utils/sanitization.py` (NEW)
  - Function: `sanitize_token(token: str) -> str` - returns prefix only
  - Function: `sanitize_nonce(nonce: str) -> str` - returns first 8 chars + "..."
  - Function: `sanitize_url(url: str) -> str` - masks credentials in URLs

- [ ] 5.0.3.3 Apply sanitization to middleware
  - File: `src/asap/transport/middleware.py`
  - Replace: Direct token logging with sanitized version
  - Pattern: `logger.debug("auth", token_prefix=sanitize_token(token))`

- [ ] 5.0.3.4 Apply sanitization to server
  - File: `src/asap/transport/server.py`
  - Update: Nonce logging (already partial, complete it)
  - Update: Any credential-related logs

- [ ] 5.0.3.5 Add sanitization tests
  - File: `tests/utils/test_sanitization.py` (NEW)
  - Test: Token sanitization preserves prefix, hides rest
  - Test: Nonce sanitization truncates correctly
  - Test: URL sanitization masks passwords

- [ ] 5.0.3.6 Commit
  - Command: `git commit -m "feat(security): add log sanitization for sensitive data"`
  - Closes: Issue #12

**Acceptance**: No sensitive data (full tokens, credentials) in logs, Issue #12 closed

---

### Task 5.0.4: Add Missing Test Coverage

**Issue**: [#11](https://github.com/adriannoes/asap-protocol/issues/11) - Add missing test coverage

- [ ] 5.0.4.1 Run coverage report and identify gaps
  - Command: `uv run pytest --cov=src/asap --cov-report=html`
  - Open: `htmlcov/index.html`
  - Identify: Files with <90% coverage
  - List: Critical paths without tests

- [ ] 5.0.4.2 Prioritize coverage gaps
  - Priority 1: Security-critical code (auth, validation, HTTPS)
  - Priority 2: Error handling paths
  - Priority 3: Edge cases in transport layer
  - Document: Which gaps to address in v0.5.0 vs v1.0.0

- [ ] 5.0.4.3 Add tests for Priority 1 gaps
  - Focus: Uncovered branches in validators.py, middleware.py
  - Focus: Error paths in client.py, server.py
  - Goal: 95%+ coverage on security-critical modules

- [ ] 5.0.4.4 Add tests for Priority 2 gaps
  - Focus: Exception handling paths
  - Focus: Retry logic edge cases
  - Goal: 92%+ overall coverage

- [ ] 5.0.4.5 Commit
  - Command: `git commit -m "test: add missing test coverage for security-critical code"`
  - Closes: Issue #11

**Acceptance**: Coverage ≥95% on security modules, Issue #11 closed

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

- [ ] 5.5.6 Final Quality Gate Review (PRE-RELEASE GATE)
  > **CRITICAL**: This is the final checkpoint before release. Do not proceed until all items pass.
  
  - [ ] **Code Quality**:
    - [ ] `uv run ruff check src/ tests/` - 0 errors
    - [ ] `uv run mypy --strict src/` - 0 errors
    - [ ] `uv run ruff format --check src/ tests/` - already formatted
  
  - [ ] **Test Coverage**:
    - [ ] Run: `uv run pytest --cov=src/asap --cov-report=term-missing`
    - [ ] Overall coverage: ≥92%
    - [ ] Security modules (validators, middleware, auth): ≥95%
    - [ ] Transport layer (client, server): ≥90%
    - [ ] Review: Any uncovered lines are acceptable edge cases
  
  - [ ] **Test Stability**:
    - [ ] Run: `uv run pytest -x --count=3` (run 3 times, fail on first error)
    - [ ] All tests pass consistently (no flaky tests)
    - [ ] Run: `uv run pytest -n auto` (parallel execution)
    - [ ] Parallel tests pass without race conditions
  
  - [ ] **Security Verification**:
    - [ ] `uv run pip-audit` - 0 vulnerabilities
    - [ ] `uv run bandit -r src/ -ll` - 0 high/medium issues
    - [ ] Manual check: No secrets in codebase (`git grep -i password src/`)
    - [ ] Manual check: No sensitive data in logs (review sanitization)
  
  - [ ] **Documentation Completeness**:
    - [ ] All public APIs documented
    - [ ] All new features in docs/
    - [ ] CHANGELOG.md updated
    - [ ] README.md examples work
  
  - [ ] **Final Sign-off**:
    - [ ] All GitHub issues #11, #12, #13 closed
    - [ ] All CI checks passing on main
    - [ ] No open PRs blocking release
    - [ ] Ready to tag and publish

**Acceptance**: All Quality Gate items checked ✅, ready for release

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
  - Comment on #7, #9, #10, #11, #12, #13
  - Message: "Fixed in v0.5.0"
  - Close issues

- [ ] 5.7.4 Thank contributors
  - Comment on merged PRs
  - Thank everyone who reported issues

**Acceptance**: Announcement posted, issues closed, contributors thanked

---

## Task 5.8: Mark Sprint S5 and v0.5.0 Complete

- [ ] 5.8.1 Update roadmap progress
  - Open: `tasks-v0.5.0-roadmap.md`
  - Mark: Tasks 5.0.1-5.7 as complete `[x]`
  - Mark: Overall v0.5.0 as 52/52 (100%)

- [ ] 5.8.2 Update detailed file progress
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion date

- [ ] 5.8.3 Update main README
  - File: `../../README.md` (tasks main README)
  - Update: v0.5.0 status from "In Planning" to "Released"
  - Add: Release date

- [ ] 5.8.4 Archive sprint documents
  - Consider: Move to `completed/v0.5.0/` or keep in place
  - Document: v0.5.0 completion in parent README

**Acceptance**: All tracking complete, v0.5.0 marked as released

---

**Sprint S5 Definition of Done**:
- [ ] S3 follow-ups completed (5.0.1, 5.0.2) - empty nonce, TTL config
- [ ] Issue #12 closed (5.0.3) - log sanitization
- [ ] Issue #11 closed (5.0.4) - test coverage
- [ ] All tasks 5.1-5.8 completed
- [ ] All CRIT+HIGH security tasks completed
- [ ] **Final Quality Gate passed** (5.5.6) - all checks green
- [ ] Zero breaking changes vs v0.1.0
- [ ] CI passes on all platforms
- [ ] v0.5.0 published to PyPI
- [ ] GitHub release created with notes
- [ ] Coverage ≥92% overall, ≥95% on security modules
- [ ] Performance regression <5%
- [ ] All open issues (#11, #12, #13) closed
- [ ] v0.5.0 marked as complete milestone

**Total Sub-tasks**: ~55 (added Issues #11, #12 + Final Quality Gate)
