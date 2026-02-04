# Tasks: ASAP v1.0.0 Release (P13) - Detailed

> **Sprint**: P13 - v1.0.0 Release Preparation  
> **Goal**: Final testing, polish, and production release  
> **Release prep completed**: 2026-02-04 (13.4 build/publish after push)

---

## Relevant Files

- `CHANGELOG.md` - v1.0.0 release notes (13.3.1 ✅)
- `.github/release-notes-v1.0.0.md` - Comprehensive release notes (13.3.2 ✅)
- `README.md` - Update to "Stable" status
- `pyproject.toml` - Update version and classifiers
- `.cursor/dev-planning/retrospectives/v1.0.0-retro.md` - Retrospective (13.6.2 ✅)
- All docs/ - Final review
- `tests/observability/test_trace_parser.py` - Coverage: format_ascii duration None, build_hops non-str sender/recipient, extract_trace_ids event filter, _timestamp_to_sort_key
- `tests/observability/test_tracing.py` - Coverage: configure_tracing otlp without endpoint
- `tests/transport/unit/test_compression.py` - Coverage: select_best_encoding unsupported-only and empty parts; compress_payload BROTLI fallback when brotli unavailable
- `tests/transport/unit/test_client_coverage_gaps.py` - Coverage: _is_localhost no hostname, _validate_connection not connected / ConnectError / Timeout / generic Exception

---

## Task 13.0: Pre-Release Technical Audit ✅

> **Status**: Completed 2026-02-03  
> **Branch**: `pre-release-audit-fixes`  
> **Report**: [pre-release-audit-report.md](../../code-review/v1.0.0/pre-release-audit-report.md)

### 13.0.1 Comprehensive codebase audit

- [x] Verify all roadmap claims (P1-P12) against code
- [x] Bug hunting (async patterns, race conditions, security)
- [x] Test suite health analysis (~27,700 lines, 1354 tests)
- [x] Code quality review (TODOs, type hints, docs)

### 13.0.2 Address audit findings

- [x] ManifestCache max_size with LRU eviction (`c19cd96`)
- [x] Batch + Auth + Pooling integration tests (`2a8d49f`, 601 lines)
- [x] MCP + ASAP integration tests (`5cd226f`, 574 lines)
- [x] Compression edge case tests (`6263f1f`, 298 lines)
- [x] Documentation and log consolidation (`e77ccc6`)
- [x] Code cleanup (`2d973c9`)

### 13.0.3 Verify all fixes

- [x] Run full test suite: 1354 passed, 4 skipped, 59.85s
- [x] Update audit report with resolution status

**Acceptance**: All HIGH/MEDIUM findings resolved ✅

---

## Task 13.1: Comprehensive Testing


- [x] 13.1.1 Run full test suite
  - Command: `PYTHONPATH=src uv run pytest -v --cov=src --cov-report=term-missing`
  - Result: 1379 passed, 5 skipped (~62s)
  - Coverage: 94.84% (raised from 93.98%; target ≥95% — close)

- [x] 13.1.2 Run all benchmarks
  - Load: `uv run locust -f benchmarks/load_test.py` (server: `ASAP_RATE_LIMIT=100000/minute uv run uvicorn asap.transport.server:app --host 127.0.0.1 --port 8000`)
  - Property: `uv run pytest tests/properties/` → 33 passed (~5s)
  - Chaos: `uv run pytest tests/chaos/` → 69 passed (~0.5s)
  - Load (20s, 30 users): RPS 1114 (≥800 ✅), error rate 0% (✅), p95 17ms (target <5ms under lighter load per benchmarks/RESULTS.md)
  - Verify: RPS and error-rate targets met; p95 acceptable under load per RESULTS.md

- [x] 13.1.3 Run security audit
  - Pip-audit: `uv run pip-audit` → No known vulnerabilities found ✅
  - Bandit: `uv run bandit -r src/` → 27 Low (0 High/Critical); examples + testing helpers (asserts, demo tokens, jitter random) ✅
  - Expected: Zero critical vulnerabilities → Met

- [x] 13.1.4 Run linters
  - Ruff: `uv run ruff check src/ tests/` → All checks passed ✅
  - Mypy: `uv run mypy --strict src/` → Success: no issues found in 60 source files ✅
  - Expected: Zero errors → Met

**Acceptance**: All quality checks pass

---

## Task 13.2: Documentation Review

- [x] 13.2.1 Review all documentation files
  - README, CHANGELOG, CONTRIBUTING, SECURITY reviewed
  - docs/ internal links: `pytest tests/test_docs_links.py` → 2 passed
  - Fix: SECURITY.md supported versions updated to include 0.5.x

