# Tasks: ASAP Protocol v1.3.0 Roadmap

> **High-level task overview** for v1.3.0 milestone (Economics Layer)
>
> **Parent PRD**: [prd-v1.3-roadmap.md](../../../product-specs/prd/prd-v1.3-roadmap.md)
> **Prerequisite**: v1.2.0 released
> **Target Version**: v1.3.0
> **Focus**: Usage Metering, Delegation Tokens, SLA Framework, Audit Logging
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [E1-E2: Metering & Delegation](./tasks-v1.3.0-economics-detailed.md)
> - [E3-E4: SLA & Release](./tasks-v1.3.0-sla-detailed.md)

---

## Strategic Context

v1.3.0 is the **final infrastructure release** before v2.0 Marketplace:
- **Metering**: Foundation for pay-per-use billing
- **Delegation**: Trust chains for enterprise hierarchies
- **SLA**: Service guarantees that consumers can rely on
- **Audit**: Compliance and dispute resolution

---

## Sprint E1: Usage Metering

**Goal**: Track and report resource consumption per task

### Tasks

- [ ] 1.1 Design metering data model
  - Goal: Define metrics schema (tokens, duration, calls)
  - Deliverable: `src/asap/economics/metering.py`

- [ ] 1.2 Implement metering hooks
  - Goal: Capture metrics during task execution
  - Deliverable: Middleware integration

- [ ] 1.3 Implement metering storage
  - Goal: Store and query usage data
  - Deliverable: Time-series storage interface

- [ ] 1.4 Implement metering API
  - Goal: GET /usage endpoint for querying
  - Deliverable: REST API

### Definition of Done
- [ ] Metering captures all task metrics
- [ ] API returns usage by agent/consumer/period
- [ ] <1% drift from actual usage
- [ ] Test coverage >95%

---

## Sprint E2: Delegation Tokens

**Goal**: Enable trust chains with spending controls

### Tasks

- [ ] 2.1 Design delegation token model
  - Goal: Token with scopes, constraints, signature
  - Deliverable: `src/asap/economics/delegation.py`

- [ ] 2.2 Implement token creation and signing
  - Goal: Create tokens signed by delegator
  - Deliverable: CLI + API

- [ ] 2.3 Implement token validation
  - Goal: Verify chain, constraints, expiration
  - Deliverable: Middleware validation

- [ ] 2.4 Implement token revocation
  - Goal: Revoke tokens with immediate effect
  - Deliverable: Revocation list

### Definition of Done
- [ ] Tokens created with scopes and limits
- [ ] Validation rejects expired/revoked/over-limit
- [ ] <10ms validation overhead
- [ ] Test coverage >95%

---

## Sprint E3: SLA Framework

**Goal**: Define and enforce service level agreements

### Tasks

- [ ] 3.1 Add SLA schema to manifest
  - Goal: availability, latency, error_rate fields
  - Deliverable: Manifest schema extension

- [ ] 3.2 Implement SLA tracking
  - Goal: Measure actual vs promised SLA
  - Deliverable: SLA metrics collection

- [ ] 3.3 Implement breach detection
  - Goal: Real-time breach alerts
  - Deliverable: Alert hooks

- [ ] 3.4 Implement SLA API
  - Goal: GET /agents/{id}/sla endpoint
  - Deliverable: SLA history API

### Definition of Done
- [ ] SLA defined in manifest
- [ ] Breaches detected in real-time
- [ ] SLA history queryable
- [ ] Test coverage >95%

---

## Sprint E4: Audit Logging & Release

**Goal**: Compliance logging and v1.3.0 release

### Tasks

- [ ] 4.1 Implement audit log format
  - Goal: Append-only, tamper-evident
  - Deliverable: `src/asap/economics/audit.py`

- [ ] 4.2 Log all billable events
  - Goal: Task start, complete, usage reports
  - Deliverable: Audit integration

- [ ] 4.3 Implement audit query API
  - Goal: Query by task, agent, time
  - Deliverable: REST API

- [ ] 4.4 Comprehensive testing
  - Goal: All tests pass
  - Deliverable: Test suite

- [ ] 4.5 Release preparation
  - Goal: CHANGELOG, docs, version bump
  - Deliverable: v1.3.0 release

### Definition of Done
- [ ] Audit logs all events
- [ ] Query API functional
- [ ] v1.3.0 published to PyPI

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| E1 | 4 | Usage Metering | 5-7 |
| E2 | 4 | Delegation Tokens | 5-7 |
| E3 | 4 | SLA Framework | 4-6 |
| E4 | 5 | Audit + Release | 4-6 |

**Total**: 17 high-level tasks across 4 sprints

---

## Progress Tracking

**Overall Progress**: 0/17 tasks completed (0%)

**Last Updated**: 2026-02-06

---

## Checkpoint: Post-v1.3.0 Review

After releasing v1.3.0, conduct a checkpoint review:

- [ ] Update v2.0.0 PRD with learnings
- [ ] Review and update v2.0.0 sprint estimates
- [ ] Document lessons learned
- [ ] Validate Economics Layer meets v2.0 requirements

---

## Related Documents

- **PRD**: [prd-v1.3-roadmap.md](../../../product-specs/prd/prd-v1.3-roadmap.md)
- **Roadmap**: [roadmap-to-marketplace.md](../../../product-specs/roadmap-to-marketplace.md)
