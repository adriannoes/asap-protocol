# ASAP Protocol v1.1 - Planned Features

> **Status**: ⚠️ **DEPRECATED** — This document was the original backlog from the v1.0.0 gap analysis.
> It has been superseded by the structured sprint planning in:
> - **PRD**: [prd-v1.1-roadmap.md](../../../product-specs/prd/prd-v1.1-roadmap.md)
> - **Tasks**: [tasks-v1.1.0-roadmap.md](./tasks-v1.1.0-roadmap.md)
> - **Sprints**: S1 (OAuth2), S2 (Discovery + Liveness), S2.5 (State Storage), S3 (WebSocket), S4 (Webhooks + Release)
>
> **Kept for historical reference only.** Do not use this document for planning.
>
> **Key changes from this backlog** (2026-02-07 strategic review):
> - Item 4 (State Storage Interface) → Promoted to Sprint S2.5 with full SQLite implementation (SD-9, ADR-13)
> - Item 1 (SSRF prevention) → Included in Sprint S4 (Webhooks)
> - Item 5 (Message Broker) → Deferred to v2.0+ per SD-3
> - Item 6 (DNS-SD) → Deferred to v1.1.1+ (P3)
> - Timeline estimates below are **outdated** — see tasks-v1.1.0-roadmap.md for current estimates
>
> **Scope**: Post-v1.0.0 enhancements
> **Parent PRD**: [prd-v1.1-roadmap.md](../../../product-specs/prd/prd-v1.1-roadmap.md)

---

## Overview

This document tracks features explicitly deferred from v1.0.0 based on gap analysis between the v1.0.0 roadmap and the original protocol specification (`v0-original-specs.md`).

All items below are **planned but not committed** to v1.1.0.

---
### 1. Core Reliability & Compliance (Priority: Critical)

> **Strategic Alignment**: This section adheres to the "Compliance First" pillar, prioritizing security and resilience.

- [ ] **[P0]** Security: validate callback URLs (Prevent SSRF)
- [ ] **[P1]** Rate limiting for callback endpoints (DoS protection)
- [ ] **[P1]** Retry logic for failed deliveries (Resilience)
- [ ] **[P2]** Callback event filtering

---

### 4. State Storage Interface

**Source**: [v0-original-specs.md §13.2](../../../product-specs/prd/v0-original-specs.md)

**Current State**:
- Spec lists this as **open decision**
- Currently implementation-specific (opaque)

**Scope for v1.1**:
```
[ ] Define abstract state storage interface
[ ] Reference implementation: in-memory
[ ] Reference implementation: SQLite
[ ] Reference implementation: Redis
[ ] Migration guide for custom implementations
```

**Options**:
1. Opaque (current) - Implementation chooses
2. Interface-defined - Abstract interface in spec
3. Reference implementations - SQLite/Redis examples

**Recommendation**: Option 2 for interoperability

---

### 5. Message Broker Integration (NATS/Pub-Sub)

**Source**: [v0-original-specs.md §6.3, §7.4](../../../product-specs/prd/v0-original-specs.md)

**Current State**:
- Explicitly excluded from v1.0.0 PRD
- Spec defines `broker` config with NATS example
- "Mesh" topology pattern requires broker

**Scope for v1.1**:
```
[ ] NATS transport binding
[ ] Subject-based routing
[ ] Reply subject handling
[ ] Connection pooling for broker
[ ] Dead letter queue handling
[ ] (Optional) Kafka support
```

**Note**: May be better as external package (`asap-nats`)

---

### 6. DNS-SD Discovery

**Source**: [v0-original-specs.md §7.4](../../../product-specs/prd/v0-original-specs.md)

**Current State**:
- Spec mentions `_asap._tcp.example.com`
- Listed as "deferred" in MVP scope
- Well-known URI discovery is primary method

**Scope for v1.1**:
```
[ ] DNS-SD service type registration
[ ] mDNS/Bonjour support for local discovery
[ ] Integration with service mesh (Consul, etc.)
```

**Priority**: Lower - well-known URI covers most use cases

---

## Version Negotiation (Covered in v1.0.0)

**Note**: After analysis, version negotiation is **already covered** by contract testing in v1.0.0 (Sprint P8.2). The downgrade protocol from the spec is validated via backward compatibility tests.

---

## Timeline Estimate

| Phase | Features | Duration |
|-------|----------|----------|
| v1.1.0 | OAuth2, WebSocket binding | 6-8 weeks |
| v1.2.0 | Webhook callbacks, State interface | 4-6 weeks |
| v1.3.0 | Broker integration, DNS-SD | 6-8 weeks |

---

## Related Documents

- **Original Spec**: [v0-original-specs.md](../../../product-specs/v0-original-specs.md)
- **v1.0.0 Roadmap**: [tasks-v1.0.0-roadmap.md](./v1.0.0/tasks-v1.0.0-roadmap.md)
- **PRD**: [prd-v1.1-roadmap.md](../../../product-specs/prd/prd-v1.1-roadmap.md)
- **Gap Analysis**: Conversation 2026-01-30

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial draft based on v1.0.0 gap analysis |
