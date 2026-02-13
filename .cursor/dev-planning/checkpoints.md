# Documentation Checkpoints

> **Purpose**: Formal review points to update documentation with learnings
> **Created**: 2026-02-06
> **Updated**: 2026-02-12 (Lean Marketplace pivot)

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
- [ ] `tasks-v1.2.0-roadmap.md` — adjust estimates (now 4 sprints / 13 tasks post-Lean pivot)
- [ ] `lessons-learned/v1.1.0-retro.md` — create retrospective

---

### CP-2: Post v1.2.0 Release

**When**: After v1.2.0 ships

**Review**:
- [ ] Ed25519 PKI complexity
- [ ] Compliance harness effectiveness — is it usable by third parties?
- [ ] Lite Registry (SD-11): Is GitHub Pages still sufficient? Should Registry API Backend be accelerated for v2.0?
- [ ] Time taken vs estimated

**Update**:
- [ ] `prd-v1.3-roadmap.md` — refine observability based on PKI learnings
- [ ] `tasks-v1.3.0-roadmap.md` — adjust estimates (now 3 sprints / 13 tasks post-Lean pivot)
- [ ] `lessons-learned/v1.2.0-retro.md` — create retrospective

> [!NOTE]
> Registry API review item removed (deferred to v2.1). Compliance harness is now the primary deliverable to evaluate.

---

### CP-3: Post v1.3.0 Release

**When**: After v1.3.0 ships

**Review**:
- [ ] Observability metering implementation lessons
- [ ] Delegation token complexity
- [ ] SLA framework effectiveness
- [ ] Lite Registry capacity — can it handle target 100+ agents for v2.0?

**Update**:
- [ ] `prd-v2.0-roadmap.md` — major update with all v1.x learnings
- [ ] `tasks-v2.0.0-roadmap.md` — realistic estimates (now 4 sprints / 20 tasks post-Lean pivot)
- [ ] `lessons-learned/v1.3.0-retro.md` — create retrospective
- [ ] Web App tech stack decisions (Next.js + Lite Registry)

---

### CP-4: Post v2.0.0 M2 (Web App Features)

**When**: After completing sprints M1-M2

**Review**:
- [ ] Lite Registry data layer — is `registry.json` SSG/ISR working well?
- [ ] Web App performance with static registry data
- [ ] Client-side search/filter UX

**Update**:
- [ ] `sprint-M3-verified-payments.md` and `sprint-M4-launch-prep.md` — adjust estimates
- [ ] Evaluate if Registry API Backend should be built for v2.1

---

### CP-5: Post v2.0.0 M4 (Launch)

**When**: 2 weeks after launch

**Review**:
- [ ] Launch success metrics (per PRD: 100+ agents, 500+ weekly visits)
- [ ] User feedback
- [ ] What to do next (v2.1 Registry API Backend? v2.2 DeepEval?)

**Create**:
- [ ] `lessons-learned/v2.0.0-retro.md` — comprehensive retrospective
- [ ] `vision-v2.1.md` — Registry API Backend + deferred features roadmap

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
| v1.2.0 | 18-26 | — | — |
| v1.3.0 | 15-22 | — | — |
| v2.0.0 | 23-33 | — | — |

> [!NOTE]
> Estimates updated after Lean Marketplace pivot: v1.2 reduced (6→4 sprints), v1.3 reduced (4→3 sprints), v2.0 reduced (6→4 sprints).

---

## Related Documents

- [roadmap-to-marketplace.md](../product-specs/strategy/roadmap-to-marketplace.md)
- [deferred-backlog.md](../product-specs/strategy/deferred-backlog.md)
- [lessons-learned/](./lessons-learned/)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-06 | Initial checkpoints document |
| 2026-02-12 | **Lean Marketplace pivot**: Updated CP-2 (removed Registry API review), CP-3 (metering→observability), CP-4 (renamed from "Marketplace Core" to "Web App Features"), CP-5 (merged with CP-6, updated metrics). Reduced from 6 checkpoints to 5. Updated velocity estimates. |
