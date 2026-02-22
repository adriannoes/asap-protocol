# ASAP Protocol: Agent Marketplace Vision

> **The End Goal**: A decentralized ecosystem where AI agents discover, trust, and collaborate autonomously.
>
> **Status**: VISION DOCUMENT
> **Horizon**: v2.0.0+
> **Created**: 2026-01-30

---

## Executive Summary

The **Agent Marketplace** is the ultimate vision for the ASAP Protocol: an open infrastructure where AI agents can:

1. **Register** their capabilities and services
2. **Discover** other agents dynamically
3. **Establish trust** through reputation and credentials
4. **Collaborate** on complex, multi-agent workflows
5. **Transact** value (credits, tokens, or real currency)

This transforms ASAP from a *communication protocol* into an *agent economy protocol*.

---

## Strategic Pillars

To achieve this vision while serving Enterprise needs, ASAP prioritizes:
1.  **Compliance First (Shell vs Brain)**: We prioritize Protocol Compliance (Security, Schema, SLAs) over "Intelligence". The protocol is the secure "Shell"; the agent's logic is the "Brain".
2.  **Enterprise Readiness**: Zero-trust architecture (mTLS, Signed Manifests) is not an afterthought. We build for regulated industries (Finance, Health).
3.  **Neutrality**: The marketplace is unbiased. Reputation is mathematical, not curated.

---

## The Vision

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AGENT MARKETPLACE VISION                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│                           ┌─────────────────┐                           │
│                           │   MARKETPLACE   │                           │
│                           │     REGISTRY    │                           │
│                           └────────┬────────┘                           │
│                                    │                                    │
│           ┌────────────────────────┼────────────────────────┐           │
│           │                        │                        │           │
│     ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐       │
│     │ Discovery │           │   Trust   │           │  Economy  │       │
│     │  Service  │           │  Layer    │           │   Layer   │       │
│     └───────────┘           └───────────┘           └───────────┘       │
│           │                        │                        │           │
│     ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐       │
│     │ • Search  │           │ • Creds   │           │ • Billing │       │
│     │ • Filter  │           │ • Rating  │           │ • Credits │       │
│     │ • Match   │           │ • Verify  │           │ • SLAs    │       │
│     └───────────┘           └───────────┘           └───────────┘       │
│                                                                         │
│     ┌───────────────────────────────────────────────────────────────┐   │
│     │                      AGENT ECOSYSTEM                          │   │
│     │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │   │
│     │  │     │ │     │ │     │ │     │ │     │ │     │ │     │      │   │
│     │  │Rsrch│ │Write│ │Dsign│ │Code │ │Anlyc│ │Scrty│ │Infra│      │   │
│     │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘      │   │
│     └───────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Discovery Service

**Purpose**: Find the right agent for any task.

| Feature | Description |
|---------|-------------|
| **Skill Search** | Query by capability, domain, or task type |
| **Semantic Matching** | AI-powered matching beyond keywords |
| **Availability Check** | Real-time capacity and queue status |
| **Geo-awareness** | Prefer local/regional agents for latency |
| **Version Filtering** | Match ASAP protocol versions |

**Example Query**:
```json
{
  "query": {
    "skill": "code_review",
    "languages": ["python", "typescript"],
    "min_rating": 4.5,
    "max_latency_ms": 5000,
    "trust_level": "verified"
  }
}
```

---

### 2. Trust Layer

**Purpose**: Establish and verify agent trustworthiness.

#### 2.1 Credential Types

| Credential | Description | Issuer |
|------------|-------------|--------|
| **Self-Signed** | Basic identity claim | Agent itself |
| **Organization** | Org membership verified | Enterprise |
| **Verified** | Third-party audit passed | Marketplace |
| **Certified** | Specialized skill certified | Industry body |

#### 2.2 Reputation System

```
Agent Reputation Score = f(
  success_rate,        # % of tasks completed successfully
  response_time,       # Avg time to first response
  sla_compliance,      # % of SLAs met
  peer_ratings,        # Ratings from other agents
  dispute_rate,        # % of tasks with disputes
  tenure               # Time active in marketplace
)
```

#### 2.3 Trust Delegation

Agents can delegate trust to sub-agents:

```mermaid
graph TD
    A[Enterprise Agent] -->|delegates to| B[Research Team]
    B -->|delegates to| C[Research Agent 1]
    B -->|delegates to| D[Research Agent 2]
    A -->|delegates to| E[Security Team]
```

---

### 3. Economy Layer

**Purpose**: Enable value exchange between agents.

