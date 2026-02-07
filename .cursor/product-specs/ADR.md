# ASAP Protocol: Critical Analysis & Design Decisions

> Expert self-review identifying unclear points, analyzing trade-offs, and documenting decisions.

## Table of Contents

- [Analysis Methodology](#analysis-methodology)
- [Question 1: Is Event-Sourced State Necessary for MVP?](#question-1-is-event-sourced-state-necessary-for-mvp)
- [Question 2: Why JSON-RPC Over REST for Primary Binding?](#question-2-why-json-rpc-over-rest-for-primary-binding)
- [Question 3: Is Peer-to-Peer Default Practical?](#question-3-is-peer-to-peer-default-practical)
- [Question 4: What Consistency Model for Shared State?](#question-4-what-consistency-model-for-shared-state)
- [Question 5: Is MCP Envelope Approach Optimal?](#question-5-is-mcp-envelope-approach-optimal)
- [Question 6: Is CalVer Appropriate for Protocol Versioning?](#question-6-is-calver-appropriate-for-protocol-versioning)
- [Question 7: Is Error Model Complete?](#question-7-is-error-model-complete)
- [Question 8: Is MVP Security Sufficient?](#question-8-is-mvp-security-sufficient)
- [Question 9: Should Any Module Use C or Rust?](#question-9-should-any-module-use-c-or-rust)
- [Question 10: Build vs Buy for Agent Evals?](#question-10-build-vs-buy-for-agent-evals)
- [Question 11: What Tech Stack for v2.0 Web Marketplace?](#question-11-what-tech-stack-for-v20-web-marketplace)
- [Question 12: Authlib vs httpx-oauth for OAuth2/OIDC](#question-12-authlib-vs-httpx-oauth-for-oauth2oidc)
- [Question 13: State Management Strategy for Marketplace](#question-13-state-management-strategy-for-marketplace)
- [Question 14: Agent Liveness & Health Protocol](#question-14-agent-liveness--health-protocol)
- [Question 15: Lite Registry for v1.1 Discovery Gap](#question-15-lite-registry-for-v11-discovery-gap)
- [Question 16: WebSocket Message Acknowledgment](#question-16-websocket-message-acknowledgment)
- [Question 17: Trust Model and Identity Binding in v1.1](#question-17-trust-model-and-identity-binding-in-v11)
- [Summary of Amendments](#summary-of-amendments)
- [Next Steps](#next-steps)

---

## Analysis Methodology

As an expert in agentic architecture, I'll examine the ASAP specification through these lenses:
1. **Consistency Model** – Event-sourced vs simpler alternatives
2. **Transport Binding** – JSON-RPC priority vs alternatives  
3. **Topology Assumptions** – P2P default viability
4. **State Semantics** – Strong vs eventual consistency
5. **MCP Integration** – Envelope approach vs deeper integration
6. **Versioning Strategy** – CalVer implications
7. **Error Handling** – Completeness of error model
8. **Security Model** – MVP adequacy

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

## Question 2: Why JSON-RPC Over REST for Primary Binding?

### The Question
The spec recommends HTTP + JSON-RPC as the canonical binding (Section 13.1). Is this the right choice given REST's ubiquity?

### Analysis

| Criterion | JSON-RPC | REST | gRPC |
|-----------|----------|------|------|
| A2A/MCP alignment | ✅ Native match | ❌ Paradigm mismatch | ⚠️ Partial (A2A supports) |
| Browser support | ✅ Full | ✅ Full | ❌ Requires proxy |
| Streaming | ⚠️ Needs SSE/WS | ⚠️ Needs SSE/WS | ✅ Native |
| Method semantics | ✅ Explicit methods | ⚠️ Resource-oriented | ✅ Explicit methods |
| Schema validation | ⚠️ Manual | ⚠️ OpenAPI | ✅ Protobuf |
| Performance | Medium | Medium | High |
| Learning curve | Low | Very low | Medium-high |

### Expert Assessment

**Why JSON-RPC wins for ASAP**:
1. **A2A compatibility**: A2A uses JSON-RPC 2.0; alignment reduces bridging friction
2. **Method-centric**: Agents think in terms of "actions" (TaskRequest, TaskCancel), not "resources"
3. **Simpler async semantics**: JSON-RPC's request/response model maps cleanly to our async patterns
4. **MCP consistency**: MCP also uses JSON-RPC

**Why not REST**:
- Resource-oriented design feels forced for agent coordination
- Mapping task state machines to HTTP verbs (GET/PUT/PATCH) is awkward
- Over-fetching/under-fetching issues irrelevant for structured agent messages

**Why defer gRPC**:
- Adds Protobuf toolchain requirement
- Limited browser support complicates demos/debugging
- Performance gains matter less than adoption barriers for MVP

### Recommendation: **KEEP**

JSON-RPC is the correct choice. Add explicit rationale to spec.

### Spec Amendment

> [!NOTE]
> Added to Section 13.1: JSON-RPC selected for A2A/MCP ecosystem alignment and method-centric semantics that match agent interaction patterns. gRPC binding deferred to v0.2 for performance-critical deployments.

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

## Question 5: Is MCP Envelope Approach Optimal?

### The Question
Section 8 wraps MCP calls in ASAP envelopes (`McpToolCall`, `McpToolResult`). Is this the right integration pattern?

### Analysis

**Integration Patterns Considered**:

| Pattern | Description | Pros | Cons |
|---------|-------------|------|------|
| **Envelope** (current) | ASAP wraps MCP | Clean separation, routing flexibility | Extra layer, translation overhead |
| **Passthrough** | Forward MCP unchanged | Zero overhead | Loses ASAP tracing/correlation |
| **Unified** | Merge into single protocol | Simplest conceptually | Massive spec, A2A/MCP conflict |
| **Sidecar** | MCP as separate channel | Independent scaling | Coordination complexity |

### Expert Assessment

**Envelope approach is correct because**:
1. **Correlation**: ASAP envelope carries `trace_id`, `correlation_id`
2. **Routing**: ASAP handles agent-to-agent routing; MCP handles tool execution
3. **Auth boundary**: ASAP auth may differ from MCP tool auth
4. **Observability**: Unified logging across both protocols

**Edge case concern**: What if MCP tool returns large binary data?

### Recommendation: **KEEP with clarification**

Add streaming support for large MCP responses.

### Spec Amendment

> [!NOTE]
> Added to Section 8.2: For large MCP tool results, the `McpToolResult` payload MAY contain a `stream_uri` instead of inline `result`, enabling chunked delivery via ASAP streaming mechanisms.

---

## Question 6: Is CalVer Appropriate for Protocol Versioning?

### The Question
Section 9.3 proposes CalVer (2025.01 format). Is this suitable for a protocol spec?

### Analysis

**Versioning Strategies**:

| Strategy | Example | When to Use |
|----------|---------|-------------|
| **SemVer** | 1.2.3 | Breaking change clarity |
| **CalVer** | 2025.01 | Time-based releases |
| **Hybrid** | 1.2025.01 | Both dimensions |

**Industry Practice**:
- HTTP: Version numbers (1.0, 1.1, 2, 3)
- JSON-RPC: 2.0 (static for 15+ years)
- GraphQL: No versioning (evolved carefully)
- MCP: Date-based (2025-11-25)
- A2A: Semantic-ish (v1.0 DRAFT)

### Expert Assessment

**CalVer advantages**:
- Communicates recency (2025.06 obviously newer than 2024.01)
- Encourages regular spec reviews
- Aligns with MCP's date-based approach

**CalVer disadvantages**:
- Doesn't communicate breaking vs non-breaking
- May create pressure for unnecessary annual changes
- Protocol users prefer stability signals

### Recommendation: **MODIFY**

Adopt **hybrid approach**: Major.CalVer

```
Format: <major>.<YYYY>.<MM>
Examples:
  1.2025.01 – Initial stable release
  1.2025.06 – Additive update
  2.2026.01 – Breaking changes
```

### Spec Amendment

> [!NOTE]
> Modified Section 9.3: Adopted hybrid versioning `Major.YYYY.MM`. Major version indicates breaking changes; CalVer portion indicates release timing. v1.2025.01 is target for first stable release.

---

## Question 7: Is Error Model Complete?

### The Question
Section 13.4 mentions namespaced error codes but doesn't define core errors. Is the error model complete?

### Analysis

**Essential Error Categories**:
1. **Protocol errors** (malformed messages)
2. **Routing errors** (agent not found)
3. **Capability errors** (skill not available)
4. **Execution errors** (task failed)
5. **Resource errors** (quota exceeded)
6. **Security errors** (auth failed)

**A2A Error Codes** (for reference):
- `ContentTypeNotSupportedError`
- `UnsupportedOperationError`
- `TaskNotFoundError`
- `InvalidRequestError`

### Recommendation: **ADD**

Define core error taxonomy.

### Spec Amendment

> [!NOTE]
> Added Error Taxonomy to spec:

```
Core Error Codes:
├── asap:protocol
│   ├── malformed_envelope
│   ├── invalid_payload_type
│   └── version_mismatch
├── asap:routing
│   ├── agent_not_found
│   ├── agent_unreachable
│   └── conversation_expired
├── asap:capability
│   ├── skill_not_found
│   ├── skill_unavailable
│   └── input_validation_failed
├── asap:execution
│   ├── task_failed
│   ├── task_timeout
│   └── task_cancelled
├── asap:resource
│   ├── quota_exceeded
│   ├── rate_limited
│   └── storage_full
└── asap:security
    ├── auth_required
    ├── auth_invalid
    └── permission_denied
```

---

## Question 8: Is MVP Security Sufficient?

### The Question
Section 10.1 defines MVP security (TLS, bearer tokens, scopes). Is this adequate for initial deployments?

### Analysis

**Threat Assessment for MVP**:

| Threat | MVP Mitigation | Gap |
|--------|----------------|-----|
| Eavesdropping | TLS 1.3 | ✅ Covered |
| Replay attacks | Idempotency keys | ⚠️ Keys expire, not cryptographic |
| Spoofing | Bearer tokens | ⚠️ Token theft risk |
| Man-in-middle | TLS | ✅ Covered |
| Privilege escalation | Scopes | ⚠️ Scope enforcement in spec, not protocol |

**Industry Baseline** (2025):
- mTLS becoming standard for service-to-service
- Signed JWTs preferred over opaque tokens
- Zero-trust architecture expected for enterprise

### Expert Assessment

**MVP security is adequate IF**:
- Deployments are within trust boundaries
- Network security complements protocol security
- Token management follows best practices

**Upgrade urgency**:
- Signed messages: High (v0.2)
- mTLS: Medium (v0.3)
- Zero-trust: Low (v1.1)

### Recommendation: **KEEP with enhancement**

Add HMAC-signed request bodies as optional MVP feature.

### Spec Amendment

> [!NOTE]
> Added to Section 10.1: Optional request signing via `X-ASAP-Signature` header using HMAC-SHA256. Enables integrity verification without full PKI. Recommended for production deployments.

---

## Question 9: Should Any Module Use C or Rust?

### The Question
Would any ASAP module benefit from being implemented in C or Rust instead of pure Python for performance reasons?

### Analysis

**Module Assessment**:

| Module | Performance Needs | Current Solution |
|--------|------------------|------------------|
| Models/Schemas | JSON parsing, validation | `pydantic-core` (Rust) ✅ |
| State Machine | Simple transitions | Pure Python sufficient |
| Snapshot Store | I/O bound | Async I/O, no CPU bottleneck |
| HTTP Transport | Network I/O | `uvloop` (C), `httpx` (optimized) ✅ |
| JSON-RPC | Serialization | `orjson` available (Rust) ✅ |
| ULID Generation | ID creation | `python-ulid` 3.0 (Rust) ✅ |

**Key Insight**: Critical performance paths already use Rust/C internally via our dependencies.

### Expert Assessment

**ASAP is I/O bound, not CPU bound**:
- Agent communication is network-limited
- JSON serialization is already Rust-optimized (pydantic-core, orjson)
- Async event loop uses libuv (C) via uvloop

**Cost of custom C/Rust**:
- Build complexity (manylinux, macOS, Windows wheels)
- Debugging difficulty across FFI boundaries
- Maintenance burden for bindings

**When C/Rust would matter (future)**:
- Cryptographic signing of manifests at scale
- Binary protocol (Protobuf/MessagePack)
- Native message broker clients

### Recommendation: **KEEP Pure Python**

Leverage Rust-based dependencies; avoid custom native extensions for MVP.

### Spec Amendment

> [!NOTE]
> Added architectural decision: ASAP SDK uses pure Python with Rust-accelerated dependencies (pydantic-core, orjson, python-ulid). Custom C/Rust extensions deferred until profiling identifies specific bottlenecks. This maximizes developer accessibility while maintaining competitive performance.

---

## Question 10: Build vs Buy for Agent Evals?

### The Question
Should ASAP build a custom native evaluation framework or integrate with existing market solutions (DeepEval, Ragas, Arize)?

### Analysis

| Approach | Pros | Cons |
|----------|------|------|
| **Build (Native)** | Total control, strict protocol alignment | High effort, reinventing LLM metrics wheel |
| **Buy/Integrate** | Immediate SOTA metrics, community maintenance | Dependency risk, "black box" logic |

### Expert Assessment

**Hybrid Strategy ("Shell vs Brain")**:
- **Protocol Compliance (Shell)**: MUST be native. We cannot rely on third parties to validate our specific binary formats, state transitions, or schemas.
- **Intelligence (Brain)**: SHOULD be delegated. Metrics like "Hallucination" or "Coherence" are commoditized and complex to maintain.

### Recommendation: **HYBRID**

Use **DeepEval** (Open Source) as the standard library for Intelligence Evals. Build a lightweight **ASAP Compliance Harness** using `pytest` for Protocol Evals.

### Spec Amendment

> [!NOTE]
> Added to Vision (Section 4): Adopted Hybrid Evaluation Strategy. Protocol Compliance is internal (Shell); Intelligence Evaluation is external via DeepEval (Brain).

---

## Question 12: Authlib vs httpx-oauth for OAuth2/OIDC

### The Question
The initial v1.1.0 plan specified `httpx-oauth` as the OAuth2 dependency. During implementation, we discovered it does **not** support the `client_credentials` grant (the primary flow for agent-to-agent auth). Should we keep httpx-oauth, use raw httpx, or switch to a more comprehensive library?

### Analysis

**Libraries Evaluated** (February 2026):

| Library | client_credentials | JWKS/JWT | OIDC Discovery | Async httpx | Downloads/mo | Status |
|---------|-------------------|----------|----------------|------------|-------------|--------|
| **Authlib** | Native | Via `joserfc` (same author) | Native | `AsyncOAuth2Client` | ~45M | Active (v1.6.6, v1.7 in dev) |
| **httpx-oauth** | **Not supported** | No | Partial (OpenID client) | Yes | Lower | Focused on authorization_code |
| **joserfc** | N/A (JOSE only) | **Complete** (JWS, JWE, JWK) | N/A | N/A | Growing | Active (v1.6.1, Dec 2025) |
| **PyJWT** | N/A (JWT only) | Partial | No | N/A | ~200M+ | Active |
| **Raw httpx** | Manual | Manual | Manual | Yes | — | We maintain |

**httpx-oauth limitations discovered**:
1. No `client_credentials` grant — only `authorization_code` flow
2. No JWT validation or JWKS fetching
3. No OIDC discovery
4. Would require manual implementation for all three Sprint S1 tasks

**Authlib advantages**:
1. **Single dependency** covers Tasks 1.1, 1.2, and 1.3 entirely
2. `AsyncOAuth2Client` with native `client_credentials` support
3. `joserfc` (same author, same org) provides modern JWS/JWE/JWK/JWT
4. Built-in OIDC discovery from `.well-known/openid-configuration`
5. FastAPI/Starlette integration available
6. 45M downloads/month, BSD-3-Clause license (compatible with Apache-2.0)
7. Active maintenance: v1.7 in development, last updated Jan 2026

**Risk assessment**:
- Authlib is a broader library than needed, but unused features have zero runtime cost
- `joserfc` replaces abandoned `python-jose` as the modern JOSE standard
- httpx integration note says "alpha" (legacy doc label, library is stable in practice)

### Expert Assessment

The original plan chose httpx-oauth based on its httpx alignment. In practice, it only solves authorization_code flows for web apps (Google, GitHub, etc.), not machine-to-machine auth. Keeping it would mean:
- Building client_credentials manually (done partially in Task 1.1.3)
- Building JWKS validation manually (Task 1.3.2)
- Building OIDC discovery manually (Task 1.3.1)
- Maintaining ~500+ lines of security-critical code ourselves

Authlib eliminates all three while providing a battle-tested, widely-adopted foundation.

### Recommendation: **REPLACE**

Replace `httpx-oauth` with `authlib` as the OAuth2/OIDC dependency. Additionally, add `joserfc` for JWT/JWKS validation (Tasks 1.2, 1.3).

### Decision

> [!IMPORTANT]
> **ADR-12**: Replaced `httpx-oauth>=0.13` with `authlib>=1.3` and `joserfc>=1.0` in v1.1.0 dependencies.
>
> **Rationale**: httpx-oauth does not support `client_credentials` (the primary agent-to-agent flow). Authlib provides native support for all three Sprint S1 requirements (OAuth2 client, token validation, OIDC discovery) as a single, well-maintained dependency. `joserfc` (same author) provides modern JOSE/JWT support, replacing the abandoned `python-jose`.
>
> **Impact**: Tasks 1.1, 1.2, and 1.3 updated to use Authlib's `AsyncOAuth2Client` and joserfc for JWT operations. The ASAP-specific `Token` model and `OAuth2ClientCredentials` wrapper remain as our public API, with Authlib as the internal engine.
>
> **Date**: 2026-02-07

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
- v1.3 Economics Layer (metering, audit) becomes unfunded mandate
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
| **Marketplace Metadata** | Manifests, trust scores, SLA metrics | ASAP centrally | PostgreSQL (v2.0) |
| **Agent Task State** | Snapshots, event history, artifacts | Agent developer | Agent's choice |
| **ASAP Cloud** (future) | Managed storage, backups | ASAP premium | Managed infra |

### Decision

> [!IMPORTANT]
> **ADR-13**: State Management follows a **Hybrid strategy (Scenario C)**. ASAP defines storage interfaces (`SnapshotStore`, `MeteringStore`) and provides reference implementations as separate packages. Agent task state is the agent developer's responsibility. Marketplace metadata (registry, trust, SLA) is managed centrally by ASAP. ASAP Cloud (v2.0+) may offer managed storage as a premium feature.
>
> **Rationale**: Balances developer experience (reference impls reduce friction) with adoption strategy (no lock-in, no data sovereignty burden). Extends the existing `SnapshotStore` Protocol pattern already in v1.0 codebase.
>
> **Impact**: v1.1.0 adds SQLite reference implementation and defines `MeteringStore` interface. v1.3.0 Economics Layer references these interfaces. v2.0 ASAP Cloud may offer managed storage.
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

---

## Question 15: Lite Registry for v1.1 Discovery Gap

### The Question
v1.1 introduces agent identity (OAuth2) and direct discovery (`.well-known`), but defers the Registry API to v1.2. This creates a "Discovery Abyss" — agents have identity but no one can find them unless they already know the URL. How do we bridge this gap without building the full Registry early?

### Analysis

**The problem**: In v1.1, the network effect is zero. A developer can build and authenticate an agent, but there's no central place to list or discover agents. The "Marketplace" story feels hollow until v1.2.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| **Static JSON on GitHub Pages** | ✅ Selected | Zero infrastructure, PR-based social proof, machine-readable |
| DNS-based discovery | Rejected | Complex for developers, no browsing/search capability |
| Do nothing | Rejected | Kills early adoption momentum |

### Expert Assessment

A static `registry.json` hosted on GitHub Pages mirrors patterns that worked well in the Go ecosystem (before `proxy.golang.org`) and `awesome-*` lists. Developers submit agents via PR, creating community engagement and quality control through code review. The v1.2 Registry API can seed itself from this file.

**Critical refinement**: Since v1.1 introduces WebSocket alongside HTTP, agents may have multiple endpoints. The schema must support a `endpoints` dict (not a single `url` string).

### Decision

> [!IMPORTANT]
> **ADR-15**: Bridge the v1.1 "Discovery Abyss" with a **Static Lite Registry** — a `registry.json` file hosted on GitHub Pages. Agents are listed via PR. The SDK provides a `discover_from_registry(registry_url)` method.
>
> **Schema** (multi-endpoint):
> ```json
> {
>   "version": "1.0",
>   "updated_at": "2026-02-07T00:00:00Z",
>   "agents": [
>     {
>       "id": "urn:asap:agent:example",
>       "name": "Example Agent",
>       "description": "Code review and summarization agent",
>       "endpoints": {
>         "http": "https://agent.example.com/asap",
>         "ws": "wss://agent.example.com/asap/ws",
>         "manifest": "https://agent.example.com/.well-known/asap/manifest.json"
>       },
>       "skills": ["code_review", "summarization"],
>       "asap_version": "1.1.0"
>     }
>   ]
> }
> ```
>
> **Rationale**: Zero-cost infrastructure, creates early community engagement, and provides a migration path to the v1.2 Registry API. Multi-endpoint schema supports HTTP + WebSocket transports introduced in v1.1.
>
> **Impact**: Added as Task in Sprint S2 (Well-Known Discovery). SDK method added to `ASAPClient`.
>
> **Date**: 2026-02-07

---

## Question 16: WebSocket Message Acknowledgment

### The Question
WebSocket is fire-and-forget at the transport level. HTTP has implicit acks (response = received), but WebSocket does not. If an agent crashes mid-message, the sender never knows. How do we ensure reliable delivery for state-changing messages over WebSocket?

### Analysis

**The problem**: Without application-level acknowledgment, WebSocket provides "at-most-once" delivery. For state-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`), this is insufficient — a lost message could leave the task state machine in an inconsistent state.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| Full ack for all messages | Rejected | Doubles traffic, overkill for streaming/progress |
| Auto-ack for all WebSocket messages | Rejected | Same traffic doubling issue |
| **Ack only for state-changing messages** | ✅ Selected | Balanced: critical messages reliable, streaming fast |
| Defer to v1.2 | Rejected | May disappoint enterprise users expecting reliability |

### Expert Assessment

State-changing messages (`TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`) MUST be acknowledged — they affect the task state machine. Streaming updates (`TaskUpdate` with `progress`) and heartbeats do NOT need acks — they're ephemeral. This aligns with existing `correlation_id` field in Envelope.

**Critical addition**: The `MessageAck` payload is useless without an `AckAwareClient` that manages the timeout/retry loop. The client must track pending acks, retransmit on timeout (using same `id` for idempotency), and integrate with the circuit breaker for max retries.

### Decision

> [!IMPORTANT]
> **ADR-16**: Add **selective message acknowledgment** for WebSocket transport. State-changing payloads automatically set `requires_ack=True`. Receiver responds with `MessageAck` payload referencing the original `envelope_id`.
>
> **Components**:
> 1. `MessageAck` payload type with `original_envelope_id` and `status` fields
> 2. `requires_ack: bool = False` field on Envelope (auto-set for state-changing payloads over WebSocket)
> 3. `AckAwareClient` that manages timeout/retry loop:
>    - Tracks pending acks with configurable timeout (default: 30s)
>    - On timeout: retransmits same message with same `id` (idempotency key ensures safety)
>    - Configurable max retries before circuit breaker trips
> 4. HTTP transport continues to use synchronous response as implicit ack
>
> **Payloads requiring ack**: `TaskRequest`, `TaskCancel`, `StateRestore`, `MessageSend`
> **Payloads NOT requiring ack**: `TaskUpdate` (progress), heartbeats, streaming
>
> **Rationale**: Balances reliability for critical messages with performance for streaming. Idempotency keys make retransmission safe. The `AckAwareClient` is essential — without it, the ack protocol defines behavior but nothing enforces it.
>
> **Impact**: Added as Tasks in Sprint S3 (WebSocket Binding).
>
> **Date**: 2026-02-07

---

## Question 17: Trust Model and Identity Binding in v1.1

### The Question
OAuth2 (v1.1) proves "I have valid credentials from an IdP", but NOT "I am the agent I claim to be". Without signed manifests (v1.2), how do we prevent agent impersonation? And how do we bind JWT identity to ASAP agent identity given that IdP subject IDs (`google-oauth2|12345`) don't match agent IDs (`urn:asap:agent:bot`)?

### Analysis

**The trust gap**: v1.1 OAuth2 provides authentication and authorization (scopes), but not identity verification. This is the SAME trust model as every web API today — OAuth2 is equivalent to API keys with scopes. The real identity verification comes in v1.2 with Ed25519 signed manifests.

**The identity mapping problem**: IdP-generated `sub` claims (e.g., `google-oauth2|12345`, `auth0|abc123`) will never match ASAP `agent_id` values (e.g., `urn:asap:agent:research-v1`). A strict `sub == agent_id` binding is impossible in practice.

**Options evaluated**:

| Option | Considered | Rationale |
|--------|------------|-----------|
| Accept and document explicitly | ✅ Selected (part 1) | Honest, sets expectations, no false security |
| **Custom Claims binding** | ✅ Selected (part 2) | Flexible, portable, standard JWT practice |
| Strict sub == agent_id | Rejected | Impossible with standard IdPs |
| Accelerate Ed25519 to v1.1 | Rejected | Scope creep, v1.1 already has 5 sprints |

### Expert Assessment

**Custom Claims** is the most flexible solution: agents configure their IdP to include `https://asap.ai/agent_id` as a custom claim in the JWT. The ASAP server validates this claim matches the requesting agent's manifest `id`. For environments where custom claims aren't possible, a configurable allowlist mapping (`ASAP_AUTH_SUBJECT_MAP`) provides a fallback.

### Decision

> [!IMPORTANT]
> **ADR-17**: v1.1 Trust Model uses **Custom Claims binding** for identity mapping, with explicit documentation of security limitations.
>
> **Identity Binding** (two approaches, both supported):
> 1. **Custom Claims** (recommended): Agent configures IdP to include `https://asap.ai/agent_id: urn:asap:agent:bot` in JWT. Server validates claim matches manifest `id`.
> 2. **Allowlist fallback**: `ASAP_AUTH_SUBJECT_MAP = {"urn:asap:agent:bot": "auth0|abc123"}` for environments without custom claims support.
>
> **Security Model documentation**:
> - v1.1 provides authentication (valid credentials) and authorization (scopes), but NOT identity verification
> - For agent identity verification, use v1.2 signed manifests (Ed25519)
> - This mirrors industry practice: OAuth2 for auth, PKI for identity, incrementally layered
>
> **Rationale**: Custom Claims are portable (work across IdPs), standards-based (RFC 7519 allows private claims), and more flexible than hardcoded config. The allowlist fallback covers edge cases. Explicit security documentation prevents false expectations.
>
> **Impact**: Custom Claims validation added as sub-task in Sprint S1. Security Model documentation added to Sprint S4 release materials.
>
> **Date**: 2026-02-07

---

## Summary of Amendments

| Question | Decision | Change Type |
|----------|----------|-------------|
| Q1: Event-sourced state | Make optional, default to snapshots | **Modified** |
| Q2: JSON-RPC binding | Keep, add explicit rationale | **Kept + Documented** |
| Q3: P2P topology | Remove as default, add deployment patterns | **Modified** |
| Q4: Consistency model | Add explicit causal consistency | **Added** |
| Q5: MCP envelope | Keep, add streaming for large results | **Kept + Enhanced** |
| Q6: CalVer versioning | Adopt hybrid Major.CalVer | **Modified** |
| Q7: Error model | Add complete error taxonomy | **Added** |
| Q8: MVP security | Add optional request signing | **Enhanced** |
| Q9: Python vs C/Rust | Keep pure Python, use Rust deps | **Documented** |
| Q10: Agent Evals | Hybrid: Native Compliance + DeepEval | **Added** |
| Q11: Web Stack | Next.js, Tailwind, Shadcn | **Added** |
| Q12: OAuth2 Lib | Replace httpx-oauth with Authlib + joserfc | **Replaced** |
| Q13: State Management | Hybrid: Interface + Reference Impls + Managed | **Added** |
| Q14: Agent Liveness | Health endpoint + TTL in manifest | **Added** |
| Q15: Lite Registry | Static JSON on GitHub Pages, multi-endpoint schema | **Added** |
| Q16: WebSocket Acks | Selective ack for state-changing messages + AckAwareClient | **Added** |
| Q17: Trust Model | Custom Claims binding + allowlist fallback + security docs | **Added** |

---

## Next Steps

1. ✅ Questions analyzed (Q1-Q17)
2. ✅ Decisions documented
3. ⏳ Apply amendments to main specification
4. ⏳ Request user review of changes

