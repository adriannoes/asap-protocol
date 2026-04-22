# PRD: ASAP Protocol v2.3.0 — Adoption Multiplier

> **Product Requirements Document**
>
> **Version**: 2.3.0
> **Status**: DRAFT (rescoped 2026-04-17)
> **Created**: 2026-03-13
> **Last Updated**: 2026-04-17
> **Origin**: Items deferred from [prd-v2.2-scale.md](./prd-v2.2-scale.md) per strategic review (2026-03), then **rescoped** in 2026-04 after v2.2.0 audit.
> **Predecessor**: [prd-v2.2.1-patch.md](./prd-v2.2.1-patch.md) (carry-over patch)
> **Successor**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md)

---

## 1. Executive Summary

### 1.1 Purpose

v2.3.0 has been **rescoped** to attack the missing v2.3 trigger directly. The original v2.3 scope assumed 500+ real agents in the registry; reality at 2026-04-17 is **120 agents**. Building a PostgreSQL Registry API Backend before adoption pulls is over-engineering and contradicts the project's "Lean/Defer" pattern (v1.2 deferred Registry API, v2.0 deferred PostgreSQL, v2.2 deferred marketplace).

Instead, v2.3 ships the **Adoption Multiplier**: three features that *generate* the agent volume the original v2.3 was waiting on.

This release delivers:

- **OpenAPI Adapter** *(pulled forward from v2.4 §4.1)*: zero-code onboarding — any existing OpenAPI spec becomes ASAP capabilities.
- **TypeScript Client SDK**: official npm package with Vercel AI SDK / OpenAI / Anthropic adapters.
- **Auto-Registration**: self-service registration without PR, gated by Compliance Harness v2 (from v2.2).
- **Runtime Capability Escalation** *(supporting feature)*: agents request additional capabilities without re-registering — needed for evolving OpenAPI-derived agents.
- **WWW-Authenticate ASAP Challenge** *(supporting feature)*: resource servers redirect unknown agents to ASAP discovery, enabling silent uplift of existing APIs.

> [!NOTE]
> **Deferred from v2.3 (will return only when triggers materialize)**:
> - Registry API Backend (PostgreSQL) — gated by 500+ agents OR IssueOps becoming the bottleneck
> - Intent-Based Directory Search — gated by Registry API Backend
> - Orchestration Primitives — gated by demand for multi-agent workflows
> - Delegated/Autonomous Mode formalization — gated by capability escalation usage data
> - Capability-Aware Introspection — gated by resource-server demand
> - Privacy Considerations spec — moved to v2.4 specification work
> - DeepEval Intelligence Layer — gated by 3+ user requests for quality filtering

### 1.2 Strategic Context

v2.3 is the **adoption flywheel**. Each of the three core features removes a specific friction:

| Friction | Multiplier | Source |
|----------|-----------|--------|
| "I have an API, not an agent" | OpenAPI Adapter (zero-code) | New, pulled from v2.4 |
| "I write TypeScript, not Python" | TypeScript SDK | Original v2.3 §4.4 |
| "Waiting for PR review to register" | Auto-Registration | Original v2.3 §4.2 |

| Layer | v2.3 Investment |
|-------|----------------|
| Adapters / Integrations | **Primary focus** — OpenAPI |
| Client SDKs | **Primary focus** — TypeScript |
| Registry | **Lean** — Auto-Registration only (no PostgreSQL backend) |
| Identity & Auth | Capability escalation + ASAP Challenge |
| Marketplace backend | Deferred until trigger met |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Zero-code agent onboarding | 20+ agents onboarded via OpenAPI adapter within 90 days | P0 |
| TypeScript adoption | 500+ weekly npm downloads of `@asap-protocol/client` within 3 months | P0 |
| Registration friction removed | > 70% of new registrations via Auto-Registration (vs IssueOps) | P0 |
| Registry growth | 500+ real agents (the original v2.3 trigger, now an outcome metric) | P1 |
| Capability escalation | Runtime capability request flow operational | P1 |
| Silent uplift via challenge | At least one reference resource server using `WWW-Authenticate: ASAP` | P2 |

---

## 3. User Stories

### API Provider (OpenAPI)
> As an **API provider with an OpenAPI spec**, I want to **auto-derive ASAP capabilities from my spec** so that **agents can discover and use my API without me writing protocol code**.

### TypeScript Developer
> As a **TypeScript developer**, I want to **use an official ASAP SDK with Vercel AI SDK adapters** so that **I can integrate ASAP agents into my Next.js application without writing protocol code**.

### Agent Developer (Provider)
> As an **agent developer**, I want to **register my agent via API with my ASAP OAuth token** so that **I don't need to wait for a PR review to be listed**.

