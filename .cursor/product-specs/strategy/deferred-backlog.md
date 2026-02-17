# ASAP Protocol: Deferred Feature Backlog

> **Purpose**: Features intentionally deferred from the v1.x → v2.0 roadmap during the "Lean Marketplace" strategic pivot.
>
> **Context**: [Lean Marketplace Vision](../../.gemini/antigravity/brain/40867da6-efec-4747-94f6-4102748afe30/lean_marketplace_vision.md)
> **Created**: 2026-02-12
> **Supersedes**: Original v1.2 Sprints T3, T4, T6.1; Original v1.3 Sprint E4 (audit tasks)
>
> ⚠️ These are NOT cancelled — they are **deferred** with clear triggers for when to revisit.

---

## 1. Registry API Backend (Originally v1.2, Sprints T3–T4)

**What**: Centralized REST API for agent registration, search, reputation, and discovery integration.

**Why deferred**: The Lite Registry (static `registry.json` on GitHub Pages, SD-11/ADR-15) is sufficient for MVP. A backend API adds infrastructure cost (PostgreSQL, hosting) without proportional value until agent count exceeds what a static file can handle (~1000+ agents).

**Trigger to revisit**: When the Lite Registry reaches **500+ agents** OR when automated registration (not PR-based) becomes a blocker for adoption.

**Proposed milestone**: v2.1

### Original Scope (Preserved)

#### Sprint T3: Registry API Core

| Task | Description | Deliverable |
|------|-------------|-------------|
| 3.1 | Data model (AgentRegistration, RegistrationStatus, RegistryStorage) | `src/asap/registry/models.py` |
| 3.2 | CRUD endpoints (POST/GET/PUT/DELETE with OAuth2 for writes) | `src/asap/registry/api.py` |
| 3.3 | Search API (skill, trust level, capability filtering + pagination) | Query API |
| 3.4 | Bootstrap from Lite Registry (import `registry.json` agents) | Import script |

**Original estimate**: 6–8 days

#### Sprint T4: Registry Features

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Reputation system (score: 0.0–5.0, components: success_rate, response_time, sla_compliance) | `src/asap/registry/reputation.py` |
| 4.2 | Client SDK (register, search, get_reputation + retry + caching) | `src/asap/registry/client.py` |
| 4.3 | Discovery integration (Registry-first, well-known fallback) | `ASAPClient.discover()` update |

**Original estimate**: 4–6 days

### Technical Notes
- PostgreSQL required for concurrent writes and full-text search
- Storage follows `SnapshotStore` Protocol pattern (SD-9)
- The bootstrap task (3.4) remains relevant — when we build the API, seed from Lite Registry

---

## 2. DeepEval Intelligence Layer (Originally v1.2, Sprint T6.1)

**What**: Integration with DeepEval for "Brain" evaluation metrics (hallucination, bias, toxicity, G-Eval reasoning).

**Why deferred**: Intelligence evaluation does NOT impact whether agents can participate in the marketplace. The marketplace needs **protocol compliance** (Shell), not AI quality scoring. DeepEval adds a heavy dependency (`deepeval>=0.21`) requiring LLM API calls (cost), and evaluates agent *intelligence* — a concern for agent *consumers*, not the marketplace infrastructure.

**Trigger to revisit**: When **marketplace users request quality filtering** (e.g., "show me only agents with low hallucination scores").

**Proposed milestone**: v2.2+

### Original Scope (Preserved)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 6.1.1 | Spike: DeepEval async adapter prototype | `prototypes/deepeval_adapter.py` |
| 6.1.2 | Configuration schema (`[tool.asap.evals]`) | `pyproject.toml` |
| 6.1.3 | Add optional dependency (`deepeval>=0.21`) | `pyproject.toml` |
| 6.1.4 | Create adapter | `asap_compliance/deepeval_adapter.py` |
| 6.1.5 | G-Eval integration (reasoning assessment) | Adapter |
| 6.1.6 | Safety metrics (hallucination, bias, toxicity) | Adapter |
| 6.1.7 | Evaluation guide | `docs/guides/evaluating-intelligence.md` |
| 6.1.8 | Documentation (enable, interpret, cost) | Docs |

**Original estimate**: ~2 days (within T6's 4–6 day sprint)

### Technical Notes
- Requires `AsyncConfig(run_async=True)` for async compatibility
- LLM API calls add cost per evaluation
- ADR-10 documents the Hybrid (Shell + Brain) rationale

---

## 3. Audit Logging (Originally v1.3, Sprint E4 tasks 4.1–4.3)

**What**: Append-only, tamper-evident audit logs for all billable events. Query API for audit data.

**Why deferred**: Audit logging is a **compliance** feature needed for enterprise customers and dispute resolution. The MVP marketplace doesn't need formal audit trails — observability metering provides sufficient visibility.

**Trigger to revisit**: When the first **enterprise customer** requests compliance audit trails OR when billing disputes arise.

**Proposed milestone**: v2.1+

### Original Scope (Preserved)

| Task | Description | Deliverable |
|------|-------------|-------------|
| 4.1 | Audit log format (append-only, tamper-evident, hash chain) | `src/asap/economics/audit.py` |
| 4.2 | Log all billable events (task start, complete, usage reports) | Integration |
| 4.3 | Audit query API (by task, agent, time) | REST API |

**Original estimate**: ~2 days (within E4's 4–6 day sprint)

### Technical Notes
- Storage follows `SnapshotStore` Protocol pattern — `AuditStore` interface
- Hash chain integrity for tamper-evidence
- Prerequisite: Usage metering (E1) must exist first

---

## 4. Economy Settlement / Credits (Originally v2.0+)

**What**: Pay-per-use billing, credit system, agent-to-agent payments.

**Why deferred**: Settlement requires a live marketplace with real transactions. Building settlement infrastructure before having paying users is premature optimization.

**Trigger to revisit**: When **Verified badge revenue exceeds $5k/month** AND users request pay-per-use agent services.

**Proposed milestone**: v3.0

### Technical Notes
- Depends on: Usage metering (v1.3), Delegation tokens (v1.3), Stripe integration (v2.0)
- Stripe Connect for marketplace-style payouts
- Complex regulatory implications (money transmission laws)

---

## 5. Payment Processing & Verified Revenue (Originally v2.0)

**What**: Stripe integration for $49/mo subscriptions and payment capability.

**Why deferred**: Focus on "Leanness" and "Trust" first. Payments introduce legal/tax friction (Nexus, VAT) and infrastructure complexity that is unnecessary for the initial directory growth phase.

**Trigger to revisit**: When **Verified Agent count > 100** OR when enterprise partners demand paid support/SLA tiers.

**Proposed milestone**: v3.0

---

## Summary

| Feature | Original Version | Deferred To | Trigger |
|---------|-----------------|-------------|---------|
| Registry API Backend | v1.2 | v2.1 | 500+ agents in Lite Registry |
| DeepEval Intelligence | v1.2 | v2.2+ | User demand for quality filtering |
| Audit Logging | v1.3 | v2.1+ | Enterprise customer or billing disputes |
| Economy Settlement | v2.0+ | v3.0 | Revenue > $5k/mo + user demand |
| Payment Processing | v2.0 | v3.0 | 100+ Verified Agents |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-12 | Initial document — Lean Marketplace pivot |
