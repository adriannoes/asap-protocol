# Documentation Checkpoints

> **Purpose**: Formal review points to update documentation with learnings
> **Created**: 2026-02-06

---

## Why Checkpoints?

As a solo developer, it's easy to lose context between sprints. These checkpoints ensure:
1. **Lessons captured**: What worked, what didn't
2. **Docs updated**: Next version PRDs refined with learnings  
3. **Estimates adjusted**: Realistic planning based on actual velocity
4. **Context preserved**: Knowledge carries forward to v2.0.0

---

## Checkpoint Schedule

### CP-1: Post v1.1.0 Release

**When**: After v1.1.0 ships (release preparation done 2026-02-10; publish in Task 4.7).

Pre-release: Release materials (CHANGELOG, README, AGENTS.md, secure_agent example) completed. Full review and velocity update to be done after v1.1.0 ships.

**Review**:
- [ ] OAuth2 implementation complexity — update v1.2 estimates?
- [ ] WebSocket lessons learned
- [ ] Discovery patterns that worked
- [ ] State Storage Interface (SD-9): Did SQLite impl meet needs? Is `MeteringStore` interface sufficient for v1.3?
- [ ] Agent Liveness (SD-10): Is the health endpoint effective? Is `ttl_seconds` default (300s) appropriate?
- [ ] `SnapshotStore` sync vs async: Should we evolve to async Protocol? (Breaking change analysis)
- [ ] Lite Registry (SD-11, ADR-15): Is GitHub Pages adequate? Is the multi-endpoint schema flexible enough?
- [ ] WebSocket MessageAck (ADR-16): Is `AckAwareClient` timeout (30s default) appropriate? Retransmission working correctly?
- [ ] Custom Claims binding (ADR-17): Are Custom Claims practical with all IdPs? Is the allowlist fallback needed often?
- [ ] Best Practices Failover doc: Is the `StateQuery`/`StateRestore` pattern sufficient without formal `TaskHandover` payload?
- [ ] Time taken vs estimated

**Update**:
- [ ] `prd-v1.2-roadmap.md` — refine based on auth + storage learnings
- [ ] `prd-v1.3-roadmap.md` — confirm `MeteringStore` interface meets v1.3 needs
- [ ] `tasks-v1.2.0-roadmap.md` — adjust estimates
- [ ] `lessons-learned/v1.1.0-retro.md` — create retrospective

---

### CP-2: Post v1.2.0 Release

**When**: After v1.2.0 ships

**Review**:
- [ ] Ed25519 PKI complexity
- [ ] Registry API patterns
- [ ] Compliance harness effectiveness
- [ ] Time taken vs estimated

**Update**:
- [ ] `prd-v1.3-roadmap.md` — refine economics based on PKI learnings
- [ ] `tasks-v1.3.0-roadmap.md` — adjust estimates
- [ ] `lessons-learned/v1.2.0-retro.md` — create retrospective

---

### CP-3: Post v1.3.0 Release

**When**: After v1.3.0 ships

**Review**:
- [ ] Metering implementation lessons
- [ ] Delegation token complexity
- [ ] SLA framework effectiveness
- [ ] Infrastructure patterns for v2.0

**Update**:
- [ ] `prd-v2.0-roadmap.md` — major update with all v1.x learnings
- [ ] `tasks-v2.0.0-roadmap.md` — realistic estimates
- [ ] `lessons-learned/v1.3.0-retro.md` — create retrospective
- [ ] Tech stack decisions for Web App

---

### CP-4: Post v2.0.0 M2 (Marketplace Core)

**When**: After completing sprints M1-M2

**Review**:
- [ ] Production deployment challenges
- [ ] Integration complexity
- [ ] Performance characteristics

**Update**:
- [ ] `sprint-M3-webapp-foundation.md` and `sprint-M4-webapp-features.md` — adjust Web App estimates
- [ ] Infrastructure decisions for Web App
- [ ] Document production patterns

---

### CP-5: Post v2.0.0 M4 (Web App Core)

**When**: After completing sprints M3-M4

**Review**:
- [ ] Frontend tech stack effectiveness
- [ ] UX feedback from early testing
- [ ] Performance on real users

**Update**:
- [ ] `sprint-M5-verified-payments.md` and `sprint-M6-launch-prep.md` — adjust launch estimates
- [ ] Prioritize M5-M6 based on feedback

---

### CP-6: Post v2.0.0 Launch

**When**: 2 weeks after launch

**Review**:
- [ ] Launch success metrics
- [ ] User feedback
- [ ] What to do next (v2.1?)

**Create**:
- [ ] `lessons-learned/v2.0.0-retro.md` — comprehensive retrospective
- [ ] `vision-v2.1.md` — if continuing development

---

## Checkpoint Process

For each checkpoint:

1. **Take 30-60 minutes** to review honestly
2. **Update documents** while context is fresh
3. **Adjust estimates** based on actual velocity  
4. **Capture patterns** that can be reused
5. **Commit changes** with descriptive message

---

## Velocity Tracking

Track actual vs estimated to improve future planning:

| Version | Estimated Days | Actual Days | Velocity |
|---------|----------------|-------------|----------|
| v1.1.0 | 31-41 | — | — |
| v1.2.0 | 28-40 | — | — |
| v1.3.0 | 18-26 | — | — |
| v2.0.0 | 38-53 | — | — |

---

## Related Documents

- [roadmap-to-marketplace.md](../product-specs/roadmap-to-marketplace.md)
- [lessons-learned/](./lessons-learned/)