### Agent Developer (Capability Escalation)
> As an **agent developer**, I want to **request additional capabilities at runtime without re-registering** so that **my agent can adapt to new tasks as they arise**.

### Resource Server Operator (ASAP Challenge)
> As a **resource server operator**, I want to **emit `WWW-Authenticate: ASAP` on 401** so that **unknown agents are nudged into ASAP discovery and registration without me hand-rolling integration docs**.

---

## 4. Functional Requirements

### 4.1 OpenAPI Adapter (P0) — pulled forward from v2.4

Auto-derive ASAP capabilities from existing OpenAPI specs. Each OpenAPI operation becomes a capability.

| ID | Requirement | Priority |
|----|-------------|----------|
| OA-001 | `create_from_openapi(spec)` — generates capabilities, execution handler, and provider config from OpenAPI spec | MUST |
| OA-002 | OpenAPI `operationId` → capability `name` mapping | MUST |
| OA-003 | OpenAPI `description`/`summary` → capability `description` | MUST |
| OA-004 | OpenAPI parameters + request body → capability `input` (JSON Schema) | MUST |
| OA-005 | OpenAPI 200/201 response body → capability `output` (JSON Schema) | MUST |
| OA-006 | Execution handler maps arguments back to path params, query params, headers, request body | MUST |
| OA-007 | `default_capabilities` filter: by HTTP method (`"GET"`, `["GET", "HEAD"]`), all, or callback | MUST |
| OA-008 | `approval_strength` per capability or per HTTP method (`GET` → `session`, `POST` → `webauthn`) | SHOULD |
| OA-009 | `resolve_headers` callback for upstream auth (e.g., inject `Authorization: Bearer` for user) | MUST |
| OA-010 | Auto-detect response types: `202` → async, `text/event-stream` → streaming, `application/json` → sync | SHOULD |
| OA-011 | Python package: `asap.adapters.openapi` | MUST |
| OA-012 | TypeScript package: `@asap-protocol/openapi` | SHOULD (deferred to v2.4 if TS SDK ships first without it) |

**Usage Example (Python)**:
```python
from asap.adapters.openapi import create_from_openapi

config = create_from_openapi(
    spec_url="https://api.example.com/openapi.json",
    default_capabilities=["GET", "HEAD"],
    approval_strength={"POST": "webauthn", "DELETE": "webauthn"},
    resolve_headers=lambda session: {"Authorization": f"Bearer {get_token(session.user_id)}"},
)
```

---

### 4.2 TypeScript Client SDK (P0)

Official npm package for ASAP Protocol with AI framework adapters.

| ID | Requirement | Priority |
|----|-------------|----------|
| TS-001 | `@asap-protocol/client` npm package — manages host/agent keys, signs JWTs, handles registration | MUST |
| TS-002 | Discovery: `listProviders()`, `searchProviders(intent)`, `discoverProvider(url)` | MUST |
| TS-003 | Capabilities: `listCapabilities()`, `describeCapability(name)`, `executeCapability(name, args)` | MUST |
| TS-004 | Connection: `connectAgent(provider, capabilities, mode)`, `disconnectAgent(agentId)` | MUST |
| TS-005 | Lifecycle: `reactivateAgent(agentId)`, `agentStatus(agentId)`, `requestCapability(agentId, caps)` | MUST |
| TS-006 | Vercel AI SDK adapter — ASAP capabilities as Vercel AI tools | MUST |
| TS-007 | OpenAI SDK adapter — ASAP capabilities as function calls | SHOULD |
| TS-008 | Anthropic SDK adapter — ASAP capabilities as tool use | SHOULD |
| TS-009 | Pluggable storage interface for key persistence (memory, file, browser localStorage, keychain) | SHOULD |
| TS-010 | Type-safe envelopes: `Envelope<TaskRequest>`, `Envelope<TaskStream>`, etc. | MUST |
| TS-011 | Streaming consumer: `client.stream(envelope)` returns `AsyncIterable<Envelope<TaskStream>>` | MUST |

---

### 4.3 Auto-Registration (P0)

Replaces IssueOps for compliant agents. **Lite Registry remains** as the storage layer — no PostgreSQL backend in v2.3.

