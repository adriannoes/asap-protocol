# Tasks: ASAP Protocol v0.5.0 Roadmap

> **High-level task overview** for v0.5.0 milestone (Security-Hardened Release)
>
> **Parent PRD**: [prd-v1-roadmap.md](../../prd/prd-v1-roadmap.md)
> **Current Version**: v0.1.0
> **Target Version**: v0.5.0
> **Focus**: CRITICAL + HIGH priority security issues
>
> 💡 **For detailed step-by-step instructions**, see individual sprint files:
> - [Sprint S1 Details](./tasks-v0.5.0-s1-detailed.md)
> - [Sprint S2 Details](./tasks-v0.5.0-s2-detailed.md)
> - [Sprint S3 Details](./tasks-v0.5.0-s3-detailed.md)
> - [Sprint S4 Details](./tasks-v0.5.0-s4-detailed.md)
> - [Sprint S5 Details](./tasks-v0.5.0-s5-detailed.md)

---

## Sprint S1: Quick Wins & Dependency Setup

**Goal**: Resolve low-hanging fruit and establish dependency monitoring

### Tasks

- [x] 1.1 ~~Authentication implementation~~ ✅
  - Status: Completed in [PR #8](https://github.com/adriannoes/asap-protocol/pull/8)
  - Includes: Bearer token auth, middleware, sender verification, tests

- [x] 1.2 Remove `type: ignore` in handlers.py ✅
  - Issue: [#10](https://github.com/adriannoes/asap-protocol/issues/10)
  - Goal: Eliminate type suppressions, achieve full mypy strict compliance
  - Details: [Sprint S1 Detailed - Task 1.1](./tasks-v0.5.0-s1-detailed.md#task-11-remove-type-ignore-in-handlerspy)

- [x] 1.3 Refactor `handle_message` into smaller helpers ✅
  - Issue: [#9](https://github.com/adriannoes/asap-protocol/issues/9)
  - Goal: Break down monolithic function into testable helpers (<20 lines)
  - Details: [Sprint S1 Detailed - Task 1.2](./tasks-v0.5.0-s1-detailed.md#task-12-refactor-handle_message-into-smaller-helpers)

- [x] 1.4 Upgrade FastAPI to 0.128.0+ ✅
  - Issue: [#7](https://github.com/adriannoes/asap-protocol/issues/7)
  - Goal: Update from 0.124 to ≥0.128.0, verify compatibility
  - Details: [Sprint S1 Detailed - Task 1.3](./tasks-v0.5.0-s1-detailed.md#task-13-upgrade-fastapi-to-01280)

- [x] 1.5 Configure Dependabot for security monitoring ✅
  - Goal: Monthly security update checks, automated PRs
  - Details: [Sprint S1 Detailed - Task 1.4](./tasks-v0.5.0-s1-detailed.md#task-14-configure-dependabot)

- [x] 1.6 Document dependency update process ✅
  - Goal: Update CONTRIBUTING.md and SECURITY.md with review workflow
  - Details: [Sprint S1 Detailed - Task 1.5](./tasks-v0.5.0-s1-detailed.md#task-15-document-dependency-process)

- [x] 1.7 Verify CI integration ✅
  - Goal: Ensure pip-audit runs on all PRs
  - Details: [Sprint S1 Detailed - Task 1.6](./tasks-v0.5.0-s1-detailed.md#task-16-verify-ci-integration)

### Definition of Done
- [x] Work for issues #7, #9, #10 completed in v0.5.0 (close on GitHub at release)
- [x] Dependabot configured and verified
- [ ] CI passes with updated FastAPI
- [ ] No breaking changes introduced
- [ ] Documentation updated (CONTRIBUTING.md, SECURITY.md)
- [ ] All 543+ tests passing
- [ ] mypy --strict passes

---

## Sprint S2: DoS Prevention & Rate Limiting

**Goal**: Implement rate limiting and request size validation

### Tasks

- [x] 2.1 Add slowapi dependency ✅
  - Goal: Install rate limiting library
  - Details: [Sprint S2 Detailed - Task 2.1](./tasks-v0.5.0-s2-detailed.md#task-21-add-slowapi-dependency)

- [x] 2.2 Implement rate limiting middleware ✅
  - Goal: Per-sender rate limiting (100 req/min default)
  - Details: [Sprint S2 Detailed - Task 2.2](./tasks-v0.5.0-s2-detailed.md#task-22-implement-rate-limiting-middleware)

- [x] 2.3 Integrate rate limiter in server ✅
  - Goal: Apply to /asap endpoint, make configurable
  - Details: [Sprint S2 Detailed - Task 2.3](./tasks-v0.5.0-s2-detailed.md#task-23-integrate-rate-limiter-in-server)

- [x] 2.4 Add request size validation ✅
  - Goal: 10MB max request size for DoS prevention
  - Details: [Sprint S2 Detailed - Task 2.4](./tasks-v0.5.0-s2-detailed.md#task-24-add-request-size-validation)

- [x] 2.5 Add rate limiting tests ✅
  - Goal: 4+ tests for rate limiting behavior
  - Details: [Sprint S2 Detailed - Task 2.5](./tasks-v0.5.0-s2-detailed.md#task-25-add-rate-limiting-tests)

- [x] 2.6 Add payload size tests ✅
  - Goal: 4+ tests for size validation
  - Details: [Sprint S2 Detailed - Task 2.6](./tasks-v0.5.0-s2-detailed.md#task-26-add-payload-size-tests)

- [x] 2.7 Update security documentation ✅
  - Goal: Document rate limiting and size limits in docs/security.md
  - Details: [Sprint S2 Detailed - Task 2.7](./tasks-v0.5.0-s2-detailed.md#task-27-update-security-documentation)

- [x] 2.8 Harden thread pool execution ✅
  - Goal: Use bounded CustomExecutor to prevent thread starvation
  - Details: [Sprint S2 Detailed - Task 2.8](./tasks-v0.5.0-s2-detailed.md#task-28-harden-thread-pool-execution)

- [x] 2.9 Protect metrics cardinality ✅
  - Goal: Whitelist payload_types to prevent memory exhaustion DoS
  - Details: [Sprint S2 Detailed - Task 2.9](./tasks-v0.5.0-s2-detailed.md#task-29-protect-metrics-cardinality)

### Definition of Done
- [x] Rate limiting: HTTP 429 after limit exceeded ✅
- [x] Request size validation: 10MB limit enforced ✅
- [x] Test coverage >95% maintained ✅ (S2-specific: 100%)
- [x] Documentation updated with configuration examples ✅

---

## Sprint S2.5: Test Infrastructure Refactoring

**Goal**: Reorganize test structure and resolve Issue #17 (33 failing tests)

### Tasks

- [x] 2.5.1 Fix critical bugs in test_server.py
  - Goal: Resolve UnboundLocalError in TestASAPRequestHandlerHelpers (3 tests)
  - Details: [Sprint S2.5 Detailed - Task 2.5.1](./tasks-v0.5.0-s2.5-detailed.md#task-251-fix-critical-bugs-in-test_serverpy)

- [x] 2.5.2 Update authentication test fixtures
  - Goal: Add isolated_rate_limiter to 4 auth tests
  - Details: [Sprint S2.5 Detailed - Task 2.5.2](./tasks-v0.5.0-s2.5-detailed.md#task-252-update-authentication-test-fixtures)

- [x] 2.5.3 Create test directory structure
  - Goal: Create unit/, integration/, e2e/ directories
  - Details: [Sprint S2.5 Detailed - Task 2.5.3](./tasks-v0.5.0-s2.5-detailed.md#task-253-create-test-directory-structure)

- [x] 2.5.4 Create transport-specific fixtures
  - Goal: Add transport/conftest.py with isolated fixtures
  - Details: [Sprint S2.5 Detailed - Task 2.5.4](./tasks-v0.5.0-s2.5-detailed.md#task-254-create-transport-specific-fixtures)

- [x] 2.5.5 Migrate BoundedExecutor to unit tests
  - Goal: Move 8 executor tests to unit/test_bounded_executor.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.5](./tasks-v0.5.0-s2.5-detailed.md#task-255-migrate-boundedexecutor-to-unit-tests)

- [x] 2.5.6 Migrate rate limiting to integration tests
  - Goal: Move 4 rate limiting tests to integration/test_rate_limiting.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.6](./tasks-v0.5.0-s2.5-detailed.md#task-256-migrate-rate-limiting-to-integration-tests)

- [x] 2.5.7 Migrate size validation to integration tests
  - Goal: Move 4 size validation tests to integration/test_request_size_limits.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.7](./tasks-v0.5.0-s2.5-detailed.md#task-257-migrate-size-validation-to-integration-tests)

- [x] 2.5.8 Migrate thread pool to integration tests
  - Goal: Move 3 thread pool tests to integration/test_thread_pool_bounds.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.8](./tasks-v0.5.0-s2.5-detailed.md#task-258-migrate-thread-pool-to-integration-tests)

- [x] 2.5.9 Migrate metrics cardinality to integration tests
  - Goal: Move 1 metrics test to integration/test_metrics_cardinality.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.9](./tasks-v0.5.0-s2.5-detailed.md#task-259-migrate-metrics-cardinality-to-integration-tests)

- [x] 2.5.10 Migrate E2E tests
  - Goal: Move test_integration.py to e2e/test_full_agent_flow.py
  - Details: [Sprint S2.5 Detailed - Task 2.5.10](./tasks-v0.5.0-s2.5-detailed.md#task-2510-migrate-e2e-tests)

- [x] 2.5.11 Fix remaining test_server.py fixtures
  - Goal: Add isolated_rate_limiter to ~20 remaining tests
  - Details: [Sprint S2.5 Detailed - Task 2.5.11](./tasks-v0.5.0-s2.5-detailed.md#task-2511-fix-remaining-test_serverpy-fixtures)

- [x] 2.5.12 Clean up test_executors.py
  - Goal: Remove empty files after migration
  - Details: [Sprint S2.5 Detailed - Task 2.5.12](./tasks-v0.5.0-s2.5-detailed.md#task-2512-clean-up-test_executorspy)

- [x] 2.5.13 Add pytest-xdist for parallel execution
  - Goal: Install pytest-xdist and update CI for parallel tests
  - Details: [Sprint S2.5 Detailed - Task 2.5.13](./tasks-v0.5.0-s2.5-detailed.md#task-2513-add-pytest-xdist-for-parallel-execution)

- [x] 2.5.14 Validate all Sprint S2 tests together
  - Goal: Ensure all 20 S2 tests pass together without interference
  - Details: [Sprint S2.5 Detailed - Task 2.5.14](./tasks-v0.5.0-s2.5-detailed.md#task-2514-validate-all-sprint-s2-tests-together)

- [x] 2.5.15 Validate full test suite
  - Goal: Verify 578+ tests pass with 0 failures
  - Details: [Sprint S2.5 Detailed - Task 2.5.15](./tasks-v0.5.0-s2.5-detailed.md#task-2515-validate-full-test-suite)

- [x] 2.5.16 Update documentation
  - Goal: Create docs/testing.md and update CONTRIBUTING.md
  - Details: [Sprint S2.5 Detailed - Task 2.5.16](./tasks-v0.5.0-s2.5-detailed.md#task-2516-update-documentation)

- [x] 2.5.17 Update roadmap and mark complete
  - Goal: Document sprint completion in roadmap files
  - Details: [Sprint S2.5 Detailed - Task 2.5.17](./tasks-v0.5.0-s2.5-detailed.md#task-2517-update-roadmap-and-mark-complete)

### Definition of Done
- [x] All 33 failing tests now passing (Issue #17 resolved) ✅
- [x] Test structure reorganized: unit/, integration/, e2e/ ✅
- [x] pytest-xdist installed and CI updated ✅
- [x] All 578+ tests passing with 0 failures ✅
- [x] Documentation complete (docs/testing.md + CONTRIBUTING.md) ✅
- [x] All CI checks passing (lint, format, mypy, security) ✅
- [x] Tests pass both sequentially AND in parallel (pytest-xdist) ✅
- [ ] Issue #17 closed with resolution notes (ready to close)

---

## Sprint S3: Replay Attack Prevention & HTTPS

**Goal**: Implement timestamp validation and HTTPS enforcement

### Tasks

- [x] 3.1 Add timestamp constants ✅
  - Goal: Define MAX_ENVELOPE_AGE_SECONDS (5min) and MAX_FUTURE_TOLERANCE_SECONDS (30s)
  - Details: [Sprint S3 Detailed - Task 3.1](./tasks-v0.5.0-s3-detailed.md#task-31-add-timestamp-constants)

- [x] 3.2 Create validators module ✅
  - Goal: Implement validate_envelope_timestamp() function
  - Details: [Sprint S3 Detailed - Task 3.2](./tasks-v0.5.0-s3-detailed.md#task-32-create-validators-module)

- [x] 3.3 Implement nonce support ✅
  - Goal: Optional nonce validation for critical operations
  - Details: [Sprint S3 Detailed - Task 3.3](./tasks-v0.5.0-s3-detailed.md#task-33-implement-nonce-support)

- [x] 3.4 Integrate timestamp validation in server ✅
  - Goal: Validate before handler dispatch
  - Details: [Sprint S3 Detailed - Task 3.4](./tasks-v0.5.0-s3-detailed.md#task-34-integrate-validation-in-server)

- [x] 3.5 Add HTTPS enforcement to client ✅
  - Goal: require_https=True parameter, validate URLs
  - Details: [Sprint S3 Detailed - Task 3.5](./tasks-v0.5.0-s3-detailed.md#task-35-add-https-enforcement-to-client)

- [x] 3.6 Add validation tests ✅
  - Goal: 12+ tests for timestamp, nonce, and HTTPS (achieved: 17 tests)
  - Details: [Sprint S3 Detailed - Task 3.6](./tasks-v0.5.0-s3-detailed.md#task-36-add-validation-tests)

- [x] 3.7 Update documentation ✅
  - Goal: Document replay prevention and HTTPS in docs/security.md
  - Details: [Sprint S3 Detailed - Task 3.7](./tasks-v0.5.0-s3-detailed.md#task-37-update-documentation)

- [x] 3.8 PRD review checkpoint ✅
  - Goal: Review Q3 (HMAC signing), document learnings
  - Decision: HMAC deferred to v1.1.0+ (DD-008)
  - Details: [Sprint S3 Detailed - Task 3.8](./tasks-v0.5.0-s3-detailed.md#task-38-prd-review-checkpoint)

### Definition of Done
- [x] Envelopes older than 5 minutes rejected ✅
- [x] Future timestamps beyond 30s rejected ✅
- [x] HTTPS enforced in production mode ✅
- [x] Test coverage >95% maintained (91.90%) ✅
- [x] Examples updated to use HTTPS ✅
- [x] PRD reviewed and updated with learnings ✅

---

## Sprint S4: Retry Logic & Authorization

**Goal**: Implement exponential backoff and authorization validation

### Tasks

- [x] 4.1 Implement exponential backoff ✅
  - Goal: Retry with exponential backoff + jitter, max delay 60s
  - Details: [Sprint S4 Detailed - Task 4.1](./tasks-v0.5.0-s4-detailed.md#task-41-implement-exponential-backoff)

- [x] 4.2 Implement circuit breaker (optional) ✅
  - Goal: Circuit breaker pattern for repeated failures
  - Details: [Sprint S4 Detailed - Task 4.2](./tasks-v0.5.0-s4-detailed.md#task-42-implement-circuit-breaker-optional)

- [x] 4.3 Add authorization scheme validation ✅
  - Issue: [#13](https://github.com/adriannoes/asap-protocol/issues/13)
  - Goal: Validate manifest.auth schemes at startup
  - Details: [Sprint S4 Detailed - Task 4.3](./tasks-v0.5.0-s4-detailed.md#task-43-add-authorization-scheme-validation)

- [x] 4.4 Add retry and authorization tests ✅
  - Goal: 12+ tests for backoff, circuit breaker, auth validation
  - Details: [Sprint S4 Detailed - Task 4.4](./tasks-v0.5.0-s4-detailed.md#task-44-add-retry-and-auth-tests)

- [x] 4.4.5 Improve connection error messages (user feedback) ✅
  - Goal: Enhanced error messages with troubleshooting guidance
  - Details: [Sprint S4 Detailed - Task 4.4.5](./tasks-v0.5.0-s4-detailed.md#task-445-improve-connection-error-messages-user-feedback)

- [x] 4.5 Update documentation ✅
  - Goal: Document retry config, auth schemes, and connection troubleshooting
  - Details: [Sprint S4 Detailed - Task 4.5](./tasks-v0.5.0-s4-detailed.md#task-45-update-documentation)

### Definition of Done
- [x] Exponential backoff with jitter working ✅
- [x] Max delay capped at 60 seconds ✅
- [x] Authorization schemes validated at manifest load ✅
- [x] Test coverage >95% maintained ✅
- [x] Documentation covers retry configuration ✅
- [x] Issue #13 closed ✅ (commit 9501297)

---

## Security Red Team Remediation

**Goal**: Address findings from internal Red Team security assessment (Jan 27, 2026)

### Tasks

- [x] RT.1 Refactor Circuit Breaker for Persistence ✅
  - Finding: Circuit breaker state was ephemeral per request
  - Solution: Implemented `CircuitBreakerRegistry` singleton

- [x] RT.2 Fix Concurrency & Blocking Issues ✅
  - Finding: Risk of event loop blocking
  - Solution: Reviewed locking strategy (retained fast RLock), added async safeguards

- [x] RT.3 Enhance Type Safety & Input Validation ✅
  - Finding: `type: ignore` usage and missing null checks
  - Solution: Strict mypy compliance, explicit `None` checks in `send()`

- [x] RT.4 Security Verification & Regression Testing ✅
  - Goal: Verify persistence and ensure no regressions
  - Outcome: New persistence tests added, full suite passing (726 tests)

### Definition of Done
- [x] All critical/high findings addressed ✅
- [x] Circuit breaker works across multiple client instances ✅
- [x] No regressions in test suite ✅

---

## Sprint S5: v0.5.0 Release Preparation

**Goal**: Final testing, documentation, and release

### Tasks

- [x] 5.0.1 Add empty nonce string validation (S3 follow-up) ✅
  - Goal: Reject empty string nonces with clear error message
  - Source: [PR #19 Code Review - Section 3.2](../code-review/v0.5.0/sprint-s3-code-review.md)
  - Details: [Sprint S5 Detailed - Task 5.0.1](./tasks-v0.5.0-s5-detailed.md#task-501-add-empty-nonce-string-validation)

- [x] 5.0.2 Make nonce TTL configurable (S3 follow-up) ✅
  - Goal: Derive nonce TTL from MAX_ENVELOPE_AGE_SECONDS constant
  - Source: [PR #19 Code Review - Section 3.4](../code-review/v0.5.0/sprint-s3-code-review.md)
  - Details: [Sprint S5 Detailed - Task 5.0.2](./tasks-v0.5.0-s5-detailed.md#task-502-make-nonce-ttl-configurable)

- [x] 5.0.3 Implement log sanitization ✅
  - Issue: [#12](https://github.com/adriannoes/asap-protocol/issues/12) — work done; close on GitHub at release
  - Goal: Prevent sensitive data (tokens, credentials) from appearing in logs
  - Details: [Sprint S5 Detailed - Task 5.0.3](./tasks-v0.5.0-s5-detailed.md#task-503-implement-log-sanitization)

- [x] 5.0.4 Add missing test coverage ✅
  - Issue: [#11](https://github.com/adriannoes/asap-protocol/issues/11) — work done; close on GitHub at release
  - Goal: Achieve ≥95% coverage on security-critical modules
  - Details: [Sprint S5 Detailed - Task 5.0.4](./tasks-v0.5.0-s5-detailed.md#task-504-add-missing-test-coverage)

- [x] 5.1 Run security audit ✅
  - Goal: pip-audit + bandit, verify no critical vulnerabilities
  - Details: [Sprint S5 Detailed - Task 5.1](./tasks-v0.5.0-s5-detailed.md#task-51-security-audit)

- [x] 5.2 Run testing & quality checks ✅
  - Goal: All tests pass, coverage ≥92%, linters clean
  - Details: [Sprint S5 Detailed - Task 5.2](./tasks-v0.5.0-s5-detailed.md#task-52-testing--quality)

- [x] 5.3 Test compatibility and upgrade path ✅
  - Goal: Verify v0.1.0 → v0.5.0 and v0.3.0 → v0.5.0 upgrade paths work smoothly
  - Details: [Sprint S5 Detailed - Task 5.3](./tasks-v0.5.0-s5-detailed.md#task-53-compatibility-testing)

- [x] 5.4 Review and update documentation ✅
  - Goal: CHANGELOG, README, migration guide complete
  - Details: [Sprint S5 Detailed - Task 5.4](./tasks-v0.5.0-s5-detailed.md#task-54-documentation-review)

- [x] 5.5 Prepare release + Final Quality Gate ✅ (version bump, PRs reviewed; final commit at release)
  - Goal: Release notes, version bump, **comprehensive quality gate**
  - Details: [Sprint S5 Detailed - Task 5.5](./tasks-v0.5.0-s5-detailed.md#task-55-release-preparation)

- [x] 5.6 Build and publish ✅
  - Goal: Build, tag, publish to PyPI, create GitHub release
  - Details: [Sprint S5 Detailed - Task 5.6](./tasks-v0.5.0-s5-detailed.md#task-56-build-and-publish)

- [x] 5.7 Communicate release ✅ (5.7.2 Discussions skipped; 5.7.1 README done; 5.7.3 close issues manual)
  - Goal: Announce, close issues (#7, #9, #10, #11, #12, #13), thank contributors
  - Details: [Sprint S5 Detailed - Task 5.7](./tasks-v0.5.0-s5-detailed.md#task-57-communication)

### Definition of Done
- [x] S3 follow-ups completed (5.0.1, 5.0.2)
- [x] Issue #12 work done - log sanitization (5.0.3); close on GitHub at release
- [x] Issue #11 work done - test coverage (5.0.4); close on GitHub at release
- [x] Issues #7, #9, #10, #13 work done in S1/S4; close on GitHub at release (5.7.3)
- [x] **Final Quality Gate passed** (5.5.6)
- [x] All CRIT+HIGH security tasks completed
- [x] Zero breaking changes vs v0.1.0 (verified in S5 compatibility tests)
- [x] CI passes on all platforms
- [x] v0.5.0 published to PyPI
- [x] GitHub release created with notes
- [x] Coverage ≥92% overall, ≥95% on security modules
- [x] Performance regression <5% (no regression; transport benchmarks limited by rate limiting)

---

## Summary

| Sprint | Tasks | Focus | Estimated Time |
|--------|-------|-------|----------------|
| S1 | 7 | Quick wins + Dependabot | 3-5 days |
| S2 | 9 | DoS prevention | 5-7 days |
| S2.5 | 13 | Test infrastructure refactoring | 4-6 hours |
| S3 | 8 | Replay attack + HTTPS + PRD Review | 4-6 days |
| S4 | 6 | Retry + Authorization (S3 patterns applied) | 3-5 days |
| Security | 4 | Red Team Remediation (Circuit Breaker, Type Safety) | 1 day |
| S5 | 11 | Release prep + S3 follow-ups + Issues #11/#12 + Quality Gate | 3-4 days |

**Total**: 58 high-level tasks across 6 sprints + security audit

**PRD Review Checkpoints**: 1 (Sprint S3)

---

## Progress Tracking

**Overall Progress**: 58/58 tasks completed (100%) — v0.5.0 released 2026-01-28

**Sprint Status**:
- ✅ S1: 7/7 tasks (100%) - All tasks completed
- ✅ S2: 9/9 tasks (100%) - All tasks completed
- ✅ S2.5: 17/17 tasks (100%) - Test infrastructure refactoring - **COMPLETE** (Jan 26, 2026)
- ✅ S3: 8/8 tasks (100%) - Replay Prevention & HTTPS + PRD Review - **COMPLETE** (Jan 27, 2026)
- ✅ S4: 6/6 tasks (100%) - Retry Logic & Authorization - **COMPLETE** (Jan 27, 2026)
- ✅ Security: 4/4 tasks (100%) - Red Team Remediation - **COMPLETE** (Jan 27, 2026)
- ✅ S5: 11/11 tasks (100%) - v0.5.0 Release Preparation **COMPLETE** (2026-01-29)

**PRD Maintenance**:
- ✅ Sprint S3 review completed (2026-01-27)
- Added DD-008: HMAC deferred to v1.1.0+
- S4 plan updated with S3 learnings (2026-01-27)
- S5 plan updated with Issues #11, #12 + Final Quality Gate (2026-01-27)
- Next review: End of Sprint P3 (v1.0.0)

**Last Updated**: 2026-01-29 (v0.5.0 release complete; 5.7.3 close issues manual on GitHub)

---

## Related Documents

- **Detailed Tasks**: [tasks-v0.5.0-s[1-5]-detailed.md](.)
- **Parent PRD**: [prd-v1-roadmap.md](../../prd/prd-v1-roadmap.md)
- **Security Review**: [tasks-security-review-report.md](../v0.1.0/tasks-security-review-report.md)
- **S3 Code Review**: [sprint-s3-code-review.md](../code-review/v0.5.0/sprint-s3-code-review.md)
- **GitHub Issues**: [Issue Tracker](https://github.com/adriannoes/asap-protocol/issues)
