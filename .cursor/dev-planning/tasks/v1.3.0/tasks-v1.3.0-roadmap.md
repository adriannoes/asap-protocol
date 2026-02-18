# Tasks: ASAP Protocol v1.3.0 Roadmap

> **High-level task overview** for v1.3.0 milestone (Observability & Delegation)
>
> **Parent PRD**: [prd-v1.3-roadmap.md](../../../product-specs/prd/prd-v1.3-roadmap.md)
> **Prerequisite**: v1.2.0 released; [Security Remediation](../v1.2.1/plan-security-remediation-pre-v1.3.md) (P0–P2) before v1.3.0
> **Target Version**: v1.3.0
> **Focus**: Observability Metering, Delegation Tokens, SLA Framework
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [E1: Observability Metering](./sprint-E1-usage-metering.md)
> - [E2: Delegation Tokens](./sprint-E2-delegation-tokens.md)
> - [E3: SLA Framework & Release](./sprint-E3-sla-framework.md)
>
> **Lean Marketplace Pivot**: Audit logging (formerly E4) has been deferred to v2.1+. Metering reframed as observability (visibility, not billing). See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

---

## Strategic Context

v1.3.0 is the **final infrastructure release** before v2.0 Marketplace:
- **Observability Metering**: Usage visibility (not billing) — uses `MeteringStore` interface from v1.1 (SD-9, ADR-13)
- **Delegation**: Trust chains for enterprise hierarchies
- **SLA**: Service guarantees — uses health endpoint from v1.1 for availability monitoring (SD-10, ADR-14)

> [!NOTE]
> **Deferred from v1.3**: Credit system (to v3.0), Audit logging (to v2.1+). See [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md).

### Prerequisites from v1.1.0 / v1.2.0

| Deliverable | Usage in v1.3 |
|-------------------|------------|
| `MeteringStore` Protocol (v1.1) | Observability metering storage backend (Sprint E1) |
| Health endpoint (v1.1) | SLA uptime/availability monitoring (Sprint E3) |
| `ttl_seconds` in Manifest (v1.1) | SLA availability measurement (Sprint E3) |
| Ed25519 signing (v1.2) | Delegation tokens signed with agent keys |
| Compliance Harness (v1.2) | Extended to validate delegation flows |

---

### Sprint E4: Security Hardening (Type Safety)

- **Goal**: Tighten `dict[str, Any]` typing and improve validation
- **Details**: [Sprint E4 Plan](./sprint-E4-type-safety.md)
- **Status**: Pending

## Sprint E1: Observability Metering

**Goal**: Track and report resource consumption per task (visibility, not billing)

### Tasks

- [x] 1.1 Design metering data model
  - Goal: Define metrics schema (tokens, duration, calls)
  - Deliverable: `src/asap/economics/metering.py`

- [x] 1.2 Implement metering hooks
  - Goal: Capture metrics during task execution
  - Deliverable: Middleware integration

- [x] 1.3 Implement metering storage
  - Goal: Store and query usage data via `MeteringStore`
  - Deliverable: SQLite reference implementation

- [x] 1.4 Implement metering API
  - Goal: REST API for querying and reporting usage
  - Deliverable: GET /usage, /usage/aggregate, /usage/summary, /usage/agents, /usage/consumers, /usage/stats, /usage/export; POST /usage, /usage/batch, /usage/purge, /usage/validate
  - See [sprint-E1-usage-metering.md](./sprint-E1-usage-metering.md) for full sub-task breakdown (~31 items)

### Definition of Done
- [x] Metering captures all task metrics
- [x] API returns usage by agent/consumer/period
- [ ] <1% drift from actual usage
- [x] Test coverage >95%

---

## Sprint E2: Delegation Tokens

**Goal**: Enable trust chains with spending controls

### Tasks

- [x] 2.1 Design delegation token model
  - Goal: Token with scopes, constraints, signature
  - Note: Financial limits (`max_cost_usd`) optional/deferred to v3.0
  - Deliverable: `src/asap/economics/delegation.py`

- [x] 2.2 Implement token creation and signing
  - Goal: Create tokens signed by delegator (Ed25519 from v1.2)
  - Deliverable: CLI + API

- [x] 2.3 Implement token validation
  - Goal: Verify chain, constraints, expiration
  - Deliverable: Middleware validation

- [x] 2.4 Implement token revocation
  - Goal: Revoke tokens with immediate effect
  - Deliverable: Revocation storage (SQLite), API, CLI, cascade

- [x] 2.5 Observability for delegations
  - Goal: List/inspect issued tokens (GET /delegations, GET /delegations/{id})
  - Deliverable: delegation_api list/detail endpoints

### Definition of Done
- [x] Tokens created with scopes and limits
- [x] Validation rejects expired/revoked/over-limit
- [ ] <10ms validation overhead
- [x] Test coverage >95%

---

## Sprint E3: SLA Framework & Release

**Goal**: Define and enforce service level agreements, then release v1.3.0

### Tasks

- [ ] 3.1 Add SLA schema to manifest
  - Goal: availability, latency, error_rate fields
  - Deliverable: Manifest schema extension

- [ ] 3.2 Implement SLA tracking
  - Goal: Measure actual vs promised SLA (uses health endpoint)
  - Deliverable: SLA metrics collection

- [ ] 3.3 Implement breach detection
  - Goal: Real-time breach alerts
  - Deliverable: Alert hooks

- [ ] 3.4 Comprehensive testing
  - Goal: All tests pass, integration with v1.1/v1.2 features
  - Deliverable: Test suite

- [ ] 3.5 Create End-to-End Demo / Showcase
  - Goal: "See it working" - Script combining Metering, Delegation, and SLA
  - Deliverable: `examples/v1_3_0_showcase.py`

- [ ] 3.6 Release preparation
  - Goal: CHANGELOG, docs, version bump
  - Deliverable: v1.3.0 release on PyPI

### Definition of Done
- [ ] SLA defined in manifest
- [ ] Breaches detected in real-time
- [ ] End-to-End demo runs successfully
- [ ] v1.3.0 published to PyPI
- [ ] Test coverage >95%

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| E1 | 4 | Observability Metering | 5-7 |
| E2 | 4 | Delegation Tokens | 5-7 |
| E3 | 6 | SLA, Demo & Release | 5-8 |

**Total**: 14 high-level tasks across 3 sprints

---

## Progress Tracking

**Overall Progress**: 2/13 tasks completed (15%)

**Last Updated**: 2026-02-17

---

## Checkpoint: Post-v1.3.0 Review

After releasing v1.3.0, conduct a checkpoint review:

- [ ] Update v2.0.0 PRD with learnings
- [ ] Review and update v2.0.0 sprint estimates
- [ ] Document lessons learned
- [ ] Validate Observability Layer meets v2.0 requirements

---

## Related Documents

- **PRD**: [prd-v1.3-roadmap.md](../../../product-specs/prd/prd-v1.3-roadmap.md)
- **Deferred Backlog**: [deferred-backlog.md](../../../product-specs/strategy/deferred-backlog.md)
- **Roadmap**: [roadmap-to-marketplace.md](../../../product-specs/strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../../product-specs/strategy/vision-agent-marketplace.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-06 | Initial task roadmap |
| 2026-02-12 | **Lean Marketplace pivot**: Removed Audit Logging sprint (E4), reframed metering as observability, merged release into E3, reduced from 4 sprints (17 tasks) to 3 sprints (13 tasks) |
| 2026-02-17 | **Sprint E1 complete**: Metering API expanded (summary, batch, agents, consumers, stats, purge, validate, export); roadmap aligned with sprint sub-tasks |
