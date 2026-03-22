# ASAP Protocol: Roadmap to Marketplace

> **Evolution Path**: v1.0.0 → v2.0.0 ✅ Released → v2.1.0 ✅ Released → v2.2.0 (next)
>
> **Status**: v2.1.1 RELEASED — Planning v2.2.0
> **Horizon**: v2.2.0 Protocol Hardening, v2.3.0 Scale, v2.4.0 Adoption, v3.0.0 Economy
> **Created**: 2026-01-30
> **Updated**: 2026-03-20

---

## Overview

This roadmap defines the evolution from v1.0.0 (stable protocol) to v2.0.0 (Agent Marketplace). Each version builds foundational capabilities required for the marketplace vision.

**Strategic Priority**: Adoption first, monetization later.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    ROADMAP TO AGENT MARKETPLACE                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  v1.0.0          v1.1           v1.2           v1.3           v1.4           v2.0      │
│  ═══════        ═══════        ═══════        ═══════        ═══════        ═══════    │
│    │              │              │              │              │              │        │
│    │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │        │
│    ├─│ Stable   │─┼─│ Identity │─┼─│ Verified │─┼─│ Observe  │─┼─│ Scale    │─┼─→ 🏪   │
│    │ │ Protocol │ │ │ +Discov  │ │ │ Identity │ │ │ +Deleg   │ │ │ +Types   │ │        │
│    │ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────┘ │        │
│    │              │              │              │              │              │        │
│    ▼              ▼              ▼              ▼              ▼              ▼        │
│  Released     Identity       Verified     Observability    Hardening     Marketplace   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Strategic Decisions

Key architectural and business decisions made during planning. Each decision includes rationale and alternatives considered.

### SD-1: Registry Architecture — Centralized First

**Decision**: Start with a centralized registry operated by ASAP, with federation as a future option.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Centralized** | ✅ Selected | Faster to build, easier monetization, quality control |
| Federated | Deferred to v2.x+ | Complex architecture, needed only at scale |
| Fully decentralized | Rejected | Too slow for early adoption, no quality control |

**Why this matters**: Like npm/PyPI, a single official registry simplifies the developer experience. Federation can be added when there's demand from enterprises wanting private registries.

---

### SD-2: Pricing Model — Freemium First

**Decision**: Launch with Free model. Monetization deferred to v3.0.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Freemium** | ✅ Selected | Zero barrier for startups/devs, adoption priority |
| Subscription | Deferred | Friction for early adopters |
| % of transactions | Deferred | Requires payment rails infrastructure |

**Initial tiers**:
- **Free**: List agents, basic features
- **Verified**: $0 (manual review, badge) - High trust bar.

**Why this matters**: Target ICP (AI startups, individual developers) need zero friction. They often build solutions for enterprise clients who value reliable protocols.

---

### SD-3: Real-time Transport — WebSocket for v1.x

**Decision**: WebSocket for v1.x, Message Broker (NATS/Kafka) as optional premium feature in v2.0+.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **WebSocket** | ✅ Selected for v1.x | Sufficient for <50 agents, simpler infrastructure |
| Message Broker | v2.0+ optional | Overkill for startups, adds infrastructure cost |

**Why this matters**: WebSocket handles direct connections well. Brokers solve the N² connection problem but require additional infrastructure most early adopters don't need.

---

### SD-4: Signing Algorithm — Ed25519

**Decision**: Use Ed25519 for manifest signing.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Ed25519** | ✅ Selected | Modern, fast, small signatures, MCP-aligned |
| ECDSA (P-256) | Rejected | Multiple curves = complexity |
| RSA-2048/4096 | Rejected | Slow, large signatures, legacy |

