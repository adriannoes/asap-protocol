# PRD: ASAP Protocol v2.3.0 — Scale & Registry

> **Product Requirements Document**
>
> **Version**: 2.3.0
> **Status**: VISION DRAFT
> **Created**: 2026-03-13
> **Last Updated**: 2026-03-20
> **Origin**: Items deferred from [prd-v2.2-scale.md](./prd-v2.2-scale.md) per strategic review (2026-03)

---

## 1. Executive Summary

### 1.1 Purpose

v2.3.0 addresses marketplace scale. These items were originally scoped for v2.2 but deferred because their triggers had not been met. With protocol hardening complete in v2.2, the foundation is stronger for scaling the registry infrastructure.

This release delivers:
- **Registry API Backend**: PostgreSQL-backed search, CRUD, and trust scoring
- **Auto-Registration**: Self-service registration without PR (with compliance gating)
- **TypeScript Client SDK**: Official npm package with AI framework adapters
- **Intent-Based Directory Search**: Natural-language queries across the registry
- **Delegated/Autonomous Mode Formalization**: Explicit mode support in manifests and registration
- **Runtime Capability Escalation**: Request additional capabilities without re-registration
- **Capability-Aware Introspection**: RFC 7662 introspection returning grant info
- **Orchestration Primitives**: Protocol-level coordinator pattern for multi-agent workflows
- **Privacy Considerations**: Formal spec section on data retention and behavioral signals
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
| Search performance | Full-text + intent-based results < 200ms p95 | P1 |
| Registration friction | Self-service without PR for compliant agents | P1 |
| TypeScript adoption | 500+ weekly npm downloads within 3 months | P1 |
| Intent-based discovery | 100+ daily intent queries | P1 |
| Capability escalation | Runtime capability request flow operational | P2 |
| Orchestration support | Coordinator pattern with streaming (v2.2) support | P2 |
| Intelligence filtering | Ability to filter by DeepEval quality scores | P3 (conditional) |

---

## 3. User Stories

### Agent Developer (Provider)
> As an **agent developer**, I want to **register my agent via API with my ASAP OAuth token** so that **I don't need to wait for a PR review to be listed**.

### Registry Consumer (Semantic Search)
> As a **developer**, I want to **search agents by capability using natural language** (e.g., "find me agents that do PDF extraction") so that **I discover relevant agents faster than scanning 500+ entries**.

### TypeScript Developer
> As a **TypeScript developer**, I want to **use an official ASAP SDK with Vercel AI SDK adapters** so that **I can integrate ASAP agents into my Next.js application without writing protocol code**.

### Agent Developer (Capability Escalation)
> As an **agent developer**, I want to **request additional capabilities at runtime without re-registering** so that **my agent can adapt to new tasks as they arise**.

### Orchestrator Agent
> As an **orchestrator agent**, I want to **discover and coordinate multiple agents using protocol-level primitives** so that **multi-agent workflows are reliable and observable without ad-hoc coordination logic**.

### Platform Operator (Privacy)
> As a **platform operator**, I want to **have formal privacy guidelines for agent activity data** so that **I can comply with data protection requirements**.

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

### 4.4 TypeScript Client SDK (P1)

Official npm package for ASAP Protocol with AI framework adapters.

| ID | Requirement | Priority |
|----|-------------|----------|
| TS-001 | `@asap-protocol/client` npm package — manages host/agent keys, signs JWTs, handles registration | MUST |
| TS-002 | Discovery: `listProviders()`, `searchProviders(intent)`, `discoverProvider(url)` | MUST |
| TS-003 | Capabilities: `listCapabilities()`, `describeCapability(name)`, `executeCapability(name, args)` | MUST |
| TS-004 | Connection: `connectAgent(provider, capabilities, mode)`, `disconnectAgent(agentId)` | MUST |
| TS-005 | Lifecycle: `reactivateAgent(agentId)`, `agentStatus(agentId)`, `requestCapability(agentId, caps)` | MUST |
| TS-006 | Vercel AI SDK adapter — ASAP capabilities as Vercel AI tools | SHOULD |
| TS-007 | OpenAI SDK adapter — ASAP capabilities as function calls | SHOULD |
| TS-008 | Anthropic SDK adapter — ASAP capabilities as tool use | SHOULD |
| TS-009 | Pluggable storage interface for key persistence (memory, file, keychain) | SHOULD |

---

### 4.5 Intent-Based Directory Search (P1)

