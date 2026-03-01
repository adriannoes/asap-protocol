# PRD: ASAP Protocol v2.2.0 — Scale & Registry

> **Product Requirements Document**
>
> **Version**: 2.2.0
> **Status**: DRAFT
> **Created**: 2026-02-25
> **Last Updated**: 2026-02-25

---

## 1. Executive Summary

### 1.1 Purpose

v2.2.0 addresses scale. With the Consumer SDK (v2.1) enabling demand-side growth, the Lite Registry will face increasing pressure on:
- **Volume**: 500+ agents make client-side filtering inadequate
- **Quality**: Intelligence metadata (DeepEval) becomes relevant when consumers compare agents
- **Operational reliability**: Enterprise customers need audit trails and compliance records

This release delivers:
- **Registry API Backend**: PostgreSQL-backed search, CRUD, and trust scoring
- **Auto-Registration**: Self-service registration without PR (with compliance gating)
- **Audit Logging**: Tamper-evident, append-only logs for compliance
- **DeepEval Intelligence Layer** *(optional gate)*: If marketplace user demand for quality filtering materializes

> [!NOTE]
> **Triggers required before starting this PRD**: (1) Lite Registry exceeds **500 real agents** OR (2) IssueOps registration becomes a bottleneck for adoption. Check `registry.json` count before committing to Registry API Backend scope.

### 1.2 Strategic Context

v2.2 is the point where the ASAP Protocol begins separating into its **Open Core + SaaS** architecture (ADR per `vision-agent-marketplace.md §5.5`):

| Component | v2.2 Status |
|-----------|------------|
| SDK, Web App frontend, Lite Registry | Public (stays in repo) |
| Registry API Backend | **Moves to private infra** (runs on our servers) |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Search performance | Full-text results < 200ms p95 | P1 |
| Registration friction | Self-service without PR for compliant agents | P1 |
| Audit compliance | All write operations logged in tamper-evident chain | P2 |
| Intelligence filtering | Ability to filter by DeepEval quality scores (SHOULD) | P3 |

---

## 3. User Stories

### Agent Developer (Provider)
> As an **agent developer**, I want to **register my agent via API with my ASAP OAuth token** so that **I don't need to wait for a PR review to be listed**.

### Registry Consumer (Semantic Search)
> As a **developer**, I want to **search agents by capability using natural language** (e.g., "find me agents that do PDF extraction") so that **I discover relevant agents faster than scanning 500+ entries**.

### Enterprise Admin
> As an **enterprise admin**, I want to **retrieve a tamper-evident audit log of all agent interactions** so that **I can satisfy compliance requirements**.

---

## 4. Functional Requirements

### 4.1 Registry API Backend (P1)

Migrates from static `registry.json` to a PostgreSQL-backed service. Lite Registry (`registry.json`) is preserved as a read-only public mirror for backward compatibility.

| ID | Requirement | Priority |
|----|-------------|----------|
| REG-API-001 | `POST /registry/agents` — authenticated self-registration (ASAP OAuth2 token) | MUST |
| REG-API-002 | `GET /registry/agents` — paginated list with filter support (skill, category, trust level) | MUST |
| REG-API-003 | `GET /registry/agents/{urn}` — agent detail by URN | MUST |
| REG-API-004 | `PUT /registry/agents/{urn}` — update metadata (authenticated, own agent only) | MUST |
| REG-API-005 | `DELETE /registry/agents/{urn}` — revoke and remove (authenticated) | MUST |
| REG-API-006 | Full-text search (`q=` param) across name, description, skills | MUST |
| REG-API-007 | Trust score display (reputation floating 0.0–5.0, computed from metrics) | SHOULD |
| REG-API-008 | Bootstrap from Lite Registry — import existing `registry.json` on first deploy | MUST |
| REG-API-009 | Generate and publish updated `registry.json` mirror for backward compatibility | MUST |

**Schema (PostgreSQL)**:
```sql
agents (urn, name, description, category, tags, skills, trust_level, trust_score, created_at, updated_at)
manifests (urn, payload_json, signature, public_key, created_at)
trust_scores (urn, success_rate, response_time_ms, sla_compliance, tenure_days, computed_at)
```

