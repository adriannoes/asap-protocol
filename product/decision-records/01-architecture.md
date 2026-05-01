# ASAP Protocol: Architecture Decisions

> **Category**: Architecture & Patterns
> **Focus**: State, Topology, Consistency

---

## Question 1: Is Event-Sourced State Necessary for MVP?

### The Question
The spec proposes an **event-sourced state model** (Section 5.3). Is this over-engineering for an MVP, or a justified architectural investment?

### Analysis

| Aspect | Event-Sourced | Simple Mutable State |
|--------|---------------|---------------------|
| **Complexity** | Higher (events, reducers, snapshots) | Lower (CRUD operations) |
| **Auditability** | Full history preserved | Manual logging required |
| **Recovery** | Deterministic replay | Checkpoint restore only |
| **Storage** | Grows unbounded without compaction | Fixed size per task |
| **Implementation** | Specialized knowledge needed | Common patterns |

### Expert Assessment

**Pros of Event-Sourcing**:
- Natural fit for long-running agent tasks (hours/days)
- Debugging distributed failures requires understanding "what happened"
- Aligns with industry trend toward observability-first design
- Supports time-travel debugging critical for agent development

**Cons**:
- Adds significant implementation complexity
- May discourage adoption by teams unfamiliar with pattern
- Overkill for simple, short-lived tasks

### Recommendation: **MODIFY**

Reframe as **optional capability**, not requirement:

```
State persistence modes:
1. "snapshot" (default) – Simple checkpoint/restore
2. "event-sourced" (opt-in) – Full event history with replay
```

### Spec Amendment

> [!NOTE]
> Added to Section 5.3: State persistence is **mode-selectable**. Implementations MUST support `snapshot` mode. Event-sourced mode is RECOMMENDED for tasks exceeding 1 hour or requiring audit trails.

---

## Question 3: Is Peer-to-Peer Default Practical?

### The Question
Section 7.1 defaults to P2P topology. Is this practical given discovery/trust challenges?

### Analysis

**P2P Challenges Identified**:
1. **N² connections**: 10 agents = 90 potential connections
2. **Discovery**: How do agents find each other initially?
3. **Trust bootstrap**: No central authority to vouch for agents
4. **NAT traversal**: Agents behind firewalls cannot receive connections

**Industry Context**:
- A2A assumes direct HTTP connections (client → server)
- Most production systems use hub/orchestrator patterns
- Message meshes (NATS, Kafka) increasingly common for scale

### Expert Assessment

**P2P makes sense when**:
- Small teams (≤5 agents)
- Single trust domain
- Development/testing scenarios
- Low-latency requirements

**Hub/Mesh better when**:
- Enterprise deployments
- Cross-organization coordination
- Audit/compliance requirements
- Scale beyond 10 agents

### Recommendation: **MODIFY**

Reframe as **deployment patterns** rather than topology choice:

```
Deployment Patterns:
1. "direct" – Agent-to-agent HTTP (dev, small teams)
2. "orchestrated" – Via coordinator agent (enterprise)
3. "mesh" – Via message broker (scale)
```

Default recommendation should be **context-dependent**, not universal.

### Spec Amendment

> [!IMPORTANT]
> Modified Section 7.1: Removed "default" designation from P2P. Added deployment pattern recommendations based on scale and trust requirements. Direct connections recommended for ≤5 agents in single trust domain.

---

## Question 4: What Consistency Model for Shared State?

### The Question
When multiple agents coordinate on a task, what consistency guarantees apply to shared state?

### Analysis

The current spec doesn't explicitly address this. This is a gap.

**Consistency Options**:

| Model | Guarantee | Agent Impact |
|-------|-----------|--------------|
| **Strong** | All agents see same state instantly | Requires coordination overhead |
| **Eventual** | State converges eventually | Agents may make decisions on stale data |
| **Causal** | Respects happened-before | Good middle ground |

**Agent Coordination Scenarios**:
1. **Handoff**: Agent A completes, Agent B starts → Sequential, no conflict
2. **Parallel work**: Agents A & B work simultaneously → May conflict
3. **Observation**: Agent A watches Agent B's progress → Staleness acceptable

### Expert Assessment