Natural-language search across the registry, beyond categories and keywords.

| ID | Requirement | Priority |
|----|-------------|----------|
| INTENT-001 | `GET /registry/search?intent=<natural-language>&limit=N` — NL search endpoint | MUST |
| INTENT-002 | BM25 full-text search as baseline | MUST |
| INTENT-003 | Optional embedding-based semantic search (when available) | SHOULD |
| INTENT-004 | Results return standard discovery documents (name, description, issuer, endpoints) | MUST |
| INTENT-005 | Integration with `search_providers` client tool | MUST |

---

### 4.6 Delegated/Autonomous Mode Formalization (P2)

Explicit mode support in manifests and agent registration.

| ID | Requirement | Priority |
|----|-------------|----------|
| MODE-001 | `supported_modes` field in manifest: `["delegated", "autonomous"]` | MUST |
| MODE-002 | Mode validation on registration: reject unsupported modes | MUST |
| MODE-003 | Autonomous agent claiming when host becomes linked to a user | SHOULD |
| MODE-004 | Mode-specific default capabilities per host | SHOULD |

---

### 4.7 Runtime Capability Escalation (P2)

Allow agents to request additional capabilities without re-registration.

| ID | Requirement | Priority |
|----|-------------|----------|
| ESC-001 | `POST /asap/agent/request-capability` — request additional capabilities for existing agent | MUST |
| ESC-002 | Triggers approval flow if capability requires consent | MUST |
| ESC-003 | Agent remains `active` while individual grants move from `pending` to `active`/`denied` | MUST |
| ESC-004 | `request_capability` client tool in Python and TypeScript SDKs | MUST |

---

### 4.8 Capability-Aware Introspection (P2)

Extend token introspection for resource servers that validate agent JWTs.

| ID | Requirement | Priority |
|----|-------------|----------|
| INTRO-001 | `POST /asap/agent/introspect` — accepts agent JWT, returns active/inactive + compact grants | MUST |
| INTRO-002 | Response includes `agent_id`, `host_id`, `user_id`, `agent_capability_grants`, `mode` | MUST |
| INTRO-003 | Compact grants (capability + status only) — no input/output schemas | MUST |
| INTRO-004 | Endpoint protected with server-to-server auth (shared secret, mTLS, or IP restriction) | SHOULD |

---

### 4.9 WWW-Authenticate ASAP Challenge (P3)

Resource servers redirect unknown agents to ASAP discovery.

| ID | Requirement | Priority |
|----|-------------|----------|
| CHAL-001 | `WWW-Authenticate: ASAP discovery="https://example.com/.well-known/asap/manifest.json"` on 401 | SHOULD |
| CHAL-002 | Client recognizes `ASAP` scheme and initiates discovery/registration | SHOULD |
| CHAL-003 | Return `403` with `capability_not_granted` when JWT present but capability missing | SHOULD |

---

### 4.10 Privacy Considerations (P3)

Formal privacy section in the ASAP specification.

| ID | Requirement | Priority |
|----|-------------|----------|
| PRIV-001 | Document host key correlation risk (same keypair across servers enables tracking) | SHOULD |
| PRIV-002 | Data retention policy guidance for agent activity logs | SHOULD |
| PRIV-003 | Capability requests as behavioral signals — treat with same data protection as grants | SHOULD |
| PRIV-004 | Guidance on `reason` field sensitivity (may contain PII) | SHOULD |

---

### 4.11 DeepEval Intelligence Layer (P3 — Conditional)

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
| OpenAPI adapter | Requires stable capability model from v2.2–v2.3 | v2.4 |
| MCP Auth Bridge | Requires stable identity model | v2.4 |
| Formal ASAP Specification Document | Requires all protocol features stable | v2.4 |
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
| TypeScript SDK weekly downloads | 500+ on npm |
| Intent-based searches | 100+ daily queries |
| Runtime capability escalation | 10+ agents using escalation flow |
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
- **Next Version**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-13 | 0.1.0 | Vision DRAFT — marketplace items deferred from v2.2 per strategic review. Added Orchestration Primitives (new). |
| 2026-03-20 | 0.2.0 | **Expanded scope**: Added §4.4 TypeScript SDK, §4.5 Intent-Based Search, §4.6 Delegated/Autonomous Modes, §4.7 Capability Escalation, §4.8 Capability-Aware Introspection, §4.9 ASAP Challenge, §4.10 Privacy Considerations. Updated goals, user stories, non-goals, success metrics. |