**Why this matters**: Ed25519 produces 64-byte signatures (vs RSA's 256+), is faster to verify, and is the modern standard used by MCP, SSH, and Signal.
**Hardening**: We mandate **JCS (RFC 8785)** for canonicalization and **Strict Verification (RFC 8032)** to prevent malleability attacks.

---

### SD-5: PKI Strategy — 3-Tier Trust Levels

**Decision**: Three trust levels for manifest signing.

| Level | Description | Cost |
|-------|-------------|------|
| **Self-signed** | Any agent can participate | Free |
| **Verified** | ASAP reviews and signs | $49/month |
| **Enterprise** | Org uses own CA | Future |

**Why this matters**: Zero barrier for developers (self-signed accepted), clear upgrade path (Verified for credibility), enterprise flexibility (bring-your-own CA for regulated industries).

---

### SD-6: mTLS — Optional, Never Required

**Decision**: mTLS available in v1.2 as optional feature, never mandatory.

| Option | Considered | Rationale |
|--------|------------|-----------|
| mTLS required | Rejected | High friction, overkill for startups |
| **mTLS optional** | ✅ Selected | Available for enterprise/regulated use cases |
| No mTLS | Rejected | Blocks enterprise adoption |

**Why this matters**: Adoption-first strategy means minimizing friction. Enterprises needing mutual TLS can enable it; others can ignore it.

---

### SD-7: Discovery — Basic Discovery in v1.1

**Decision**: Move well-known URI and DNS-SD discovery to v1.1 (before Registry API Backend in v2.1).

**Rationale**: WebSocket requires agents to find each other. Without basic discovery, real-time communication cannot work across dynamic agents.

---

### SD-8: Documentation Architecture — Separated Docs

**Decision**: Keep documentation (MkDocs) separate from the Web App (Next.js).

| Option | Considered | Rationale |
|--------|------------|-----------|
| Docs inside Web App | Rejected | Mixing concerns, slower iteration on docs vs product |
| **Separated (MkDocs + Web App)** | ✅ Selected | Independent deploy cycles, docs can ship faster |
| Docs in GitHub Wiki | Rejected | Poor DX, no custom styling, limited search |

**Why this matters**: Documentation needs to ship independently of the marketplace. API docs, guides, and examples should be deployable without a full Web App release. MkDocs provides a fast, markdown-first authoring experience while the Web App focuses on interactive marketplace features.

---

### SD-9: State Management — Hybrid Strategy

**Decision**: ASAP defines storage interfaces and provides reference implementations. Agent task state is the agent's responsibility. Marketplace metadata is managed centrally.

| Layer | Data | Owner |
|-------|------|-------|
| **Protocol Interface** | `SnapshotStore`, `MeteringStore`, `SLAStorage` | ASAP SDK (open source) |
| **Reference Impls** | SQLite, Redis adapters | Separate packages |
| **Marketplace Metadata** | Manifests, trust scores, SLA | ASAP centrally (v2.0) |
| **Agent Task State** | Snapshots, artifacts | Agent developer's choice |
| **ASAP Cloud** (future) | Managed storage | Premium feature |

| Option | Considered | Rationale |
|--------|------------|-----------|
| State-as-a-Service | Rejected | Data sovereignty burden, massive infra cost, contradicts adoption-first |
| Communication only | Rejected | v1.3 Economics impossible without storage interfaces, poor DX |
| **Hybrid** | ✅ Selected | Extends existing `SnapshotStore` pattern, no lock-in, enables ASAP Cloud monetization |

**Why this matters**: Without defined storage interfaces, v1.3 (metering, audit logging) and v2.0 (reputation, SLA tracking) become impossible. The hybrid approach keeps ASAP lightweight while enabling the full marketplace vision.

**Reference**: [ADR-13](../decision-records/01-architecture.md)

---

### SD-10: Agent Liveness — Health Protocol in v1.1

**Decision**: Agents SHOULD expose `GET /.well-known/asap/health` with TTL field in manifest.

| Option | Considered | Rationale |
|--------|------------|-----------|
| No health protocol | Rejected | Registry shows stale agents, SLA unverifiable |
| Full health framework | Rejected | Over-engineering for current stage |
| **Simple health endpoint + TTL** | ✅ Selected | Low cost, high value, Kubernetes-aligned |

**Why this matters**: Without liveness, the Registry (v1.2) becomes a graveyard of dead agents. The Reputation System (v2.0) cannot calculate uptime, and SLA monitoring (v1.3) has no measurement mechanism.

**Reference**: [ADR-14](../decision-records/01-architecture.md)

---

### SD-11: Lite Registry — Bridging the Discovery Abyss

**Decision**: Bridge the gap between v1.1 (Identity + Direct Discovery) and v2.1 (Registry API Backend) with a static `registry.json` file hosted on GitHub Pages. Agents are listed via PR.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Static JSON on GitHub Pages** | ✅ Selected | Zero infrastructure, PR-based social proof, machine-readable |
| DNS-based discovery | Rejected | Complex for developers, no browsing/search |
| Do nothing (accept gap) | Rejected | Kills early adoption momentum, network effect is zero |

**Why this matters**: In v1.1, agents have identity (OAuth2) and serve manifests (well-known), but no one can find them unless they already know the URL. The Lite Registry provides immediate discoverability with zero infrastructure cost. The v2.1 Registry API Backend can seed itself from this file when scale demands it.

**Key design**: Schema uses `endpoints` dict (not single `url`) to support HTTP + WebSocket transports introduced in v1.1.

**Reference**: [ADR-15](../decision-records/05-product-strategy.md)

---

### SD-12: Agent Identity — Per-Runtime-Agent Keypairs

**Decision**: Upgrade from service-level identity to per-runtime-agent identity. Each conversation/task/session gets its own Ed25519 keypair under a persistent Host identity.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Per-runtime keypair** | ✅ Selected | Granular audit, isolated revocation, enterprise-grade security |
| Service-level identity only | Rejected | No isolation between agents sharing credentials; insufficient for regulated industries |
| Per-user identity | Rejected | Agents are not users — they need distinct lifecycle and scoping |

**Why this matters**: Two separate conversations in the same application are different agents with different contexts and permissions. Service-level identity collapses all runtime agents into one — no visibility, no scoping, no isolation. Per-agent keypairs give servers the ability to identify, scope, audit, and revoke individual agents.

---

### SD-13: Authorization Model — Capabilities with Constraints

**Decision**: Upgrade from coarse OAuth scopes (`READ/EXECUTE/ADMIN`) to fine-grained capabilities with constraint operators (`min/max/in/not_in`).

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Capability-based with constraints** | ✅ Selected | Precise authorization, self-correcting agents, enterprise compliance |
| OAuth scopes (current) | Keep as compatibility layer | Too coarse for real-world authorization (e.g., "transfer up to $1000 in USD") |
| RBAC (role-based) | Rejected | Roles are too broad; capabilities are more composable |

**Why this matters**: OAuth scopes tell you *what category* of action is allowed. Capabilities tell you *exactly which action* with *exactly what parameters*. Constraint operators enable scoped grants like "transfer up to $1,000 in USD to account X" — a requirement for financial, healthcare, and enterprise use cases.

---

### SD-14: Approval Flows — Device Authorization + CIBA + WebAuthn

**Decision**: Add protocol-level user consent flows for agent registration and capability escalation, with self-authorization prevention.

| Option | Considered | Rationale |
|--------|------------|-----------|
| **RFC 8628 + CIBA + WebAuthn** | ✅ Selected | Standards-based, covers all deployment models, prevents self-approval |
| A2H only | Rejected | A2H is agent-to-human communication, not formal consent/authorization |
| Custom consent UI | Rejected | Non-standard, no interoperability |

**Why this matters**: Agents increasingly control the user's browser (MCP servers, browser tools, desktop copilots). Without biometric/hardware proof of presence, an agent can navigate to the approval URL and approve itself. WebAuthn is the only reliable proof-of-human when the agent controls the browser.

---

## Release Timeline

| Version | Codename | Focus | Key Deliverables |
|---------|----------|-------|------------------|
| **v1.0.0** | Foundation | Stable protocol | ✅ Released |
| **v1.1.0** | Identity | Auth + Discovery + Real-time | OAuth2, WebSocket, Well-known URI, Lite Registry, MessageAck |
| **v1.2.0** | Verified Identity | Signing + Compliance | Ed25519 signing, Compliance Harness, mTLS (opt) |
| **v1.3.0** | Observability | Metering + SLAs + Delegation | ✅ Released — Observability metering, SLA framework, delegation tokens |
| **v1.4.0** | Hardening | Resilience + Scale | Type safety hardening, storage pagination |
| **v2.0.0** | Marketplace | Full launch | ✅ Released (2026-02-25) — Web App, Lite Registry (120+ agents), Verified Badge, IssueOps registration |
| **v2.1.0** | Ecosystem | Demand-side activation | ✅ Released — Consumer SDK, LangChain/CrewAI/MCP integrations, Category/Tags, Agent Revocation, PyPI — See [prd-v2.1-ecosystem.md](../prd/prd-v2.1-ecosystem.md) |
| **v2.2.0** | Protocol Hardening | Identity, auth, and protocol maturity | Per-runtime-agent identity, capability-based authz, approval flows, agent lifecycle, streaming/SSE, error taxonomy, versioning, async, batch, audit logging — See [prd-v2.2-protocol-hardening.md](../prd/prd-v2.2-protocol-hardening.md) |
| **v2.3.0** | Scale | Registry + SDK expansion | Registry API Backend (PostgreSQL), Auto-Registration, TypeScript SDK, Intent-Based Search, Orchestration Primitives, DeepEval (conditional) — See [prd-v2.3-scale.md](../prd/prd-v2.3-scale.md) |
| **v2.4.0** | Adoption | Lower integration barriers | OpenAPI adapter, WWW-Authenticate ASAP challenge, cross-protocol compatibility |
| **v3.0.0** | Economy | Monetization | Stripe, Credits, Economy Settlement, Clearing House, ASAP Cloud — See [prd-v3.0-economy.md](../prd/prd-v3.0-economy.md) |

---

## v1.1.0 "Identity" — Foundation for Trust

**Goal**: Establish identity, discovery, state persistence, and real-time communication.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| OAuth2/OIDC + Custom Claims binding | P1 | Agent identity verification + identity mapping (ADR-17) |
| Well-known URI discovery | P1 | Basic agent discovery |
| Lite Registry (GitHub Pages) | P1 | Bridge discovery gap before v1.2 Registry (SD-11) |
| Agent health/liveness | P1 | Prevent stale agent entries (SD-10) |
| State Storage Interface + SQLite | P1 | Persistent state foundation (SD-9) |
| WebSocket binding + MessageAck | P1 | Real-time comms + reliable delivery for critical messages (ADR-16) |
| Webhook callbacks | P2 | Event-driven notifications |
| DNS-SD discovery | P3 | Local network discovery (defer to v1.1.1+) |

### Why This Matters

- OAuth2 enables enterprise agent identity; Custom Claims binding maps IdP subjects to agent IDs (ADR-17)
- Well-known URI allows agents to discover each other before Registry exists (Decision SD-7)
- Lite Registry provides early discoverability via GitHub Pages (Decision SD-11)
- Health/liveness prevents Registry from listing dead agents (Decision SD-10)
- State Storage Interface is foundational for v1.3 metering and v2.0 marketplace (Decision SD-9)
- WebSocket provides low-latency comms (Decision SD-3); MessageAck ensures reliable delivery for critical messages (ADR-16)

### Deliverables

```
src/asap/
├── auth/
│   ├── oauth2.py         # OAuth2 client & server
│   └── oidc.py           # OIDC discovery
├── state/
│   ├── snapshot.py        # SnapshotStore interface (exists) + SQLite impl
│   └── stores/
│       ├── sqlite.py      # SQLite reference implementation
│       └── memory.py      # InMemorySnapshotStore (moved)
├── transport/
│   ├── websocket.py      # WebSocket binding
│   └── webhook.py        # Webhook delivery
└── discovery/
    ├── wellknown.py      # /.well-known/asap/manifest.json
    ├── health.py         # /.well-known/asap/health
    └── registry.py       # Lite Registry client (SD-11)
```

---

## v1.2.0 "Verified Identity" — Cryptographic Trust

**Goal**: Enable verifiable agent identity and protocol compliance certification.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Signed manifests (Ed25519) | P1 | Verifiable agent identity |
| ASAP Compliance Harness | P1 | Protocol compliance testing |
| mTLS support (optional) | P2 | Transport-level trust |

> [!NOTE]
> **Deferred from v1.2**: Registry API Backend (to v2.1), DeepEval Intelligence (to v2.2+). See [deferred-backlog.md](./deferred-backlog.md).

### Why This Matters

- Signed manifests prevent agent impersonation (Decision SD-4)
- Compliance Harness certifies agents as "good citizens" of the network
- mTLS available for enterprise use cases (Decision SD-6)
- Lite Registry (v1.1, SD-11) provides discovery — no backend API needed yet

### Manifest Signing (Ed25519)

```json
{
  "manifest": {
    "id": "urn:asap:agent:example",
    "version": "1.0.0"
  },
  "signature": {
    "algorithm": "Ed25519",
    "public_key": "base64...",
    "value": "base64..."
  },
  "trust_level": "self-signed"
}
```

### Trust Levels (Decision SD-5)

| Level | Badge | Signing |
|-------|-------|---------|
| Self-signed | None | Agent's own key |
| Verified | ✓ | ASAP-signed after review |
| Enterprise | Custom | Organization's CA |

### Compliance Harness

**Shell-only strategy**: Protocol compliance testing via ASAP-native pytest harness.

| Layer | Tool | Validates |
|-------|------|-----------|
| Shell | pytest (ASAP native) | Handshake, Schema, State machine, SLA |

---

## v1.3.0 "Observability" — Visibility & Delegation

**Goal**: Enable usage visibility, service guarantees, and trust delegation.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Observability metering | P1 | Track resource consumption (visibility, not billing) |
| SLA framework | P1 | Define service guarantees |
| Delegation tokens | P1 | Trust chains for sub-agents |

> [!NOTE]
> **Deferred from v1.3**: Credit system (to v3.0), Audit logging (to v2.1+). See [deferred-backlog.md](./deferred-backlog.md).

### Usage Metering

```json
{
  "usage": {
    "task_id": "task_123",
    "agent": "urn:asap:agent:example",
    "metrics": {
      "tokens_in": 1500,
      "tokens_out": 2300,
      "duration_ms": 4500,
      "api_calls": 3
    }
  }
}
```

### Delegation Token

```json
{
  "delegation": {
    "delegator": "urn:asap:agent:enterprise",
    "delegate": "urn:asap:agent:research-team",
    "scopes": ["research.execute", "data.read"],
    "constraints": {
      "max_cost_usd": 100,
      "expires_at": "2026-02-28T00:00:00Z"
    },
    "signature": "..."
  }
}
```

### SLA Framework

SLAs define service guarantees as trust signals (not financial penalties in v1.3). The `SLADefinition` lives on the `Manifest` model; metrics are stored via a dedicated `SLAStorage` Protocol (InMemory + SQLite implementations). API endpoints use feature-centric paths (`/sla/*`).

---

## v1.4.0 "Hardening" — Resilience & Scale

**Goal**: Prepare the codebase for marketplace scale by addressing technical debt and performance bottlenecks.

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Type Safety Hardening | P1 | Eliminate runtime type errors |
| Storage Pagination | P1 | Scalable data access (SLA history, Metering) |

### Why This Matters

- **Type Safety**: Reduces regression risks as the codebase grows.
- **Pagination**: Prevents OOM errors when users query large datasets (vital for the SLA dashboards in v2.0).

---

## v2.0.0 "Marketplace" — The End Goal

**Goal**: Launch the Agent Marketplace as a Web App powered by the Lite Registry.

### Core Components

| Component | Description |
|-----------|-------------|
| **Web App** | Human interface for marketplace (SD-8) |
| **Lite Registry** | GitHub Pages JSON as data source (SD-11) |
| **Verified Badge** | Manual trust verification (IssueOps) |
| **Message Broker** | Optional premium for scale (SD-3) |

> [!NOTE]
> **Lean approach**: v2.0 reads from Lite Registry (`registry.json`) instead of a backend API. Registry API Backend is deferred to v2.1. See [deferred-backlog.md](./deferred-backlog.md).

> [!TIP]
> **Pre-launch (2026-02)**: Sprints M1–M3 complete. Registration and verification flows work via IssueOps (Web Form → GitHub Issue → Action). M4 (security audit, performance testing, docs) is the final gate before public launch.

### Web App (SD-8)

Human interface for marketplace interactions:

| Area | MVP Features | Status |
|------|-------------|--------|
| Landing | Hero, value prop, "Get Started" CTA | ✅ M1 |
| Registry Browser | Search, filters (skill, trust level), agent details | ✅ M2 |
| Developer Dashboard | My agents, pending registrations, Listed/Pending/Verified | ✅ M3 |
| Registration | Web Form → pre-filled GitHub Issue → Action auto-merge | ✅ M3 |
| Verified Badge | Manual IssueOps request (Free), form → GitHub Issue | ✅ M3 |
| Auth | OAuth2 (dog-fooding ASAP auth), `read:user` only | ✅ M1 |

**Technical Stack**:

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Frontend | **Next.js 15 (App Router)** | SSR for SEO, Registry indexing |
| Data Source | Lite Registry (GitHub JSON) | No backend needed for MVP |
| Auth | ASAP OAuth2 | Dog-fooding |
| Payments | None | Deferred to v3.0 |
| Hosting | Vercel | Simple for solo dev |
| Docs | Separate MkDocs | Keep docs simple (SD-8) |

**Domain**: asap-protocol.com (marketplace name TBD)

### Launch Criteria

- [ ] Lite Registry has 100+ agents
- [x] Verified badge flow working (Manual IssueOps process) — M3 complete
- [x] Web App live with core features (browse, search, register) — M1–M2 complete
- [x] Registration via Web Form → GitHub Issue → Action (IssueOps) — M3 complete
- [ ] Security audit passed (M4)
- [ ] Documentation complete (M4)

---

## v2.2.0 "Protocol Hardening" — Identity, Auth & Protocol Maturity

**Goal**: Elevate the protocol to production-grade with per-runtime-agent identity, capability-based authorization, streaming, and formal error handling. This is the most transformative release since v2.0.

**PRD**: [prd-v2.2-protocol-hardening.md](../prd/prd-v2.2-protocol-hardening.md)

### Features

#### Identity & Authorization (NEW — SD-12, SD-13, SD-14)

| Feature | Priority | Purpose |
|---------|----------|---------|
| Per-Runtime-Agent Identity | P0 | Host→Agent hierarchy; each session gets Ed25519 keypair |
| Capability-Based Authorization | P0 | Fine-grained capabilities with `min/max/in/not_in` constraints |
| Agent Lifecycle Management | P0 | Session TTL, max lifetime, absolute lifetime; reactivation as security checkpoint |
| Approval Flows (RFC 8628 + CIBA) | P1 | Protocol-level user consent for registration and capability escalation |
| Self-Authorization Prevention | P1 | WebAuthn/biometric proof for agents controlling the browser |

#### Protocol Maturity (Existing v2.2 scope)

| Feature | Priority | Purpose |
|---------|----------|---------|
| Streaming/SSE | P1 | `POST /asap/stream`, `TaskStream` payload, incremental responses |
| Error Taxonomy Evolution | P1 | `RecoverableError`/`FatalError`, recovery hints, structured retry |
| Unified Versioning | P1 | `ASAP-Version` header, content negotiation 2.1↔2.2 |
| Async Protocol | P1 | `AsyncSnapshotStore`, `AsyncMeteringStore`; sync path deprecated |
| A2H Integration Completion | P1 | Finalize pending A2H commits |
| Batch Operations | P2 | JSON-RPC batch (array of requests in one POST) |
| Compliance Harness v2 | P2 | Extended checks for streaming, errors, versioning, batch |
| Audit Logging | P2 | Tamper-evident logs, hash chain, `AuditStore` protocol |

### Deliverables

```
src/asap/
├── auth/
│   ├── identity.py        # HostIdentity, AgentSession models
│   ├── capabilities.py    # CapabilityDefinition, CapabilityGrant, constraints
│   ├── approval.py        # Device Authorization (RFC 8628), CIBA flows
│   ├── lifecycle.py       # Session TTL, max lifetime, reactivation logic
│   └── oauth2.py          # Existing (enhanced with capability mapping)
├── transport/
│   ├── sse.py             # SSE streaming endpoint
│   ├── batch.py           # JSON-RPC batch handler
│   └── server.py          # Updated: /asap/agent/* endpoints
├── models/
│   ├── errors.py          # RecoverableError, FatalError, recovery hints
│   └── versioning.py      # ASAP-Version negotiation
├── state/
│   ├── async_snapshot.py  # AsyncSnapshotStore protocol
│   ├── async_metering.py  # AsyncMeteringStore protocol
│   └── audit.py           # AuditStore, hash chain
└── handlers/
    └── a2h.py             # A2H completion
```

### Why This Matters

- **Per-agent identity** is the foundation for enterprise trust. Two agents sharing credentials = no visibility, no scoping, no isolation.
- **Capability constraints** enable regulated use cases (finance, health) — "transfer up to $1,000 in USD" instead of "has EXECUTE scope".
- **Streaming/SSE** closes the last major gap vs Google A2A.
- **Async protocols** resolve the CP-1 technical debt from sync SnapshotStore.

### Non-Goals (Deferred)

- Registry API Backend → v2.3
- TypeScript SDK → v2.3
- DeepEval → v2.3 (conditional)
- OpenAPI adapter → v2.4
- Economy Settlement → v3.0

---

## v2.3.0 "Scale" — Registry, SDKs & Discovery

**Goal**: Scale the ecosystem infrastructure and expand beyond Python with a TypeScript SDK, API-driven registration, and intelligent discovery.

**PRD**: [prd-v2.3-scale.md](../prd/prd-v2.3-scale.md)

**Trigger**: v2.2 released AND (500+ agents OR IssueOps bottleneck)

### Features

#### Registry & Discovery

| Feature | Priority | Purpose |
|---------|----------|---------|
| Registry API Backend | P1 | PostgreSQL: CRUD, search, trust scoring, `registry.json` mirror |
| Auto-Registration | P1 | Self-service API (no PR required), compliance gating |
| Intent-Based Directory Search | P1 | Natural-language queries ("I need an agent for code review") |
| Capability-Aware Introspection | P2 | RFC 7662 introspection returning grant info for resource servers |
| WWW-Authenticate ASAP Challenge | P3 | Resource servers redirect unknown agents to discovery |

#### SDK Expansion

| Feature | Priority | Purpose |
|---------|----------|---------|
| TypeScript Client SDK | P1 | `@asap-protocol/client` npm package |
| AI Framework Adapters (TS) | P2 | Vercel AI SDK, OpenAI SDK, Anthropic SDK adapters |

#### Protocol Enhancements

| Feature | Priority | Purpose |
|---------|----------|---------|
| Delegated/Autonomous Mode Formalization | P2 | Explicit mode support in manifest and registration |
| Runtime Capability Escalation | P2 | `POST /asap/agent/request-capability` — add capabilities without re-registration |
| Orchestration Primitives | P2 | `CoordinatorEnvelope`, `TaskGroup`, wait-all/any/first-success patterns |
| DeepEval Intelligence | P3 | Cognitive quality scoring (conditional: 3+ user requests) |

#### Governance & Privacy

| Feature | Priority | Purpose |
|---------|----------|---------|
| Privacy Considerations (Spec §) | P3 | Data retention, host key correlation, behavioral signals |

### Deliverables

```
src/asap/
├── registry/
│   ├── api.py             # REST API (CRUD, search, trust scoring)
│   ├── auto_register.py   # Self-service registration with compliance gate
│   └── intent_search.py   # NL intent search (BM25 + optional embeddings)
├── auth/
│   ├── introspection.py   # Capability-aware token introspection
│   ├── escalation.py      # Runtime capability request flow
│   └── modes.py           # Delegated/Autonomous mode support
├── orchestration/
│   ├── coordinator.py     # CoordinatorEnvelope, TaskGroup
│   └── patterns.py        # wait-all, wait-any, first-success
└── discovery/
    └── challenge.py       # WWW-Authenticate ASAP challenge

packages/
└── @asap-protocol/
    ├── client/            # TypeScript SDK (npm)
    └── adapters/          # Vercel AI, OpenAI, Anthropic
```

### Migration (v2.2 → v2.3)

| Action | Required? |
|--------|-----------|
| Migrate from IssueOps to API registration | Optional (IssueOps still works) |
| Add `mode` field to manifest | Recommended |
| Enable intent-based search in registry | Automatic for API-registered agents |

### Non-Goals (Deferred)

- OpenAPI adapter → v2.4
- Economy Settlement, Billing → v3.0
- Crypto/DeFi → v4.0+
- Federated Registry → v3.x+

---

## v2.4.0 "Adoption" — Lower Integration Barriers

**Goal**: Make ASAP trivially adoptable for services with existing APIs and ensure interoperability across the agent protocol landscape.

**Trigger**: v2.3 released

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| OpenAPI Adapter | P1 | Auto-derive ASAP capabilities from existing OpenAPI specs (zero-code onboarding) |
| MCP Auth Bridge | P2 | ASAP identity layer for MCP servers (solve MCP's auth gap) |
| Cross-Protocol Compatibility | P3 | Thin adapters for interop with other agent auth protocols |
| Formal ASAP Specification Document | P2 | RFC-style specification for standardization track |

### OpenAPI Adapter

```python
from asap.adapters.openapi import create_from_openapi

server = create_from_openapi(
    spec_url="https://api.example.com/openapi.json",
    default_capabilities=["GET", "HEAD"],
    approval_strength={"POST": "webauthn", "DELETE": "webauthn"},
)
```

Each OpenAPI `operationId` becomes a capability. Input/output schemas are derived from the spec. Execution proxies to the upstream API.

### Migration (v2.3 → v2.4)

| Action | Required? |
|--------|-----------|
| Use OpenAPI adapter for existing APIs | Optional (manual capability definitions still work) |
| Enable MCP Auth Bridge | Optional |

### Non-Goals (Deferred)

- Economy Settlement, Billing → v3.0
- ASAP Cloud → v3.0
- Crypto/DeFi → v4.0+

---

## v3.0.0 "Economy" — Monetization & Marketplace Economics

**Goal**: Enable paid agent services, verified badge monetization, and the foundation for an agent economy.

**PRD**: [prd-v3.0-economy.md](../prd/prd-v3.0-economy.md)

**Trigger**: 100+ Verified Agents willing to pay $49/mo OR agent-to-agent transactions > $5k/mo

### Features

| Feature | Priority | Purpose |
|---------|----------|---------|
| Payment Processing (Stripe) | P1 | Verified Badge $49/mo, webhooks, tax, Customer Portal |
| Credit System | P1 | 1 credit = $0.01, `price_per_task_credits`, SDK auto-deduct |
| Clearing House | P1 | 5–10% fee on agent-to-agent transactions, Stripe Connect payouts |
| Escrow & Disputes | P2 | Hold on task start, 24h dispute window, arbitration |
| SLA Financial Compensation | P2 | Breach penalties funded from escrow |
| ASAP Cloud (Alpha) | P2 | `asap deploy`, managed hosting ("Vercel for Agents") |

### Architecture

```
┌──────────────────────────────────────────────────────┐
│                  ECONOMY LAYER (v3.0)                 │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │
│  │   Stripe     │  │  Credits    │  │  Clearing    │ │
│  │   Backend    │  │  Ledger     │  │  House       │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘ │
│         └────────────────┼────────────────┘          │
│                    ┌─────┴──────┐                     │
│                    │ Settlement │                     │
│                    │  Backend   │ ← Pluggable Protocol│
│                    │ (Protocol) │                     │
│                    └────────────┘                     │
└──────────────────────────────────────────────────────┘
```

Settlement uses a pluggable `SettlementBackend` Protocol — Stripe is the v3.0 reference implementation. Crypto/DeFi (stablecoins on L2) lives in a **separate repo** (`asap-settlement-crypto`) for v4.0+.

### Non-Goals (Deferred)

- Crypto/DeFi settlement → v4.0+ (separate repo)
- Real-time bidding/auctions → v4.0+
- Enterprise SSO/SAML → TBD
- Federated Registry → v3.x+

---

## Roadmap Summary

```
v2.2 Protocol Hardening     v2.3 Scale           v2.4 Adoption        v3.0 Economy
═══════════════════════     ═══════════════      ═══════════════      ═══════════════
┌───────────────────┐       ┌──────────────┐     ┌──────────────┐    ┌──────────────┐
│ • Agent Identity  │       │ • Registry   │     │ • OpenAPI    │    │ • Stripe     │
│ • Capabilities +  │──────▶│   API Backend│────▶│   Adapter    │───▶│ • Credits    │
│   Constraints     │       │ • TS SDK     │     │ • MCP Auth   │    │ • Clearing   │
│ • Approval Flows  │       │ • Intent     │     │   Bridge     │    │   House      │
│ • Agent Lifecycle │       │   Search     │     │ • Formal     │    │ • Escrow     │
│ • Streaming/SSE   │       │ • Auto-Reg   │     │   Spec Doc   │    │ • ASAP Cloud │
│ • Error Taxonomy  │       │ • Orchestr.  │     │ • Cross-     │    │   (alpha)    │
│ • Versioning      │       │   Primitives │     │   Protocol   │    │              │
│ • Async Protocol  │       │ • Delegated/ │     │   Compat     │    │              │
│ • Batch Ops       │       │   Autonomous │     │              │    │              │
│ • Audit Logging   │       │ • Cap. Escal.│     │              │    │              │
│ • Compliance v2   │       │ • Privacy    │     │              │    │              │
└───────────────────┘       └──────────────┘     └──────────────┘    └──────────────┘

  🔐 Security &              📈 Growth &          🔌 Integration      💰 Monetization
  Protocol maturity          Ecosystem            & Adoption          & Economy
```

---

## Migration Guide

| Version | Action Required |
|---------|-----------------|
| v1.0 → v1.1 | Add OAuth2 config (with Custom Claims), expose well-known + health endpoints, choose storage backend, register in Lite Registry |
| v1.1 → v1.2 | Sign manifest with Ed25519, run compliance harness |
| v1.2 → v1.3 | Define SLAs in manifest, add metering hooks (using `MeteringStore` interface), configure delegation, set up `SLAStorage` |
| v1.3 → v2.0 | Register in marketplace Web App, consider Verified badge (Free) |
| v2.1 → v2.2 | Adopt per-agent identity (optional, OAuth2 still works), define capabilities with constraints, migrate to `AsyncSnapshotStore`, add `ASAP-Version` header |
| v2.2 → v2.3 | Migrate to API registration (optional), add `mode` to manifest, install TS SDK if applicable |
| v2.3 → v2.4 | Use OpenAPI adapter for existing APIs (optional) |
| v2.4 → v3.0 | Configure Stripe for Verified Badge billing, set `price_per_task_credits` in manifest |

### Backward Compatibility

- All v1.x releases maintain backward compat
- v2.0 may have breaking changes (advance notice provided)
- Migration tools provided for each version

---

## Risks & Blind Spots

Strategic risks identified during the v1.1.0 planning review (2026-02-07):

| Risk | Severity | Mitigation | Status |
|------|----------|------------|--------|
| **State persistence gap** | Critical | SD-9 Hybrid strategy, SQLite impl in v1.1 | ✅ Addressed |
| **Stale agents in Registry** | High | SD-10 Liveness protocol in v1.1 | ✅ Addressed |
| **Multi-agent workflow orchestration** | Medium | Saga/choreography patterns needed. Define in v1.2+ | ⏳ Tracked |
| **Agent capability versioning** | Medium | Define version negotiation for skills. Target v1.2 | ⏳ Tracked |
| **Storage backend alignment** | Medium | v1.1 defines interfaces; v1.2/v1.3/v2.0 reuse them | ✅ Addressed |
| **p95 latency (17-21ms vs 5ms target)** | Low | Documented in v1.0 retro. Horizontal scaling recommended. | ⏳ Tracked |

### Blind Spots to Monitor

| Area | Concern | When to Address |
|------|---------|-----------------|
| **Data residency** | Enterprise customers may require regional storage | v2.0 if enterprise traction |
| **Agent migration** | What happens when an agent moves to a different host? | v1.2 (Registry should handle re-registration) |
| **Rate limiting across transports** | HTTP has rate limiting, WebSocket does not | v1.1 Sprint S3 |
| **Conflict resolution** | Multi-agent parallel work on same task | v1.2+ (define in orchestration patterns) |
| **Host key correlation** | Same host keypair across servers enables cross-server tracking | v2.3 (privacy considerations) |
| **Self-authorization attack surface** | Agents controlling browsers can auto-approve; WebAuthn required | v2.2 (SD-14) |
| **TypeScript ecosystem gap** | AI tools (Claude, Cursor, ChatGPT) are TS-native; Python-only SDK limits adoption | v2.3 (TypeScript SDK) |
| **OpenAPI integration path** | Services with existing APIs need zero-code onboarding | v2.4 (OpenAPI adapter) |

---

## Resolved Questions

> **Note**: These are strategic roadmap questions (SQ). Architecture decisions are tracked separately in [Decision Records](../decision-records/README.md) with their own numbering (Q1-Q14).

| ID | Question | Decision | Reference |
|----|----------|----------|-----------|
| SQ-1 | Centralized vs federated registry? | Centralized first | SD-1 |
| SQ-2 | Signing algorithm? | Ed25519 | SD-4 |
| SQ-3 | mTLS required? | Optional only | SD-6 |
| SQ-4 | Discovery before Registry? | Yes, v1.1 | SD-7 |
| SQ-5 | Pricing model? | Freemium first | SD-2 |
| SQ-6 | WebSocket vs Broker? | WebSocket v1.x, Broker v2.0+ | SD-3 |
| SQ-7 | Docs inside Web App? | Separated (MkDocs + Web App) | SD-8 |
| SQ-8 | State management strategy? | Hybrid: Interface + Ref Impls + Managed | SD-9 |
| SQ-9 | Agent liveness protocol? | Health endpoint + TTL in manifest | SD-10 |
| SQ-10 | Discovery gap between v1.1 and v1.2? | Lite Registry on GitHub Pages | SD-11 |
| SQ-11 | WebSocket message reliability? | Selective ack for state-changing messages + AckAwareClient | ADR-16 |
| SQ-12 | Identity mapping (IdP sub → agent_id)? | Custom Claims + allowlist fallback | ADR-17 |
| SQ-13a | Per-agent vs per-service identity? | Per-runtime-agent keypair under Host | SD-12 |
| SQ-14a | Scope-based vs capability-based authz? | Capabilities with constraint operators | SD-13 |
| SQ-15a | Approval mechanism for agent registration? | RFC 8628 + CIBA + WebAuthn | SD-14 |

## Open Source vs. Proprietary Boundary

We follow an **Open Core + SaaS** model (LangChain-style). See [vision-agent-marketplace.md](./vision-agent-marketplace.md#55-open-source-vs-proprietary-boundary-langchain-style) for full details.

| Phase | Public (repo) | Private (separate) |
|-------|---------------|---------------------|
| **v2.0-v2.2 (current)** | SDK (Python + TS), Web App, Lite Registry | — |
| **v2.3-v2.4** | SDK, Web App frontend, OpenAPI adapter | Registry API Backend |
| **v3.0** | SDK, Web App frontend | Registry API, Billing, Economy Settlement |

**Decision point**: Start separating when building **v2.3 Registry API Backend**. Until then, everything stays public. Cloning the repo does not replace the product (network effect, trust, backend services).

---

## Open Questions

| ID | Question | Decide By |
|----|----------|-----------|
| SQ-13 | Monetization model post-adoption? | After traction data |
| SQ-14 | Federation protocol spec? | v2.x if needed |
| SQ-15 | Marketplace product name? | Before v2.0 launch |

---

## Success Metrics by Version

| Version | Key Metric | Target |
|---------|------------|--------|
| v1.1 | OAuth2 adoption | 50% of users |
| v1.2 | Signed manifests | 80% of agents |
| v1.3 | SLA definitions | 60% of agents |
| v2.0 | Marketplace registrations | 100+ agents |
| v2.2 | Per-agent identity adoption | 30% of new agents use runtime identity |
| v2.2 | Capability-based grants | 50% of agents define capabilities |
| v2.3 | TypeScript SDK downloads | 500+ npm weekly downloads |
| v2.3 | Intent-based searches | 100+ daily queries |
| v2.4 | OpenAPI adapter usage | 20+ services onboarded via adapter |

---

## Related Documents

- **Vision**: [vision-agent-marketplace.md](./vision-agent-marketplace.md)
- **Deferred Backlog**: [deferred-backlog.md](./deferred-backlog.md)
- **Repository Strategy**: [repository-strategy.md](./repository-strategy.md)
- **Design Decisions**: [Decision Records](../decision-records/README.md)
- **v1.1 PRD**: [prd-v1.1-roadmap.md](../prd/prd-v1.1-roadmap.md)
- **v1.2 PRD**: [prd-v1.2-roadmap.md](../prd/prd-v1.2-roadmap.md)
- **v1.3 PRD**: [prd-v1.3-roadmap.md](../prd/prd-v1.3-roadmap.md)
- **v2.0 PRD**: [prd-v2.0-roadmap.md](../prd/prd-v2.0-roadmap.md)
- **v2.2 PRD**: [prd-v2.2-protocol-hardening.md](../prd/prd-v2.2-protocol-hardening.md)
- **v2.3 PRD**: [prd-v2.3-scale.md](../prd/prd-v2.3-scale.md)
- **Checkpoints**: [checkpoints.md](../../dev-planning/checkpoints.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial roadmap document |
| 2026-02-05 | Added strategic decisions (SD-1 to SD-7) with rationale |
| 2026-02-05 | Added Web App to v2.0, SD-8 (docs architecture) |
| 2026-02-07 | Strategic review: added SD-9 (State Management Hybrid), SD-10 (Agent Liveness) |
| 2026-02-07 | Added Risks & Blind Spots section, updated v1.1 features |
| 2026-02-07 | Resolved Q8 (state management) and Q9 (liveness), renumbered open questions |
| 2026-02-07 | Added SD-11 (Lite Registry), resolved SQ-10/11/12, updated v1.1 features |
| 2026-02-12 | **Lean Marketplace pivot**: v1.2 renamed "Verified Identity" (removed Registry API, DeepEval), v1.3 renamed "Observability" (removed credit system, audit logging), v2.0 simplified to Web App + Lite Registry (removed backend services). Added deferred-backlog.md reference |
| 2026-02-13 | **Security Hardening**: Updated SD-4 to include JCS (RFC 8785) and Strict Verification (RFC 8032) |
| 2026-02-18 | **v1.3 SLA decisions**: Added SLAStorage to SD-9, expanded v1.3 section with SLA Framework details (/sla/* API, trust signals), updated migration guide |
| 2026-02-18 | **v1.3.0 released**: Marked v1.3.0 as released in Release Timeline. Removed duplicate v1.4.0 section. |
| 2026-02-21 | **Sprint M3 complete**: Status → LAUNCH PREP. Launch criteria updated (IssueOps, registration, verification done). Web App table with status. v2.0.0 timeline note. |
| 2026-02-21 | **Open Core boundary**: Added Open Source vs. Proprietary section. Public until v2.1; Registry API Backend and billing become private. |
| 2026-02-25 | **v2.0.0 Released**: Status → RELEASED. Release timeline updated with v2.1.0 (Ecosystem), v2.2.0 (Scale), v3.0.0 (Economy). PRDs created for each. Header updated. |
| 2026-03-13 | **Strategic Review v2.2**: Re-scoped v2.2 from "Scale & Registry" to "Protocol Hardening" (streaming, errors, versioning, batch, async). Marketplace items deferred to v2.3 (triggers not met). Added v2.3.0 "Scale" to timeline. |
| 2026-03-20 | **Identity & Auth Hardening**: Added SD-12 (per-runtime-agent identity), SD-13 (capability-based authz with constraints), SD-14 (approval flows — Device Auth, CIBA, WebAuthn). Updated v2.2 scope to include identity/auth features. Added v2.4.0 "Adoption" to timeline (OpenAPI adapter, ASAP challenge). Added new blind spots (host correlation, self-auth, TS gap, OpenAPI). Extended success metrics for v2.2–v2.4. Resolved SQ-13a/14a/15a. |