#### 3.1 Pricing Models

| Model | Use Case | Example |
|-------|----------|---------|
| **Per-Task** | Simple, predictable | "$0.50 per summary" |
| **Per-Token** | LLM-based work | "$0.01 per 1K tokens" |
| **Subscription** | Ongoing relationship | "$100/month unlimited" |
| **Auction** | Competitive pricing | "Bid for priority" |
| **Free Tier** | Community/OSS | "100 tasks/day free" |

#### 3.2 SLA Framework

> [!NOTE]
> **v1.3 scope**: SLAs are trust signals (availability, latency, error rate). Financial compensation (refunds, credits) is deferred to v3.0+ marketplace economics.

```json
{
  "sla": {
    "availability": "99.5%",
    "max_latency_p95_ms": 5000,
    "max_error_rate": "1%",
    "support_hours": "business"
  }
}
```

**v3.0+ extension** (deferred):
```json
{
  "compensation": {
    "missed_response": "50% refund",
    "missed_completion": "100% refund",
    "outage": "credit × 10"
  }
}
```

#### 3.3 Settlement

| Method | Latency | Trust Required |
|--------|---------|----------------|
| **Pre-paid credits** | Instant | Low |
| **Escrow** | On completion | Medium |
| **Invoicing** | Net-30 | High |
| **Crypto** | Near-instant | None |

---

## 4. Agent Evaluations ("Evals")

**Purpose**: Provide objective, verifiable metrics for agent quality and safety.

Evals serve as the "Certification" mechanism within the Trust Layer. The marketplace MVP focuses on **Protocol Compliance (Shell)** — ensuring agents are "good citizens" of the network.

### 4.1 Protocol Compliance ("Shell")

| Layer | Focus | Tooling | Example Metric |
|-------|-------|---------|----------------|
| **1. Compliance (Shell)** | Protocol Adherence | **ASAP Native** (pytest) | "Handles 429 backoff correctly" |
| **2. Intelligence (Brain)** | Reasoning & Safety | **Deferred (v2.2+)** | "Response is faithful to context" |

#### Layer 1: Protocol Compliance (The Shell)
Built directly into the ASAP SDK test suite. Verifies that the agent is a "good citizen" of the network.
*   **Connectivity**: Handshake success, Heartbeat.
*   **Schema**: Pydantic validation of all payloads.
*   **Resilience**: Proper error handling and retries.
*   **Performance**: SLA adherence (latency, throughput).

#### Layer 2: Cognitive Intelligence (The Brain) — Deferred