---

### 4.2 Auto-Registration (P1)

Replaces IssueOps for compliant agents (agents that pass the ASAP Compliance Harness).

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTO-001 | Self-registration endpoint: agent submits manifest URL + ASAP auth token | MUST |
| AUTO-002 | Compliance gating: agent must pass automated schema + health validation before listing | MUST |
| AUTO-003 | Rate limiting: max 5 registration attempts per token per hour | MUST |
| AUTO-004 | IssueOps remains available as human-review path for edge cases | SHOULD |
| AUTO-005 | Anti-spam: trust level starts at `self-signed`, manual review required for `verified` | MUST |

---

### 4.3 Audit Logging (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| AUD-001 | Append-only, tamper-evident audit log (hash chain / Merkle style) | MUST |
| AUD-002 | Log all write operations: registrations, updates, deletions, revocations | MUST |
| AUD-003 | `GET /audit?urn=&start=&end=` — query audit log by agent URN and time range | SHOULD |
| AUD-004 | Export audit log as JSON or CSV | COULD |

---

### 4.4 DeepEval Intelligence Layer (P3 — Conditional)

> [!IMPORTANT]
> Only implement if marketplace users actively request quality filtering (e.g., "show me agents with low hallucination scores"). Do not implement speculatively. Trigger: 3+ user requests for quality filtering OR Verified Badge applicants request standardized evaluation.

| ID | Requirement | Priority |
|----|-------------|----------|
| EVAL-001 | Optional dependency: `asap-protocol[evals]` installs `deepeval>=0.21` | COULD |
| EVAL-002 | Evaluation harness: hallucination, bias, toxicity, G-Eval reasoning | COULD |
| EVAL-003 | Evaluation scores exposed in Registry API as optional metadata | COULD |
| EVAL-004 | Filter agents by min evaluation score in Registry API | COULD |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Economy Settlement / Billing | No live transactions yet | v3.0 |
| Node.js / Go SDKs | Demand-driven | TBD |
| Federated Registry | Centralised approach still validates | v3.x+ |
| Mobile App | Web-first strategy | TBD |

---

## 6. Technical Considerations

### 6.1 Infrastructure

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Database | PostgreSQL (asyncpg) | ACID, full-text (`tsvector`), proven at scale |
| ORM/Migrations | SQLAlchemy async + Alembic | Type-safe, migration tooling |
| Hosting | Railway or Fly.io | Low ops overhead, scale-on-demand |
| Auth | ASAP OAuth2 (existing) | Dogfooding |

### 6.2 Open Core Boundary

The Registry API Backend **leaves the public repo** and becomes private infrastructure (per `vision-agent-marketplace.md §5.5`). The public repo retains the SDK and Web App frontend. The `registry.json` mirror is published via GitHub Pages for backward compatibility.

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Real agents (non-seed) in Registry | 500+ |
| Auto-registration adoption | > 70% of new registrations via API (vs IssueOps) |
| Search p95 latency | < 200ms |
| Audit log coverage | 100% of write events logged |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| **v2.1.0 Tech Debt & Security Cleared** | [tasks-v2.2.0-tech-debt.md](../../tasks/v2.2.0/tasks-v2.2.0-tech-debt.md) must be done first! |
| Consumer SDK live and adopted | v2.1 |
| 500+ real agents in Lite Registry | Growth trigger — verify before starting |
| ASAP OAuth2 infrastructure working | v1.1+ |

---

## 9. Related Documents

- **Deferred Backlog (original scope)**: [deferred-backlog.md](../strategy/deferred-backlog.md) §1, §2, §3
- **Previous Version**: [prd-v2.1-ecosystem.md](./prd-v2.1-ecosystem.md)
- **Next Version**: [prd-v3.0-economy.md](./prd-v3.0-economy.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-25 | 1.0.0 | Initial DRAFT — consolidates deferred-backlog §1, §2, §3 into structured PRD |