For agent coordination:
- **Strong consistency** rarely needed (agents aren't databases)
- **Eventual consistency** acceptable for most workflows
- **Causal consistency** ideal for task dependencies

Most agent interactions are **naturally sequential** (delegation chains), reducing consistency concerns.

### Recommendation: **ADD**

Explicitly declare consistency model in spec.

### Spec Amendment

> [!NOTE]
> Added to Section 5: ASAP uses **causal consistency** for task state. Agents observing a task see updates in causal order (a task cannot be "completed" before it was "working"). Implementations MAY offer stronger guarantees. Cross-agent state sharing uses eventual consistency with version vectors for conflict detection.

---

## Question 13: State Management Strategy for Marketplace

### The Question
The v0 spec lists "First-class persistent state with snapshots" as a key design goal. The `SnapshotStore` Protocol and `InMemorySnapshotStore` exist in v1.0, but no persistent implementation or storage interface specification exists. As we build toward the Marketplace (v2.0), what is ASAP's responsibility regarding agent state persistence?

### Analysis

**Three scenarios evaluated**:

| Scenario | Description | Scalability | Lock-in | Engineering Cost |
|----------|-------------|-------------|---------|-----------------|
| **A: State-as-a-Service** | ASAP stores all agent state centrally | Poor (storage grows with adoption) | Maximum | Massive (distributed DB, multi-tenant) |
| **B: Communication Only** | ASAP is "just the pipe", agents own state | Excellent | Minimal | Low |
| **C: Hybrid** | ASAP defines interface + reference impls; Marketplace stores metadata only | Good | Low (portable interfaces) | Moderate |

**Scenario A risks**:
- Single point of failure for the entire ecosystem
- Data sovereignty/compliance burden (GDPR, HIPAA) — ASAP becomes data processor
- Contradicts "adoption first" strategy (high infrastructure cost)
- Incompatible with solo/small team execution

**Scenario B risks**:
- v1.3 Observability & Delegation Layer (metering, delegation) becomes unfunded mandate
- Reputation scores are shallow without historical data
- Usage metering relies on agent self-reporting (gameable)
- Each agent reinvents storage — poor DX

**Scenario C advantages**:
- `SnapshotStore` Protocol already exists in codebase — extend, don't rebuild
- Reference implementations (SQLite, Redis) reduce adoption friction
- Marketplace stores only metadata (manifests, trust scores, SLA metrics)
- ASAP Cloud (v2.0+ monetization) offers managed storage as premium upsell
- Agents choose their storage backend — no lock-in

### Expert Assessment

Scenario C aligns with the project's DNA: the `SnapshotStore` Protocol pattern in `src/asap/state/snapshot.py` already defines the abstract interface. What's missing is:
1. **Persistent reference implementations** (SQLite for dev, Redis/Postgres for prod)
2. **A `MeteringStore` interface** for v1.3 usage tracking
3. **Clear documentation** of what ASAP stores centrally vs what agents own

The v0 spec Section 13.2 recommended "Option 2 (interface) for interoperability" — this decision formalizes that recommendation.

### Recommendation: **HYBRID (Scenario C)**

Adopt a layered storage strategy:

| Layer | Data | Owner | Storage |
|-------|------|-------|---------|
| **Protocol Interface** | `SnapshotStore`, `MeteringStore` | ASAP SDK (open source) | Agent's choice |
| **Reference Impls** | SQLite, Redis, PostgreSQL adapters | Separate packages | Agent's infra |
| **Marketplace Metadata** | Manifests, trust scores, SLA metrics | ASAP centrally | Lite Registry (v2.0), PostgreSQL (v2.1+) |
| **Agent Task State** | Snapshots, event history, artifacts | Agent developer | Agent's choice |
| **ASAP Cloud** (future) | Managed storage, backups | ASAP premium | Managed infra |

### Decision

> [!IMPORTANT]
> **ADR-13**: State Management follows a **Hybrid strategy (Scenario C)**. ASAP defines storage interfaces (`SnapshotStore`, `MeteringStore`) and provides reference implementations as separate packages. Agent task state is the agent developer's responsibility. Marketplace metadata (registry, trust, SLA) is managed centrally by ASAP. ASAP Cloud (v2.0+) may offer managed storage as a premium feature.
>
> **Rationale**: Balances developer experience (reference impls reduce friction) with adoption strategy (no lock-in, no data sovereignty burden). Extends the existing `SnapshotStore` Protocol pattern already in v1.0 codebase.
>
> **Impact**: v1.1.0 adds SQLite reference implementation and defines `MeteringStore` interface. v1.3.0 Observability Layer references these interfaces. v2.0 ASAP Cloud may offer managed storage.
>
> **Date**: 2026-02-07

---

## Question 14: Agent Liveness & Health Protocol

### The Question
The vision document describes "Availability Check: Real-time capacity and queue status" in the Discovery Service. No version in the roadmap defines a health/liveness protocol for agents. Without it, the Registry (v1.2) will show stale/dead agents.

### Analysis

**The problem without liveness**:
- Discovery (v1.1) returns manifests from well-known URIs, but cannot tell if the agent is alive
- Registry (v1.2) lists agents that may have crashed, creating a "graveyard" of stale entries
- Reputation System (v2.0) calculates uptime without a measurement mechanism
- SLA Framework (v1.3) defines `availability: "99.5%"` without a way to verify

**Industry patterns**:
- Kubernetes: `/healthz` (liveness), `/readyz` (readiness)
- A2A: No standard health check
- MCP: No health protocol

**Proposed approach**:
- `GET /.well-known/asap/health` — simple JSON response with status and capabilities
- `ttl` field in manifest — how long to consider the agent "alive" without re-check
- Minimal: no heavy health framework, just HTTP endpoint + TTL

### Recommendation: **ADD to v1.1.0**

Add as part of Sprint S2 (Discovery), since it's a natural extension of the well-known endpoint.

### Decision

> [!IMPORTANT]
> **ADR-14**: Agents SHOULD expose a `GET /.well-known/asap/health` endpoint returning a simple JSON status. Manifests SHOULD include a `ttl_seconds` field (default: 300) indicating how long the agent can be considered alive without re-checking. This is foundational for Registry liveness (v1.2) and SLA monitoring (v1.3).
>
> **Rationale**: Without liveness, the Registry becomes a graveyard of stale agents. A simple health endpoint is low-cost to implement and provides high value for the discovery and trust layers.
>
> **Impact**: Added to Sprint S2 (Well-Known Discovery) in v1.1.0.
>
> **Date**: 2026-02-07