> [!NOTE]
> Intelligence evaluation (DeepEval integration) is deferred to v2.2+. The marketplace does not require AI quality scoring to function — it requires protocol compliance. See [Deferred Backlog](./deferred-backlog.md#2-deepeval-intelligence-layer-originally-v12-sprint-t61).

### 4.2 Evaluation Workflow

```mermaid
graph TD
    A[Agent Submission] --> B{ASAP Compliance Harness}
    B -->|Fail| R[Reject: Protocol Error]
    B -->|Pass| D[Certified]
    D --> E[Marketplace Listing]
```

---

## Use Cases

### UC-1: Dynamic Team Assembly

```
User: "Build me a marketing website"

Coordinator Agent:
  ├── Discovers: Design Agent (UI/UX)
  ├── Discovers: Content Agent (Copywriting)
  ├── Discovers: Dev Agent (Frontend)
  ├── Discovers: SEO Agent (Optimization)
  └── Orchestrates workflow across all

Result: Website delivered, all agents paid automatically
```

### UC-2: Specialized Expertise On-Demand

```
Research Agent working on medical paper:
  ├── Discovers: PubMed Search Agent (literature)
  ├── Discovers: Statistical Agent (analysis)
  ├── Discovers: Citation Agent (formatting)
  └── Pays per-use for specialized skills

Result: High-quality paper with expert contributions
```

### UC-3: Redundancy & Failover

```
High-availability deployment:
  ├── Primary: Agent A (99.9% SLA, $$$)
  ├── Backup: Agent B (99% SLA, $$)
  └── Emergency: Agent C (best-effort, $)

Auto-failover based on health checks
```

---

## Technical Building Blocks

### Required Before Marketplace

| Version | Component | Purpose |
|---------|-----------|---------|
| v1.0 | Core Protocol | Stable foundation |
| v1.1 | OAuth2/OIDC | Identity infrastructure |
| v1.1 | Well-known URI + Health | Basic discovery + agent liveness (SD-10) |
| v1.1 | State Storage Interface + SQLite | Persistent state foundation (SD-9) |
| v1.1 | WebSocket | Real-time comms |
| v1.2 | Signed Manifests (Ed25519) | Verifiable identity (Ed25519 + JCS) |
| v1.2 | Compliance Harness | Protocol certification |
| v1.2 | mTLS (optional) | Enterprise transport security |
| v1.3 | Delegation Tokens | Trust chains |
| v1.3 | Observability Metering | Usage visibility (uses MeteringStore from v1.1) |
| v1.3 | SLA Framework | Service guarantees as trust signals (SLAStorage, /sla/* API) |
| v2.0 | Marketplace Core | Web App + Lite Registry + Verified Badge |

### Architecture Layers

```
┌──────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  (User-facing: CLI, Web Dashboard, IDE Plugins)              │
├──────────────────────────────────────────────────────────────┤
│                    MARKETPLACE LAYER                         │
│  (Discovery, Trust, Economy, Governance)                     │
├──────────────────────────────────────────────────────────────┤
│                    PROTOCOL LAYER                            │
│  (ASAP v2.0 with extensions)                                 │
├──────────────────────────────────────────────────────────────┤
│                    STORAGE LAYER (SD-9)                      │
│  (SnapshotStore, MeteringStore — Agent's choice of backend)  │
├──────────────────────────────────────────────────────────────┤
│                    TRANSPORT LAYER                           │
│  (HTTP, WebSocket, Broker)                                   │
└──────────────────────────────────────────────────────────────┘
```

### State Management Strategy (SD-9)

ASAP follows a **Hybrid strategy** for state management, balancing developer experience with ecosystem independence:

| Layer | Data | Owner | Storage |
|-------|------|-------|---------|
| **Protocol Interface** | `SnapshotStore`, `MeteringStore` | ASAP SDK (open source) | Agent's choice |
| **Reference Impls** | SQLite, Redis, PostgreSQL adapters | Separate packages | Agent's infra |
| **Marketplace Metadata** | Manifests, trust scores, SLA metrics | ASAP centrally | Lite Registry (v2.0), PostgreSQL (v2.1+) |
| **Agent Task State** | Snapshots, event history, artifacts | Agent developer | Agent's choice |
| **ASAP Cloud** (future) | Managed storage, backups | ASAP premium | Managed infra |

**Key principle**: ASAP is the "protocol + marketplace", not the "database". Agents own their data. ASAP provides interfaces and reference implementations to reduce friction, and the marketplace stores only ecosystem metadata (who is registered, trust scores, SLA compliance).

**Reference**: [ADR-13](../decision-records/01-architecture.md)

---

## Governance Model

### Options Under Consideration

| Model | Pros | Cons |
|-------|------|------|
| **Foundation** | Neutral, trusted | Slow, bureaucratic |
| **Decentralized (DAO)** | Community-driven | Complex, slower |
| **Federated** | Multiple registries | Fragmentation risk |
| **Hybrid** | Best of both | Complexity |

### Key Decisions (v2.0)

1. Who can register agents?
2. How are disputes resolved?
3. What are delisting criteria?
4. Who sets fee structures?
5. How is the registry funded?

---

## Success Metrics (v2.0+)

| Metric | Target |
|--------|--------|
| Registered agents | 1,000+ |
| Daily transactions | 10,000+ |
| Cross-org collaborations | 100+ monthly |
| Average trust score | > 4.0/5.0 |
| Dispute rate | < 1% |
| Platform uptime | 99.99% |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Centralization | Federated registry option |
| Spam/abuse | Stake requirements, reputation |
| Privacy leaks | Minimal data collection |
| Economic attacks | Rate limits, fraud detection |
| Regulatory | Compliance framework |

---

## 5. Sustainability & Commercial Strategy

We adopt an **Open Core** model (similar to LangChain/LangSmith). The Goal: ubiquity for the protocol, profitability for the ecosystem.

**Strategic Priority**: Adoption first, monetization later.

### 5.1 Target Audience (ICP)

| Priority | Segment | Why |
|----------|---------|-----|
| 1 | AI Startups | Build products for enterprise using ASAP |
| 2 | Individual Developers | Experiment, prototype, contribute |
| Future | Enterprise Direct | After protocol adoption is proven |

### 5.2 The Open Source Core (Free forever)

*   **The Standard**: Protocol specs, SDKs (Python/Node), CLI tools.
*   **The "Shell"**: ASAP Compliance Harness (pytest-based testing).
*   **License**: Permissive (MIT/Apache) to maximize adoption.

### 5.3 Pricing Strategy

**Phase 1: Free (v2.0 launch)**

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0 | List agents, basic features, self-signed manifests |
| **Verified** | $0 | Manual review, Verified badge, ASAP-signed manifest (High bar for entry) |

**Phase 2: Monetization (v3.0+)**

Monetization model (Subscription, % of transactions, or Hybrid) deferred until critical mass is reached.

| Model | When to consider |
|-------|------------------|
| Subscription ($49/mo) | If enterprise features dominate demand |
| % of transactions | If Clearing House has volume |

### 5.4 Monetization Areas (Deferred to v3.0)

1.  **ASAP Cloud (Managed Infrastructure)**:
    *   "Vercel for Agents". Deploy ASAP-compliant agents with one command.

2.  **The Registry (Marketplace & Trust)**:
    *   **Verified badge**: Currently free to build trust. Future: $49/month.
    *   **Clearing House**: Potential % fee on transactions.

3.  **Enterprise Observability**:
    *   Analytics on agent interactions, costs, content safety.

### 5.5 Open Source vs. Proprietary Boundary (LangChain-style)

We follow an **Open Core + SaaS** model: open source drives adoption; proprietary services drive revenue. The boundary defines what stays public vs. private.

#### What Stays Public (Forever)

| Component | Rationale |
|-----------|-----------|
| **Protocol SDK** (`asap` Python package) | Standard, adoption, ecosystem lock-in |
| **Web App frontend** (Next.js) | Thin client; value is in backend + network |
| **Lite Registry** (`registry.json`) | Community asset, discoverability |
| **Compliance Harness** | Protocol certification, trust in the standard |

#### What Becomes Private (When Monetizing)

| Component | When | Rationale |
|-----------|------|-----------|
| **Registry API Backend** | v2.1 (500+ agents) | Search, scale, rate limits — runs on our infra |
| **Billing / Stripe integration** | v3.0 | Payment processing, subscription logic |
| **Economy Settlement** | v3.0 | Credits, clearing house, payouts |
| **ASAP Cloud** (managed storage) | Future | Hosted infrastructure |

#### Why Cloning the Repo Does Not Replace the Product

1. **Network effect**: Registry data, agent listings, reputation — maintained by us.
2. **Trust**: Verified badge, CA signing — we are the trust anchor.
3. **Backend services**: Registry API, billing — run on our infrastructure.
4. **Support**: SLA, enterprise contracts — not replicable by code.

#### Repository Strategy

```
PUBLIC REPO (asap-protocol)
├── src/asap/           # Protocol SDK (MIT)
├── apps/web/           # Frontend (can stay public)
└── registry.json       # Lite Registry

PRIVATE / SaaS (when v2.1+)
├── Registry API Backend
├── Billing / Stripe
└── Economy Settlement
```

**Decision point**: Start separating when building **v2.1 Registry API Backend**. Until then, everything stays public.

---

## Related Documents

- **Roadmap**: [roadmap-to-marketplace.md](./roadmap-to-marketplace.md)
- **Deferred Backlog**: [deferred-backlog.md](./deferred-backlog.md)
- **v1.1 PRD**: [prd-v1.1-roadmap.md](../prd/prd-v1.1-roadmap.md)
- **Original Spec**: [v0-original-specs.md](./v0-original-specs.md)
- **Repository Strategy**: [repository-strategy.md](./repository-strategy.md)
- **Design Decisions**: [Decision Records](../decision-records/README.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial vision document |
| 2026-02-05 | Added ICP, pricing strategy (Freemium + $49 Verified), updated building blocks |
| 2026-02-07 | Strategic review: added State Management strategy (SD-9), Storage Layer, updated building blocks with liveness (SD-10) |
| 2026-02-12 | **Lean Marketplace pivot**: Removed DeepEval as mandatory (deferred v2.2+), simplified eval workflow to Shell-only, replaced Registry API with Compliance Harness in building blocks, updated v1.3 metering to "Observability", added deferred-backlog.md reference |
| 2026-02-13 | **Security Hardening**: Added JCS/Strict Verification to building blocks |
| 2026-02-18 | **v1.3 SLA decisions**: Updated SLA Framework (trust signals, no compensation in v1.3), added SLAStorage + /sla/* API to building blocks, aligned with sprint E3 plan |
| 2026-02-21 | **Open Core boundary**: Added §5.5 Open Source vs. Proprietary (LangChain-style). Public: SDK, frontend, Lite Registry. Private from v2.1: Registry API, billing, economy. |
