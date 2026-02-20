# Sprint M4: Launch Preparation

> **Goal**: Final polish, security audit, and launch
> **Prerequisites**: Sprint M3 completed (Verified Badge)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](./tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- Prometheus/Grafana configuration
- Sentry configuration
- Documentation updates
- Production deployment scripts

---

## Context

This is the final sprint before v2.0.0 launch. Focus on security, performance, and monitoring.

---

## Task 4.1: Security Audit

### Sub-tasks

- [ ] 4.1.1 Internal security review (Checklist)
  - [ ] **Secrets**: Verify no `.env` committed
  - [ ] **Rate Limiting**: Verify `upstash/ratelimit` or Vercel KV limits on API routes
  - [ ] **Input Validation**: Check all Zod schemas are strict
  - [ ] **CSRF**: Verify `NextAuth` (Auth.js) state checks

- [ ] 4.1.2 Fix identified issues

- [ ] 4.1.3 Document security practices (`SECURITY.md`)
  - Reporting policy
  - Scope of coverage

**Acceptance Criteria**:
- [ ] Security audit passed

- [ ] 4.1.4 Commit Security
  - **Command**: `git commit -m "chore(security): apply audit fixes"`

---

## Task 4.2: Performance Optimization

### Sub-tasks

- [ ] 4.2.1 Script 10k test agents

- [ ] 4.2.2 Run load test (1000 req/sec)

- [ ] 4.2.3 Identify bottlenecks

- [ ] 4.2.4 Optimize as needed

**Acceptance Criteria**:
- [ ] System handles expected load

- [ ] 4.2.5 Commit Optimization
  - **Command**: `git commit -m "perf(web): apply load testing optimizations"`

---

## Task 4.3: Documentation

### Sub-tasks

- [ ] 4.3.1 Web App user guide

- [ ] 4.3.2 Verified badge guide

**Acceptance Criteria**:
- [ ] Documentation complete

- [ ] 4.3.3 Commit Docs
  - **Command**: `git commit -m "docs: update user guides for v2.0"`

---

## Task 4.4: Beta Program

### Sub-tasks

- [ ] 4.4.1 Invite beta developers

- [ ] 4.4.2 Collect feedback

- [ ] 4.4.3 Fix critical issues

- [ ] 4.4.4 Reach 100+ registrations

**Acceptance Criteria**:
- [ ] 100+ beta agents

- [ ] 4.4.5 Commit Beta Fixes
  - **Command**: `git commit -m "fix: address beta feedback"`

---

## Task 4.5: Launch

### Sub-tasks

- [ ] 4.5.1 Final checklist review
  - Domain DNS propagated?
  - GitHub OAuth Production App configured?
  - Sentry DSN active?

- [ ] 4.5.2 Deploy to production (Promote Vercel Preview to Prod)

- [ ] 4.5.3 Announce on social/blog (Twitter/LinkedIn)

- [ ] 4.5.4 Monitor post-launch (Sentry + Vercel Analytics)

**Acceptance Criteria**:
- [ ] v2.0.0 launched!

- [ ] 4.5.5 Tag Logic Release
  - **Command**: `git tag v2.0.0`
  - **Command**: `git push origin v2.0.0`

---

## Sprint M4 Definition of Done

- [ ] Security audit passed
- [ ] Load testing passed
- [ ] Monitoring operational
- [ ] 100+ beta agents
- [ ] v2.0.0 launched!

**Total Sub-tasks**: ~20

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v2.0.0 Roadmap](./tasks-v2.0.0-roadmap.md)
