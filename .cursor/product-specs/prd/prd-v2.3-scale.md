# PRD: ASAP Protocol v2.3.0 — Scale & Registry

> **Product Requirements Document**
>
> **Version**: 2.3.0
> **Status**: VISION DRAFT
> **Created**: 2026-03-13
> **Last Updated**: 2026-03-13
> **Origin**: Items deferred from [prd-v2.2-scale.md](./prd-v2.2-scale.md) per strategic review (2026-03)

---

## 1. Executive Summary

### 1.1 Purpose

v2.3.0 addresses marketplace scale. These items were originally scoped for v2.2 but deferred because their triggers had not been met. With protocol hardening complete in v2.2, the foundation is stronger for scaling the registry infrastructure.

This release delivers:
- **Registry API Backend**: PostgreSQL-backed search, CRUD, and trust scoring
- **Auto-Registration**: Self-service registration without PR (with compliance gating)
- **Orchestration Primitives**: Protocol-level coordinator pattern for multi-agent workflows
- **DeepEval Intelligence Layer** *(conditional)*: If marketplace user demand for quality filtering materializes

> [!CAUTION]
> **Triggers required before starting this PRD**:
> 1. Lite Registry exceeds **500 real agents** OR IssueOps registration becomes a bottleneck for adoption
> 2. v2.2 Protocol Hardening is released (streaming, versioning, batch, error taxonomy evolution)
> 3. For DeepEval: 3+ user requests for quality filtering OR Verified Badge applicants request standardized evaluation

### 1.2 Strategic Context

v2.3 is the point where the ASAP Protocol begins separating into its **Open Core + SaaS** architecture (per `vision-agent-marketplace.md §5.5`):

| Component | v2.3 Status |
|-----------|------------|
| SDK, Web App frontend, Lite Registry | Public (stays in repo) |
| Registry API Backend | **Moves to private infra** (runs on our servers) |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Search performance | Full-text results < 200ms p95 | P1 |
| Registration friction | Self-service without PR for compliant agents | P1 |
| Orchestration support | Coordinator pattern with streaming (v2.2) support | P1 |
| Intelligence filtering | Ability to filter by DeepEval quality scores | P3 (conditional) |

---

## 3. User Stories

### Agent Developer (Provider)
> As an **agent developer**, I want to **register my agent via API with my ASAP OAuth token** so that **I don't need to wait for a PR review to be listed**.

### Registry Consumer (Semantic Search)
> As a **developer**, I want to **search agents by capability using natural language** (e.g., "find me agents that do PDF extraction") so that **I discover relevant agents faster than scanning 500+ entries**.

### Orchestrator Agent
> As an **orchestrator agent**, I want to **discover and coordinate multiple agents using protocol-level primitives** so that **multi-agent workflows are reliable and observable without ad-hoc coordination logic**.

---

## 4. Functional Requirements

### 4.1 Registry API Backend (P1)

Migrates from static `registry.json` to a PostgreSQL-backed service. Lite Registry is preserved as a read-only public mirror.

Scope preserved from original [prd-v2.2-scale.md](./prd-v2.2-scale.md) §4.1:

| ID | Requirement | Priority |
|----|-------------|----------|
| REG-API-001 | `POST /registry/agents` — authenticated self-registration (ASAP OAuth2 token) | MUST |
| REG-API-002 | `GET /registry/agents` — paginated list with filter support (skill, category, trust level) | MUST |
| REG-API-003 | `GET /registry/agents/{urn}` — agent detail by URN | MUST |
| REG-API-004 | `PUT /registry/agents/{urn}` — update metadata (authenticated, own agent only) | MUST |
| REG-API-005 | `DELETE /registry/agents/{urn}` — revoke and remove (authenticated) | MUST |
| REG-API-006 | Full-text search (`q=` param) across name, description, skills | MUST |
| REG-API-007 | Trust score display (reputation floating 0.0-5.0, computed from metrics) | SHOULD |
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

Scope preserved from original [prd-v2.2-scale.md](./prd-v2.2-scale.md) §4.2:

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTO-001 | Self-registration endpoint: agent submits manifest URL + ASAP auth token | MUST |
| AUTO-002 | Compliance gating: agent must pass Compliance Harness v2 (from v2.2) before listing | MUST |
| AUTO-003 | Rate limiting: max 5 registration attempts per token per hour | MUST |
| AUTO-004 | IssueOps remains available as human-review path for edge cases | SHOULD |
| AUTO-005 | Anti-spam: trust level starts at `self-signed`, manual review required for `verified` | MUST |

---

### 4.3 Orchestration Primitives (P1)

New scope. Enables protocol-level multi-agent coordination.

| ID | Requirement | Priority |
|----|-------------|----------|
| ORCH-001 | `CoordinatorEnvelope` — envelope variant for fan-out task distribution | MUST |
| ORCH-002 | `TaskGroup` model — tracks related tasks across agents with shared correlation_id | MUST |
| ORCH-003 | Aggregation patterns: wait-all, wait-any, first-success | MUST |
| ORCH-004 | Streaming aggregation — coordinator streams partial results from multiple agents (builds on v2.2 SSE) | SHOULD |
| ORCH-005 | Failure propagation — coordinator handles partial failures with configurable strategy | SHOULD |
| ORCH-006 | Orchestration compliance checks in Compliance Harness | SHOULD |

---

### 4.4 DeepEval Intelligence Layer (P3 — Conditional)

Scope preserved from original [prd-v2.2-scale.md](./prd-v2.2-scale.md) §4.4:

> [!IMPORTANT]
> Only implement if marketplace users actively request quality filtering. Trigger: 3+ user requests OR Verified Badge applicants request standardized evaluation.

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
| Payment Processing (Stripe) | Trigger not met (100+ Verified Agents) | v3.0 |
| Node.js / Go SDKs | Demand-driven | TBD |
| Federated Registry | Centralized approach still validates | v3.x+ |
| ASAP Cloud | Requires economy layer | v3.0 |

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

The Registry API Backend **leaves the public repo** and becomes private infrastructure (per `vision-agent-marketplace.md §5.5`). The public repo retains the SDK and Web App frontend.

### 6.3 v2.2 Dependencies

Orchestration Primitives depend on v2.2 features:
- **Streaming** (SSE) for real-time result aggregation
- **Batch Operations** for fan-out task distribution
- **Error Taxonomy Evolution** for failure propagation strategies
- **Version Negotiation** for multi-version agent coordination

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Real agents (non-seed) in Registry | 500+ |
| Auto-registration adoption | > 70% of new registrations via API (vs IssueOps) |
| Search p95 latency | < 200ms |
| Multi-agent workflows | 10+ orchestration flows using ORCH primitives |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.2.0 Protocol Hardening released | This PRD |
| 500+ real agents in Lite Registry | Growth trigger |
| ASAP OAuth2 infrastructure working | v1.1+ |
| Streaming/SSE operational | v2.2 |
| Batch Operations operational | v2.2 |

---

## 9. Related Documents

- **Origin PRD (deferred scope)**: [prd-v2.2-scale.md](./prd-v2.2-scale.md)
- **Protocol Hardening**: [prd-v2.2-protocol-hardening.md](./prd-v2.2-protocol-hardening.md)
- **Previous Version**: [prd-v2.1-ecosystem.md](./prd-v2.1-ecosystem.md)
- **Next Version**: [prd-v3.0-economy.md](./prd-v3.0-economy.md)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-13 | 0.1.0 | Vision DRAFT — marketplace items deferred from v2.2 per strategic review. Added Orchestration Primitives (new). |
