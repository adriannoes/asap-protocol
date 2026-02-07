# PRD: ASAP Protocol v1.3.0 — Economics Layer

> **Product Requirements Document**
>
> **Version**: 1.3.0
> **Status**: APPROVED
> **Created**: 2026-02-06
> **Last Updated**: 2026-02-06

---

## 1. Executive Summary

### 1.1 Purpose

v1.3.0 establishes the **Economics Layer** for the Agent Marketplace. This release delivers:
- **Usage Metering**: Track and report resource consumption
- **Delegation Tokens**: Trust chains for hierarchical agent relationships
- **SLA Framework**: Define and enforce service level agreements
- **Audit Logging**: Compliance and dispute resolution support

### 1.2 Strategic Context

v1.3.0 is the final step before the v2.0 Marketplace. See [roadmap-to-marketplace.md](../roadmap-to-marketplace.md).

**Prerequisite**: v1.2.0 (Trust Layer) released — agents must have signed manifests and be discoverable via Registry.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Usage metering accuracy | <1% drift from actual | P1 |
| Delegation token validation | <10ms overhead | P1 |
| SLA breach detection | Real-time alerts | P1 |
| Audit log completeness | 100% of billable events | P2 |

---

## 3. User Stories

### Agent Provider
> As an **agent provider**, I want to **track usage metrics (tokens, API calls, duration)** so that **I can bill consumers accurately**.

### Agent Consumer
> As an **agent consumer**, I want to **set spending limits via delegation tokens** so that **I control costs when using third-party agents**.

### Enterprise Admin
> As an **enterprise admin**, I want to **define SLAs and audit all interactions** so that **I can ensure compliance and resolve disputes**.

---

## 4. Functional Requirements

### 4.1 Usage Metering (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| METER-001 | Track tokens_in, tokens_out per task | MUST |
| METER-002 | Track duration_ms per task | MUST |
| METER-003 | Track API calls count | MUST |
| METER-004 | Aggregate by agent, consumer, time period | MUST |
| METER-005 | Export metering data (JSON, CSV) | SHOULD |
| METER-006 | Real-time usage dashboard (via API) | SHOULD |

**Usage Event Schema**:
```json
{
  "usage": {
    "task_id": "task_123",
    "agent": "urn:asap:agent:provider",
    "consumer": "urn:asap:agent:consumer",
    "metrics": {
      "tokens_in": 1500,
      "tokens_out": 2300,
      "duration_ms": 4500,
      "api_calls": 3
    },
    "timestamp": "2026-02-06T12:00:00Z"
  }
}
```

---

### 4.2 Delegation Tokens (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| DELEG-001 | Create delegation token with scopes | MUST |
| DELEG-002 | Set spending limits (max_cost_usd) | MUST |
| DELEG-003 | Set expiration (expires_at) | MUST |
| DELEG-004 | Validate token chain (delegator → delegate) | MUST |
| DELEG-005 | Revoke delegation tokens | MUST |
| DELEG-006 | Nested delegation (with constraints) | SHOULD |

**Delegation Token Schema**:
```json
{
  "delegation": {
    "id": "del_abc123",
    "delegator": "urn:asap:agent:enterprise",
    "delegate": "urn:asap:agent:team",
    "scopes": ["research.execute", "data.read"],
    "constraints": {
      "max_cost_usd": 100.00,
      "max_tasks": 50,
      "expires_at": "2026-02-28T00:00:00Z"
    },
    "signature": "..."
  }
}
```

---

### 4.3 SLA Framework (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SLA-001 | Define SLA in manifest (latency, uptime) | MUST |
| SLA-002 | Track SLA compliance per agent | MUST |
| SLA-003 | Breach detection and alerting | MUST |
| SLA-004 | SLA history API | SHOULD |
| SLA-005 | Penalty calculation (for future billing) | MAY |

**SLA Definition in Manifest**:
```json
{
  "sla": {
    "availability": "99.5%",
    "max_latency_p95_ms": 5000,
    "max_error_rate": "1%",
    "support_hours": "24/7"
  }
}
```

---

### 4.4 Audit Logging (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| AUDIT-001 | Log all billable events | MUST |
| AUDIT-002 | Tamper-evident log format | SHOULD |
| AUDIT-003 | Query logs by task, agent, time | MUST |
| AUDIT-004 | Retention policy (configurable) | SHOULD |
| AUDIT-005 | Export for compliance | SHOULD |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Payment processing | Stripe integration in v2.0 | v2.0 Web App |
| Credit system | Part of Marketplace | v2.0 |
| Real-time billing alerts | Post-MVP | v2.1+ |

---

## 6. Technical Considerations

### 6.1 New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| None required | — | Uses `MeteringStore` and `SnapshotStore` interfaces from v1.1.0 (SD-9) |

### 6.2 Code Structure

```
src/asap/
├── economics/
│   ├── __init__.py
│   ├── metering.py       # Usage tracking logic (uses MeteringStore from state/)
│   ├── delegation.py     # Delegation tokens
│   ├── sla.py            # SLA framework (uses health endpoint from v1.1)
│   └── audit.py          # Audit logging
└── ...
```

### 6.3 Storage

**Foundation**: v1.1.0 (SD-9, ADR-13) defined the `MeteringStore` Protocol and SQLite reference implementation. v1.3 builds on this:

- **Metering**: Uses `MeteringStore` interface (defined in v1.1.0) with SQLite backend for dev, PostgreSQL for production
- **Audit**: Append-only log with hash chain for integrity, using `SnapshotStore`-derived `AuditStore` interface
- **SLA monitoring**: Leverages health endpoint (`/.well-known/asap/health`) from v1.1.0 (SD-10, ADR-14)

> **Note**: Storage interfaces were intentionally defined in v1.1.0 to avoid duplicating storage plumbing in v1.3. This sprint focuses on **economics logic**, not storage infrastructure.

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Metering accuracy | <1% drift |
| Delegation overhead | <10ms |
| SLA tracking | 100% of agents |
| Audit completeness | 100% billable events |

---

## 8. Prerequisites from v1.1.0

v1.3 depends on interfaces and infrastructure from v1.1.0:

| v1.1 Deliverable | v1.3 Usage | Reference |
|-------------------|------------|-----------|
| `MeteringStore` Protocol | Usage metering storage backend | SD-9, ADR-13 |
| `SnapshotStore` + SQLite impl | Base for AuditStore pattern | SD-9, ADR-13 |
| Health endpoint (`/.well-known/asap/health`) | SLA uptime monitoring | SD-10, ADR-14 |
| `ttl_seconds` in Manifest | SLA availability measurement | SD-10, ADR-14 |

---

## 9. Related Documents

- **Tasks**: [tasks-v1.3.0-roadmap.md](../../dev-planning/tasks/v1.3.0/tasks-v1.3.0-roadmap.md)
- **Roadmap**: [roadmap-to-marketplace.md](../roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../vision-agent-marketplace.md)
- **State Management Decision**: [ADR-13](../ADR.md#question-13-state-management-strategy-for-marketplace)
- **Liveness Decision**: [ADR-14](../ADR.md#question-14-agent-liveness--health-protocol)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-06 | 1.0.0 | Initial PRD |
| 2026-02-07 | 1.1.0 | Updated storage section to reference v1.1 interfaces (SD-9), added prerequisites section |