| ID | Requirement | Priority |
|----|-------------|----------|
| AUTO-001 | Self-registration endpoint: agent submits manifest URL + ASAP auth token | MUST |
| AUTO-002 | Compliance gating: agent must pass Compliance Harness v2 (from v2.2) before listing | MUST |
| AUTO-003 | Rate limiting: max 5 registration attempts per token per hour | MUST |
| AUTO-004 | IssueOps remains available as human-review path for edge cases | SHOULD |
| AUTO-005 | Anti-spam: trust level starts at `self-signed`, manual review required for `verified` | MUST |
| AUTO-006 | Auto-Registration writes to current `registry.json` mirror via Git PR (bot-driven) until Registry API Backend exists | MUST |
| AUTO-007 | Registration receipt with `agent_id`, `urn`, and Compliance Harness v2 score | MUST |

---

### 4.4 Runtime Capability Escalation (P1) — supporting feature

Allow agents to request additional capabilities without re-registration. Required so OpenAPI-derived agents can grow over time without re-onboarding.

| ID | Requirement | Priority |
|----|-------------|----------|
| ESC-001 | `POST /asap/agent/request-capability` — request additional capabilities for existing agent | MUST |
| ESC-002 | Triggers approval flow if capability requires consent | MUST |
| ESC-003 | Agent remains `active` while individual grants move from `pending` to `active`/`denied` | MUST |
| ESC-004 | `request_capability` client tool in Python and TypeScript SDKs | MUST |

---

### 4.5 WWW-Authenticate ASAP Challenge (P2)

Resource servers redirect unknown agents to ASAP discovery — enables silent uplift of existing APIs onto ASAP.

| ID | Requirement | Priority |
|----|-------------|----------|
| CHAL-001 | `WWW-Authenticate: ASAP discovery="https://example.com/.well-known/asap/manifest.json"` on 401 | SHOULD |
| CHAL-002 | Client recognizes `ASAP` scheme and initiates discovery/registration | SHOULD |
| CHAL-003 | Return `403` with `capability_not_granted` when JWT present but capability missing | SHOULD |
| CHAL-004 | Reference implementation: middleware in `asap.adapters.openapi` for auto-emitted challenges | SHOULD |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| **Registry API Backend (PostgreSQL)** | Trigger not met (120/500 agents); Auto-Registration on Lite Registry suffices | Returns when 500+ agents OR IssueOps bottleneck materialize |
| **Intent-Based Directory Search** | Depends on Registry API Backend | Same trigger as Registry API Backend |
| **Orchestration Primitives** | Demand-driven; v2.2 streaming + batch unblock workarounds | Returns when 10+ users request multi-agent flows |
| **Delegated/Autonomous Mode formalization** | Optimization on top of identity (already implicit via `mode` field on `AgentSession`) | Driven by usage data from capability escalation |
| **Capability-Aware Introspection (RFC 7662)** | Resource-server feature; no current asks | Returns with v2.4 spec work |
| **Privacy Considerations spec** | Document deliverable, fits better with v2.4 formal spec | v2.4 |
| **DeepEval Intelligence Layer** | Trigger not met (no requests) | Conditional |
| **MCP Auth Bridge** | v2.4 scope | v2.4 |
| **Formal ASAP Specification Document** | v2.4 scope | v2.4 |
| **Economy / Settlement / Billing** | No live transactions yet | v3.0 |
| **Federated Registry** | Centralised approach still validates | v3.x+ |

---

## 6. Technical Considerations

### 6.1 OpenAPI Adapter Architecture

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Spec parsing | `openapi-pydantic` (Python), `openapi-types` (TS) | Type-safe OpenAPI 3.x parsing |
| HTTP proxying | `httpx` (Python), `fetch` (TS) | Existing dependencies (ADR-008) |
| Schema derivation | JSON Schema subset from OpenAPI | Direct mapping, no conversion needed |
| Discovery integration | OpenAPI adapter emits `/.well-known/asap/manifest.json` automatically | Consistent with v1.2 discovery |

### 6.2 TypeScript SDK Architecture

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Build | `tsup` + `tshy` (dual ESM/CJS) | Standard for modern npm packages |
| Crypto | Web Crypto API (Ed25519) with `@noble/ed25519` fallback | Browser + Node compatibility |
| Transport | `fetch` + `EventSource` for SSE | Native runtime support |
| Adapters location | `@asap-protocol/client/adapters/{vercel-ai,openai,anthropic}` | Tree-shakeable |

### 6.3 Auto-Registration on Lite Registry

Auto-Registration writes to `registry.json` via a **bot-authored PR** (not direct write to disk). This avoids needing a Postgres backend while still gating via Compliance Harness v2 + manual review for `verified` trust level.

```
Agent → POST /registry/agents (auth: ASAP OAuth2)
        ↓
   Compliance Harness v2 (synchronous check)
        ↓
   PR opened by `asap-bot` against registry.json
        ↓
   Auto-merge if Harness passed AND trust_level == "self-signed"
        ↓
   GitHub Pages serves updated registry.json mirror
```

