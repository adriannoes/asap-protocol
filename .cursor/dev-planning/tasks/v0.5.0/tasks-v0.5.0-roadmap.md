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

**Duration**: Flexible (3-5 days)
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
- [ ] All GitHub issues #7, #9, #10 closed
- [ ] Dependabot configured and verified
- [ ] CI passes with updated FastAPI
- [ ] No breaking changes introduced
- [ ] Documentation updated (CONTRIBUTING.md, SECURITY.md)
- [ ] All 543+ tests passing
- [ ] mypy --strict passes

---

## Sprint S2: DoS Prevention & Rate Limiting

**Duration**: Flexible (5-7 days)
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

## Sprint S3: Replay Attack Prevention & HTTPS

**Duration**: Flexible (4-6 days)
**Goal**: Implement timestamp validation and HTTPS enforcement

### Tasks

- [ ] 3.1 Add timestamp constants
  - Goal: Define MAX_ENVELOPE_AGE_SECONDS (5min) and MAX_FUTURE_TOLERANCE_SECONDS (30s)
  - Details: [Sprint S3 Detailed - Task 3.1](./tasks-v0.5.0-s3-detailed.md#task-31-add-timestamp-constants)

- [ ] 3.2 Create validators module
  - Goal: Implement validate_envelope_timestamp() function
  - Details: [Sprint S3 Detailed - Task 3.2](./tasks-v0.5.0-s3-detailed.md#task-32-create-validators-module)

- [ ] 3.3 Implement nonce support
  - Goal: Optional nonce validation for critical operations
  - Details: [Sprint S3 Detailed - Task 3.3](./tasks-v0.5.0-s3-detailed.md#task-33-implement-nonce-support)

- [ ] 3.4 Integrate timestamp validation in server
  - Goal: Validate before handler dispatch
  - Details: [Sprint S3 Detailed - Task 3.4](./tasks-v0.5.0-s3-detailed.md#task-34-integrate-validation-in-server)

- [ ] 3.5 Add HTTPS enforcement to client
  - Goal: require_https=True parameter, validate URLs
  - Details: [Sprint S3 Detailed - Task 3.5](./tasks-v0.5.0-s3-detailed.md#task-35-add-https-enforcement-to-client)

- [ ] 3.6 Add validation tests
  - Goal: 12+ tests for timestamp, nonce, and HTTPS
  - Details: [Sprint S3 Detailed - Task 3.6](./tasks-v0.5.0-s3-detailed.md#task-36-add-validation-tests)

- [ ] 3.7 Update documentation
  - Goal: Document replay prevention and HTTPS in docs/security.md
  - Details: [Sprint S3 Detailed - Task 3.7](./tasks-v0.5.0-s3-detailed.md#task-37-update-documentation)

- [ ] 3.8 PRD review checkpoint
  - Goal: Review Q3 (HMAC signing), document learnings
  - Details: [Sprint S3 Detailed - Task 3.8](./tasks-v0.5.0-s3-detailed.md#task-38-prd-review-checkpoint)

### Definition of Done
- [ ] Envelopes older than 5 minutes rejected
- [ ] Future timestamps beyond 30s rejected
- [ ] HTTPS enforced in production mode
- [ ] Test coverage >95% maintained
- [ ] Examples updated to use HTTPS
- [ ] PRD reviewed and updated with learnings

---

## Sprint S4: Retry Logic & Authorization

**Duration**: Flexible (3-5 days)
**Goal**: Implement exponential backoff and authorization validation

### Tasks

- [ ] 4.1 Implement exponential backoff
  - Goal: Retry with exponential backoff + jitter, max delay 60s
  - Details: [Sprint S4 Detailed - Task 4.1](./tasks-v0.5.0-s4-detailed.md#task-41-implement-exponential-backoff)

- [ ] 4.2 Implement circuit breaker (optional)
  - Goal: Circuit breaker pattern for repeated failures
  - Details: [Sprint S4 Detailed - Task 4.2](./tasks-v0.5.0-s4-detailed.md#task-42-implement-circuit-breaker-optional)

- [ ] 4.3 Add authorization scheme validation
  - Issue: [#13](https://github.com/adriannoes/asap-protocol/issues/13)
  - Goal: Validate manifest.auth schemes at startup
  - Details: [Sprint S4 Detailed - Task 4.3](./tasks-v0.5.0-s4-detailed.md#task-43-add-authorization-scheme-validation)

- [ ] 4.4 Add retry and authorization tests
  - Goal: 12+ tests for backoff, circuit breaker, auth validation
  - Details: [Sprint S4 Detailed - Task 4.4](./tasks-v0.5.0-s4-detailed.md#task-44-add-retry-and-auth-tests)

- [ ] 4.5 Update documentation
  - Goal: Document retry config and auth schemes
  - Details: [Sprint S4 Detailed - Task 4.5](./tasks-v0.5.0-s4-detailed.md#task-45-update-documentation)

### Definition of Done
- [ ] Exponential backoff with jitter working
- [ ] Max delay capped at 60 seconds
- [ ] Authorization schemes validated at manifest load
- [ ] Test coverage >95% maintained
- [ ] Documentation covers retry configuration
- [ ] Issue #13 closed

---

## Sprint S5: v0.5.0 Release Preparation

**Duration**: Flexible (2-3 days)
**Goal**: Final testing, documentation, and release

### Tasks

- [ ] 5.1 Run security audit
  - Goal: pip-audit + bandit, verify no critical vulnerabilities
  - Details: [Sprint S5 Detailed - Task 5.1](./tasks-v0.5.0-s5-detailed.md#task-51-security-audit)

- [ ] 5.2 Run testing & quality checks
  - Goal: All tests pass, coverage ≥95%, linters clean
  - Details: [Sprint S5 Detailed - Task 5.2](./tasks-v0.5.0-s5-detailed.md#task-52-testing--quality)

- [ ] 5.3 Test compatibility and upgrade path
  - Goal: Verify v0.1.0 → v0.5.0 upgrade works smoothly
  - Details: [Sprint S5 Detailed - Task 5.3](./tasks-v0.5.0-s5-detailed.md#task-53-compatibility-testing)

- [ ] 5.4 Review and update documentation
  - Goal: CHANGELOG, README, migration guide complete
  - Details: [Sprint S5 Detailed - Task 5.4](./tasks-v0.5.0-s5-detailed.md#task-54-documentation-review)

- [ ] 5.5 Prepare release
  - Goal: Release notes, version bump, PR reviews
  - Details: [Sprint S5 Detailed - Task 5.5](./tasks-v0.5.0-s5-detailed.md#task-55-release-preparation)

- [ ] 5.6 Build and publish
  - Goal: Build, tag, publish to PyPI, create GitHub release
  - Details: [Sprint S5 Detailed - Task 5.6](./tasks-v0.5.0-s5-detailed.md#task-56-build-and-publish)

- [ ] 5.7 Communicate release
  - Goal: Announce, close issues, thank contributors
  - Details: [Sprint S5 Detailed - Task 5.7](./tasks-v0.5.0-s5-detailed.md#task-57-communication)

### Definition of Done
- [ ] All CRIT+HIGH security tasks completed
- [ ] Zero breaking changes vs v0.1.0 (or documented)
- [ ] CI passes on all platforms
- [ ] v0.5.0 published to PyPI
- [ ] GitHub release created with notes
- [ ] Test coverage ≥95%
- [ ] Performance regression <5%

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| S1 | 6 | Quick wins + Dependabot | 3-5 |
| S2 | 9 | DoS prevention | 5-7 |
| S3 | 8 | Replay attack + HTTPS + PRD Review | 4-6 |
| S4 | 5 | Retry + Authorization | 3-5 |
| S5 | 7 | Release prep | 2-3 |

**Total**: 35 high-level tasks across 5 sprints

**PRD Review Checkpoints**: 1 (Sprint S3)

---

## Progress Tracking

**Overall Progress**: 16/35 tasks completed (45.71%)

**Sprint Status**:
- ✅ S1: 7/7 tasks (100%) - All tasks completed
- ✅ S2: 9/9 tasks (100%) - All tasks completed
- ⏳ S3: 0/8 tasks (0%) - **Includes PRD review checkpoint**
- ⏳ S4: 0/5 tasks (0%)
- ⏳ S5: 0/7 tasks (0%)

**PRD Maintenance**:
- Next review: End of Sprint S3
- Questions to address: Q3 (HMAC signing decision)

**Last Updated**: 2026-01-25 (Sprint S2 completed)

---

## Related Documents

- **Detailed Tasks**: [tasks-v0.5.0-s[1-5]-detailed.md](.)
- **Parent PRD**: [prd-v1-roadmap.md](../../prd/prd-v1-roadmap.md)
- **Security Review**: [tasks-security-review-report.md](../v0.1.0/tasks-security-review-report.md)
- **GitHub Issues**: [Issue Tracker](https://github.com/adriannoes/asap-protocol/issues)
