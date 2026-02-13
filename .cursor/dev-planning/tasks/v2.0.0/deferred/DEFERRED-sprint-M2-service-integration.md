> [!CAUTION]
> **DEFERRED (2026-02-12, Lean Marketplace Pivot)**: Service Integration sprint removed. v2.0 Web App reads from Lite Registry — no backend services to integrate. These integrations move to v2.1 when Registry API Backend is built. See [deferred-backlog.md](../../../../product-specs/strategy/deferred-backlog.md).
>
> This sprint file is preserved for reference.

# Sprint M2: Service Integration (DEFERRED)

> **Goal**: Integrate all v1.x services (OAuth2, Metering, SLA, Audit)
> **Prerequisites**: Sprint M1 completed (Production Registry)
> **Parent Roadmap**: [tasks-v2.0.0-roadmap.md](../tasks-v2.0.0-roadmap.md)

---

## Relevant Files

- `src/asap/registry/middleware.py` - Auth integration
- `src/asap/economics/metering.py` - Usage tracking
- `src/asap/economics/audit.py` - Audit logging

---

## Context

This sprint connects the Registry to the rest of the ASAP ecosystem, enabling paid storage, authenticated access, and compliance logging.

---

## Task 2.1: OAuth2 Integration

### Sub-tasks

- [ ] 2.1.1 Add OAuth2 middleware to Registry

- [ ] 2.1.2 Protect mutation endpoints

- [ ] 2.1.3 Allow public reads

- [ ] 2.1.4 Test token validation

**Acceptance Criteria**:
- [ ] Auth enforced on writes

---

## Task 2.2: Metering Integration

### Sub-tasks

- [ ] 2.2.1 Track Registry API calls

- [ ] 2.2.2 Connect to Metering service

- [ ] 2.2.3 Emit usage events

**Acceptance Criteria**:
- [ ] Registry usage tracked

---

## Task 2.3: SLA Integration

### Sub-tasks

- [ ] 2.3.1 Include SLA in agent responses

- [ ] 2.3.2 Add SLA filter to search

- [ ] 2.3.3 Display compliance status

**Acceptance Criteria**:
- [ ] SLA visible in search

---

## Task 2.4: Audit Integration

### Sub-tasks

- [ ] 2.4.1 Log registrations

- [ ] 2.4.2 Log updates

- [ ] 2.4.3 Log deletions

- [ ] 2.4.4 Test audit trail

**Acceptance Criteria**:
- [ ] All mutations audited

---

## Sprint M2 Definition of Done

- [ ] OAuth2 integrated
- [ ] Metering active
- [ ] SLA visible
- [ ] Audit logging complete

**Total Sub-tasks**: ~15
