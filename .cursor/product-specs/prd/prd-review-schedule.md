# PRD Review Schedule & Process

> **Document**: Living documentation for PRD maintenance during v0.5.0 → v1.0.0 development
> **Parent PRD**: [prd-v1-roadmap.md](./prd-v1-roadmap.md)
> **Created**: 2026-01-24
> **Status**: Active

---

## Overview

The PRD is a **living document** that evolves with the project. This document tracks:
- When to review open questions
- What decisions to make at each checkpoint
- How to document decisions

---

## Review Schedule

### v0.5.0 Security-Hardened Release

| Checkpoint | Sprint | Timing | Questions to Address | Deliverable |
|------------|--------|--------|----------------------|-------------|
| **Security Review** | S3 | End of sprint | Q3: HMAC signing decision | Update PRD DD-008 or defer to v1.1.0 |

**Total Checkpoints**: 1

---

### v1.0.0 Production-Ready Release

| # | Checkpoint | Sprint | Timing | Questions to Address | Deliverable |
|---|------------|--------|--------|----------------------|-------------|
| 1 | **Security Decisions** | P1 | End of sprint | Q3: HMAC signing (if deferred from v0.5.0) | DD-008 or defer |
| 2 | **Performance Benchmarks** | P3 | End of sprint | Q1: Optimal connection pool size | DD-008 with recommendations |
| 3 | **DX Examples** | P5 | End of sprint | Q4: Auth scheme for examples<br>Q6: pytest-asap plugin assessment | DD-009 for auth<br>Plugin decision |
| 4 | **Debugging Tools** | P6 | End of sprint | Q5: Trace JSON export support | Implement or defer |
| 5 | **Load Testing** | P7 | End of sprint | Q2: Adaptive rate limiting | Include in v1.0.0 or defer |
| 6 | **Documentation i18n** | P9 | Start of sprint | Q8: i18n languages (check PyPI stats) | DD-013 for i18n scope ✅ |
| 7 | **Final Review** | P13 | Start of sprint | All remaining Q1-Q12 | Complete PRD<br>Create retrospective |

**Total Checkpoints**: 7

---

### Post-Release

| Checkpoint | Timing | Questions to Address | Action |
|------------|--------|----------------------|--------|
| **Community Feedback** | 2 weeks after v1.0.0 | Q7: Video tutorials<br>Q9: Discord/Slack community | Update PRD with community decisions |
| **Adoption Metrics** | 3 months after v1.0.0 | Q10: Foundation sponsorship | Assess based on metrics |
| **v1.1.0 Planning** | v1.1.0 kickoff | Q11: Next transport binding<br>Q12: Message encryption | Create v1.1.0 PRD |

---

## Decision Documentation Process

### 1. Review Question at Checkpoint

During the designated sprint, review the open question:

```markdown
Example from PRD Section 11:

1. ❓ What is the optimal default connection pool size?
   - **Action**: Benchmark during Sprint P3
   - **Review Point**: End of Sprint P3 → Update DD-008
```

### 2. Conduct Investigation

Execute the action specified (benchmark, assess, gather feedback).

### 3. Document Decision

Add a new Design Decision to PRD Section 10:

```markdown
#### DD-008: Connection Pool Size Defaults
**Decision**: ✅ Default pool size = 100 connections

**Rationale**:
- Benchmarks show optimal performance at 100 connections
- Scales well for single-agent deployments
- Can be tuned up to 1000 for high-traffic scenarios

**Implementation**:
- v1.0.0 Sprint P3: `pool_connections=100, pool_maxsize=100`
- Documented in performance tuning guide

**Benchmark Results**:
- Single-agent: 100 connections = <10ms p95
- Small cluster (3 agents): 200 connections recommended
- Large cluster (10+ agents): 500+ connections recommended
```

### 4. Update Task Lists (if needed)

If the decision impacts implementation:
- Update relevant tasks in task files
- Add new tasks if required
- Adjust timelines if necessary

### 5. Mark Question as Resolved

In PRD Section 11, mark the question:

```markdown
1. ✅ ~~What is the optimal default connection pool size?~~
   - **Decision**: See DD-008 in Section 10
   - **Resolved**: End of Sprint P3
```

---

## Task Integration

Each checkpoint has corresponding tasks in the roadmap files:

### v0.5.0 Checkpoints

**Sprint S3, Section 3.6** ([tasks-v0.5.0-roadmap.md](../../dev-planning/tasks/tasks-v0.5.0-roadmap.md)):
- [ ] 3.6.1 Review PRD Open Questions
- [ ] 3.6.2 Document learnings from security implementation

### v1.0.0 Checkpoints

| Sprint | Section | Tasks |
|--------|---------|-------|
| P1 | 1.3 | Review security open questions |
| P3 | 3.3 | Review performance open questions |
| P5 | 5.3 | Review DX open questions |
| P6 | 6.3 | Review debugging tool questions |
| P7 | 7.4 | Review performance open questions |
| P9 | 9.3 | Review documentation open questions |
| P13 | 13.6 | Complete PRD review + retrospective |

---

## Retrospective Process (Sprint P13)

### Create Retrospective Document

**File**: `.cursor/dev-planning/lessons-learned/v1.0.0-retro.md`

**Template**:
```markdown
# v1.0.0 Retrospective

## What Went Well
- List successes
- Highlight achievements vs targets

## What Could Be Improved
- Challenges encountered
- Bottlenecks identified

## Lessons Learned
- Technical insights
- Process improvements

## Metrics vs Targets
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Tests | 800+ | XXX | ✅/❌ |
| Coverage | ≥95% | XX% | ✅/❌ |
| ...

## Recommendations for v1.1.0
- Carry-forward items
- New opportunities
```

### Schedule Post-Release Review

**Timeline**: 2 weeks after v1.0.0 release

**Agenda**:
1. Review community feedback from GitHub Discussions
2. Check PyPI download statistics
3. Assess adoption metrics (stars, forks, issues)
4. Answer remaining open questions (Q7, Q9, Q10)
5. Update PRD with decisions
6. Begin v1.1.0 planning if needed

---

## Question Status Tracker

### v0.5.0 Questions

| ID | Question | Status | Review Point | Resolution |
|----|----------|--------|--------------|------------|
| Q3 | HMAC signing in v1.0.0? | ⏳ Pending | Sprint S3 | TBD |

### v1.0.0 Questions

| ID | Question | Status | Review Point | Resolution |
|----|----------|--------|--------------|------------|
| Q1 | Connection pool size | ⏳ Pending | Sprint P3 | TBD |
| Q2 | Adaptive rate limiting | ✅ Resolved | Sprint P7 | DD-012: Defer to v1.1.0+ |
| Q3 | HMAC signing (if deferred) | ⏳ Pending | Sprint P1 | TBD |
| Q4 | Auth scheme for examples | ✅ Resolved | Sprint P5 | DD-010: Both Bearer + OAuth2 concept |
| Q5 | Trace JSON export | ✅ Resolved | Sprint P6 | DD-011: Implemented --format json in v1.0.0 |
| Q6 | pytest-asap plugin | ✅ Resolved | Sprint P5 | Defer to v1.1.0 |
| Q7 | Video tutorials | ⏳ Pending | Post-release | TBD |
| Q8 | i18n languages | ✅ Resolved | Sprint P9 | DD-013: English-only v1.0.0, reassess v1.1.0 |
| Q9 | Discord/Slack community | ⏳ Pending | Post-release | TBD |
| Q10 | Foundation sponsorship | ⏳ Pending | Post-release | TBD |
| Q11 | Next transport binding | ⏳ Pending | v1.1.0 planning | TBD |
| Q12 | Message encryption | ⏳ Pending | v1.1.0 planning | TBD |

---

## Changelog

| Date | Version | Change |
|------|---------|--------|
| 2026-01-24 | 1.0 | Initial review schedule created |

---

**Maintainer**: Project leads
**Review Frequency**: Update after each checkpoint
**Status**: ✅ Active tracking document
