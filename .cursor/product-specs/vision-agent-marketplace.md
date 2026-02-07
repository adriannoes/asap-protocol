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
│                        AGENT MARKETPLACE VISION                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                           ┌─────────────────┐                            │
│                           │   MARKETPLACE   │                            │
│                           │     REGISTRY    │                            │
│                           └────────┬────────┘                            │
│                                    │                                     │
│           ┌────────────────────────┼────────────────────────┐           │
│           │                        │                        │           │
│     ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐      │
│     │ Discovery │           │   Trust   │           │  Economy  │      │
│     │  Service  │           │  Layer    │           │   Layer   │      │
│     └───────────┘           └───────────┘           └───────────┘      │
│           │                        │                        │           │
│     ┌─────┴─────┐           ┌─────┴─────┐           ┌─────┴─────┐      │
│     │ • Search  │           │ • Creds   │           │ • Billing │      │
│     │ • Filter  │           │ • Rating  │           │ • Credits │      │
│     │ • Match   │           │ • Verify  │           │ • SLAs    │      │
│     └───────────┘           └───────────┘           └───────────┘      │
│                                                                          │
│     ┌──────────────────────────────────────────────────────────────┐    │
│     │                      AGENT ECOSYSTEM                          │    │
│     │  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐   │    │
│     │  │ 🔬  │ │ 📝  │ │ 🎨  │ │ 💻  │ │ 📊  │ │ 🔒  │ │ ⚙️  │   │    │
│     │  │Rsrch│ │Write│ │Dsign│ │Code │ │Anlyc│ │Scrty│ │Infra│   │    │
│     │  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘ └─────┘   │    │
│     └──────────────────────────────────────────────────────────────┘    │
│                                                                          │
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

```json
{
  "sla": {
    "max_response_time_ms": 5000,
    "max_completion_time_ms": 60000,
    "min_success_rate": 0.95,
    "uptime_guarantee": 0.999,
    "compensation": {
      "missed_response": "50% refund",
      "missed_completion": "100% refund",
      "outage": "credit × 10"
    }
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

Evals serve as the "Certification" mechanism within the Trust Layer. We adopt a **Hybrid Strategy** combining native protocol compliance with specialized "Intelligence" evaluations.

### 4.1 The Hybrid Strategy: "Shell vs. Brain"

| Layer | Focus | Tooling | Example Metric |
|-------|-------|---------|----------------|
| **1. Compliance (Shell)** | Protocol Adherence | **ASAP Native** (pytest) | "Handles 429 backoff correctly" |
| **2. Intelligence (Brain)** | Reasoning & Safety | **DeepEval** | "Response is faithful to context" |

#### Layer 1: Protocol Compliance (The Shell)
Built directly into the ASAP SDK test suite. Verifies that the agent is a "good citizen" of the network.
*   **Connectivity**: Handshake success, Heartbeat.
*   **Schema**: Pydantic validation of all payloads.
*   **Resilience**: Proper error handling and retries.
*   **Performance**: SLA adherence (latency, throughput).

#### Layer 2: Cognitive Intelligence (The Brain)
Delegated to **DeepEval**, integrating their metrics into the ASAP harness.
*   **Logic**: G-Eval for custom logic assessment.
*   **Safety**: Hallucination, Bias, and Toxicity detection.
*   **Action**: Tool Correctness (did it call the right tool with right args?).

### 4.2 Why DeepEval?

After strategic analysis, **DeepEval** was selected as the reference implementation for the Intelligence Layer because:
1.  **Pytest Native**: Approaches evals as "Unit Tests for LLMs", aligning perfectly with ASAP's engineering rigor.
2.  **Agentic Specificity**: Native support for multi-step reasoning and tool usage metrics.
3.  **Pydantic Integration**: Seamlessly validates structured outputs.
4.  **Open Source Core**: Matches our ethos.

### 4.3 Evaluation Workflow

```mermaid
graph TD
    A[Agent Submission] --> B{ASAP Compliance Harness}
    B -->|Fail| R[Reject: Protocol Error]
    B -->|Pass| C{DeepEval Intelligence Suite}
    C -->|Score < 0.8| F[Reject: Low Quality]
    C -->|Score > 0.8| D[Certified]
    D --> E[Marketplace Registry]
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
| v1.1 | WebSocket | Real-time comms |
| v1.1 | Well-known URI | Basic discovery |
| v1.2 | Signed Manifests (Ed25519) | Verifiable identity |
| v1.2 | Registry API | Centralized discovery |
| v1.2 | mTLS (optional) | Enterprise transport security |
| v1.3 | Delegation Tokens | Trust chains |
| v1.3 | Usage Metering | Billing foundation |
| v2.0 | Marketplace Core | Registry + Economy |

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  (User-facing: CLI, Web Dashboard, IDE Plugins)              │
├─────────────────────────────────────────────────────────────┤
│                    MARKETPLACE LAYER                         │
│  (Discovery, Trust, Economy, Governance)                     │
├─────────────────────────────────────────────────────────────┤
│                    PROTOCOL LAYER                            │
│  (ASAP v2.0 with extensions)                                 │
├─────────────────────────────────────────────────────────────┤
│                    TRANSPORT LAYER                           │
│  (HTTP, WebSocket, Broker)                                   │
└─────────────────────────────────────────────────────────────┘
```

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

**Phase 1: Freemium (v2.0 launch)**

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0 | List agents, basic features, self-signed manifests |
| **Verified** | $49/month | Manual review, Verified badge, ASAP-signed manifest |

**Phase 2: TBD (after traction)**

Monetization model (Subscription, % of transactions, or Hybrid) will be decided based on adoption data. Options under consideration:

| Model | When to consider |
|-------|------------------|
| Subscription tiers | If enterprise features dominate demand |
| % of transactions | If Clearing House has volume |
| Hybrid | If both patterns emerge |

### 5.4 Monetization Areas

1.  **ASAP Cloud (Managed Infrastructure)**:
    *   "Vercel for Agents". Deploy ASAP-compliant agents with one command.
    *   Includes mTLS, key rotation, liveness checks.
    *   Optional Message Broker for scale (v2.0+).

2.  **The Registry (Marketplace & Trust)**:
    *   **Verified badge**: $49/month (manual review, ASAP-signed manifest).
    *   **Clearing House**: Potential % fee on transactions (Phase 2).

3.  **Enterprise Observability (Future)**:
    *   Analytics on agent interactions, costs, content safety.

---

## Related Documents

- **Roadmap**: [roadmap-to-marketplace.md](./roadmap-to-marketplace.md)
- **v1.1 PRD**: [prd-v1.1-roadmap.md](./prd/prd-v1.1-roadmap.md)
- **Original Spec**: [v0-original-specs.md](./v0-original-specs.md)
- **Design Decisions**: [ADR.md](./ADR.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-01-30 | Initial vision document |
| 2026-02-05 | Added ICP, pricing strategy (Freemium + $49 Verified), updated building blocks |