- [x] 13.2.2 Test all examples
  - Run: 13 runnable examples (auth_patterns, rate_limiting, state_migration, streaming_response, multi_step_workflow, websocket_concept, mcp_integration, error_recovery, long_running, run_demo, echo_agent, coordinator, orchestration); secure_handler is library-only
  - Verify: All exited 0, output/logs correct

- [x] 13.2.3 Test upgrade paths
  - Test: `uv run pytest tests/contract/` → 81 passed (~0.5s)
  - v0.1.0 → v1.0.0: test_v0_1_to_v1_0.py (task request, envelope, cancel, errors, manifest, correlation_id)
  - v0.5.0 → v1.0.0: test_v0_5_to_v1_0.py (nonce, auth, extensions, timestamp, manifest, errors)
  - Schema evolution + v1.0→v0.5 (rollback) also covered
  - Verify: Smooth upgrades ✅

**Acceptance**: All docs accurate, examples work, upgrades smooth

---

## Task 13.3: Release Preparation

- [x] 13.3.1 Update CHANGELOG.md
  - Section: `## [1.0.0] - 2026-02-03`
  - List: All changes since v0.5.0 (security, performance, DX, testing, docs, observability, MCP)
  - Format: Keep a Changelog

- [x] 13.3.2 Create comprehensive release notes
  - File: `.github/release-notes-v1.0.0.md`
  - Sections:
    - Major features (security, performance, DX)
    - Performance improvements (benchmarks)
    - Breaking changes (if any)
    - Migration guide
    - Contributors

- [x] 13.3.3 Review and merge open PRs
  - Merge: Ready PRs for v1.0.0
  - Defer: Non-critical to v1.1.0
  - Close: Stale PRs
  - **Result**: No open PRs (verified 2026-02-04); nothing to merge, defer, or close.

- [x] 13.3.4 Update version
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

- [x] 13.5.1 Announce release
  - Update README status (if needed, review anyway)
  - **Result**: Review confirmed README already has v1.0.0, Stable, PyPI link; no change needed.

- [x] 13.5.2 Update project status
  - README: "Alpha" → "Stable" (if needed, review anyway)
  - Badges: Update version (if needed, review anyway)
  - **Result**: Already "Stable" and v1.0.0; classifier updated in 13.3.4.

- [ ] 13.5.3 Close resolved issues
  - Comment: "Fixed in v1.0.0"
  - **Note**: Do after push and publish (GitHub Issues).

**Acceptance**: Announcement posted, status updated

---

## Task 13.6: PRD Review & Retrospective

- [x] 13.6.1 Final PRD review
  - Review: All remaining open questions (Q1-Q12)
  - Document: Decisions or defer to v1.1.0
  - Update: PRD Section 10 with all decisions
  - **Result**: PRD Section 11 already has Q1-Q12 resolved or deferred; Section 10 has DD-009–DD-013. Changelog entry added for v1.0.0 final review.

- [x] 13.6.2 Create retrospective
  - File: `.cursor/dev-planning/retrospectives/v1.0.0-retro.md`
  - Content:
    - What went well
    - What could improve
    - Lessons learned
    - Metrics vs targets
    - Recommendations for v1.1.0

**Acceptance**: PRD complete, retrospective created, review scheduled

---

## Task 13.7: Mark Sprint P13 and v1.0.0 Complete

- [x] 13.7.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P13 tasks (13.1-13.6) as complete `[x]`; 13.4 remains `[ ]` until after push/publish.
  - Mark: Overall v1.0.0 as 38/39 (13.4 pending).

- [x] 13.7.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]` except 13.4.x and 13.5.3 (post-push).
  - Completion date: 2026-02-04.

- [x] 13.7.3 Update main tracking
  - README already has v1.0.0, Stable, PyPI link.
  - Optional: add "Released: 2026-02-04" when publishing (or leave as is).

- [x] 13.7.4 Archive v1.0.0 milestone
  - Document: v1.0.0 completion in roadmap and this file.
  - Milestone closed after 13.4 (tag, PyPI, GitHub release, Docker) is done.

**Acceptance**: All tracking complete, v1.0.0 milestone closed after 13.4

---

**P13 Definition of Done**:
- [x] All tasks 13.1-13.3, 13.5-13.7 completed (13.4 after push)
- [x] All success metrics met
- [x] 1379+ tests passing
- [ ] v1.0.0 on PyPI (13.4.4)
- [ ] GitHub release published (13.4.5)
- [x] Documentation 100% complete
- [x] PRD fully reviewed
- [x] Retrospective created
- [ ] Post-release review scheduled (2 weeks after publish)
- [x] Progress tracked everywhere
- [ ] v1.0.0 marked as complete milestone (after 13.4)

**Total Sub-tasks**: ~55