When the 500-agent trigger fires, this flow is replaced by the (deferred) Registry API Backend — but the public contract stays identical.

### 6.4 v2.2 Dependencies

OpenAPI Adapter and TypeScript SDK both depend on v2.2 protocol features:

- **Streaming SSE** for OpenAPI `text/event-stream` responses and TypeScript streaming consumer
- **Capability-Based Authorization** with constraints (`max`, `min`, `in`, `not_in`) for OpenAPI parameter limits
- **Per-Runtime-Agent Identity** for TypeScript host/agent JWT generation
- **Error Taxonomy + Recovery Hints** for client retry semantics
- **ASAP-Version Negotiation** for SDK ↔ server version handshake

### 6.5 Carry-over: "extract when touched" refactor of transport/ monoliths

Inherited as a conscious carry-over from the v2.2.1 tech-debt sweep (2026-04-22):

- [`src/asap/transport/server.py`](../../../src/asap/transport/server.py) (~2160 LoC) and
  [`src/asap/transport/client.py`](../../../src/asap/transport/client.py) (~1750 LoC) are
  cognitively heavy but **coherent** around their primary types (`ASAPRequestHandler` +
  `create_app`; `ASAPClient`). A speculative split would force an internal-API reshuffle
  right before new routes land in v2.3.
- **Rule for v2.3 contributors**: when a sprint task adds a route (Auto-Registration,
  Runtime Capability Escalation) or a client method (TS SDK parity), **extract the new
  surface into a dedicated module from day one** (e.g., `asap.transport.auto_registration`,
  `asap.transport.capability_escalation`). Do not add a new method to `server.py` when a
  new module is the natural home.
- Do **not** ship a standalone "split transport/server.py" PR — the cost was assessed and
  the value realizes only as features accrete.

---

## 7. Success Metrics

| Metric | Target | Time Horizon |
|--------|--------|--------------|
| Agents onboarded via OpenAPI adapter | 20+ | 90 days post-release |
| `@asap-protocol/client` weekly npm downloads | 500+ | 3 months post-release |
| Auto-registration adoption | > 70% of new registrations | 6 months post-release |
| Real agents (non-seed) in Registry | 500+ | Outcome metric — unlocks deferred Registry API Backend |
| Runtime capability escalation flows | 10+ agents using escalation | 6 months post-release |
| WWW-Authenticate ASAP reference deployment | 1+ | 90 days post-release |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.2.0 Protocol Hardening released | ✅ 2026-04-15 |
| v2.2.1 carry-over patch released | [prd-v2.2.1-patch.md](./prd-v2.2.1-patch.md) |
| Capability model stable | ✅ v2.2 |
| Identity model stable | ✅ v2.2 |
| Streaming/SSE operational | ✅ v2.2 |
| Compliance Harness v2 operational | ✅ v2.2 |
| ASAP OAuth2 infrastructure working | ✅ v1.1+ |

---

## 9. Related Documents

- **Origin PRD (deferred scope, superseded)**: [prd-v2.2-scale.md](./prd-v2.2-scale.md)
- **Carry-over Patch**: [prd-v2.2.1-patch.md](./prd-v2.2.1-patch.md)
- **Protocol Hardening (foundation)**: [prd-v2.2-protocol-hardening.md](./prd-v2.2-protocol-hardening.md)
- **Previous Major Release**: [prd-v2.1-ecosystem.md](./prd-v2.1-ecosystem.md)
- **Next Version**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md) (MCP Auth Bridge, Formal Spec, cross-protocol)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-03-13 | 0.1.0 | Vision DRAFT — marketplace items deferred from v2.2 per strategic review. Added Orchestration Primitives (new). |
| 2026-03-20 | 0.2.0 | **Expanded scope**: Added §4.4 TypeScript SDK, §4.5 Intent-Based Search, §4.6 Delegated/Autonomous Modes, §4.7 Capability Escalation, §4.8 Capability-Aware Introspection, §4.9 ASAP Challenge, §4.10 Privacy Considerations. |
| 2026-04-17 | 0.3.0 | **Rescoped to "Adoption Multiplier"** after v2.2.0 audit confirmed 120/500 agents (trigger unmet). Pulled OpenAPI Adapter forward from v2.4 §4.1. Kept TypeScript SDK, Auto-Registration, Capability Escalation, ASAP Challenge. **Deferred** Registry API Backend, Intent-Based Search, Orchestration Primitives, Delegated/Autonomous Mode formalization, Capability-Aware Introspection, Privacy spec, DeepEval — each with explicit return-trigger. |
