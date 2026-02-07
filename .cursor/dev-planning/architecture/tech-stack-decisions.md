# ASAP Protocol: Technology Stack & Architecture Decisions

This document provides a historical and technical rationale for the technology choices made throughout the evolution of the ASAP Protocol, from its core (v1.0) to the Marketplace (v2.0).

> **Goal**: Explain *why* we chose these tools, offering context for future contributors and architects.
>
> **Last Updated**: 2026-02-07 (strategic review)

---

## 1. Core Protocol (v1.0 - "Foundation")

The foundation required stability, developer experience (DX), and strict correctness.

### 1.1 Language: Python 3.13+
-   **Decision**: **Python**
-   **Rationale**:
    -   **AI Native**: The primary audience for Agentic Protocols are AI engineers, who predominantly use Python.
    -   **Sync/Async**: Python's `asyncio` is mature enough for high-concurrency IO-bound tasks (agents waiting on LLMs).
    -   **Ecosystem**: Unrivaled libraries for LLM integration (LangChain, OpenAI, Pydantic).
-   **Why strict typing?**: We enforce `mypy` strict mode because protocols cannot be ambiguous. Python 3.13+ brings massive performance wins and better type hints.
-   **Why not Rust/Go?**: ASAP is I/O-bound, not CPU-bound. Critical performance paths already use Rust internally via dependencies (pydantic-core, orjson). Custom native extensions deferred until profiling identifies specific bottlenecks. See [ADR-9](../../product-specs/ADR.md#question-9-should-any-module-use-c-or-rust).

### 1.2 Data Core: Pydantic v2
-   **Decision**: **Pydantic**
-   **Rationale**:
    -   **Validation as Schema**: It defines the protocol schema (Models) and validator (Runtime) in one place.
    -   **Performance**: v2 is written in Rust, offering near-native serialization speeds.
    -   **JSON Schema**: Auto-generates standard JSON Schemas for interoperability with non-Python agents.

### 1.3 Communication: JSON-RPC 2.0
-   **Decision**: **JSON-RPC** over REST
-   **Rationale**:
    -   **Action-Oriented**: Agents perform *actions* (TaskRequest, TaskCancel), not just resource manipulation (GET/POST).
    -   **Transport Agnostic**: JSON-RPC works equally well over HTTP, WebSockets, or stdio (MCP).
    -   **Standard**: It is a stable, boring standard. Agents don't need creative URL schemes.
-   **Alternatives rejected**: REST (paradigm mismatch for agent actions), gRPC (limited browser support, heavier tooling). See [ADR-2](../../product-specs/ADR.md#question-2-why-json-rpc-over-rest-for-primary-binding).

### 1.4 API Framework: FastAPI
-   **Decision**: **FastAPI**
-   **Rationale**:
    -   **Native Pydantic**: Seamless integration with our data core.
    -   **Async First**: Built on `Starlette`/`AnyIO`, critical for handling thousands of concurrent agent connections.
    -   **Doc Generation**: Auto-generates OpenAPI specs, helping developers visualize the protocol endpoints.

---

## 2. Identity & Transport (v1.1 - "Connectivity")

Focus shifted to secure, real-time communication and persistent state.

### 2.1 Authentication: OAuth2 with JWT
-   **Decision**: **OAuth2 (Client Credentials Flow)**
-   **Rationale**:
    -   **Machine-to-Machine**: Agents are headless service accounts. Client Credentials is the standard for M2M.
    -   **Stateless**: JWTs allow signature verification without hitting a database for every request (performance).
    -   **Scopes**: Fine-grained permissions (`task:create`, `agent:read`) baked into the standard.

### 2.2 OAuth2 Library: Authlib + joserfc
-   **Decision**: **Authlib** (replacing httpx-oauth)
-   **Rationale**:
    -   **client_credentials**: httpx-oauth only supports `authorization_code` flow (web apps). Authlib natively supports `client_credentials` (the primary agent-to-agent flow).
    -   **Single dependency**: Authlib covers OAuth2 client, token validation, and OIDC discovery — all three Sprint S1 requirements.
    -   **joserfc**: Modern JOSE/JWT library (same author as Authlib), replaces abandoned `python-jose`. Provides JWS/JWE/JWK/JWT.
    -   **Maturity**: 45M downloads/month, BSD-3-Clause, active maintenance (v1.7 in dev).
-   **Alternatives rejected**: httpx-oauth (no client_credentials), raw httpx (500+ lines of security-critical code to maintain), PyJWT (JWT only, no OIDC).
-   **Reference**: [ADR-12](../../product-specs/ADR.md#question-12-authlib-vs-httpx-oauth-for-oauth2oidc)

### 2.3 Real-time: WebSockets
-   **Decision**: **WebSockets** (via `websockets>=12.0`)
-   **Rationale**:
    -   **Bi-directional**: Essential for "Interrupts" (Human-in-the-loop stopping an agent) and streaming partial LLM tokens.
    -   **Low Overhead**: Eliminates polling latency for agent-to-agent negotiation.
    -   **Sufficient for scale**: Handles direct connections well for <50 agents. Message broker (NATS/Kafka) deferred to v2.0+ for larger deployments.
-   **Alternatives deferred**: NATS/Kafka (overkill for startups, adds infrastructure cost). See [SD-3](../../product-specs/roadmap-to-marketplace.md).
-   **Reference**: [ADR-3](../../product-specs/ADR.md#question-3-is-peer-to-peer-default-practical)

### 2.4 State Storage: SQLite via aiosqlite
-   **Decision**: **SQLite** as first persistent backend (via `aiosqlite>=0.20`)
-   **Rationale**:
    -   **Zero-config**: No external services needed. A single file (`asap_state.db`) is the entire database.
    -   **Async-compatible**: `aiosqlite` wraps SQLite with async/await, matching ASAP's async-first architecture.
    -   **Sufficient for single-agent**: One agent = one SQLite file. Covers development, testing, and small production deployments.
    -   **Standard library**: SQLite is part of Python stdlib; `aiosqlite` is a thin async wrapper.
    -   **Foundation, not ceiling**: This is the *reference implementation*. Redis and PostgreSQL adapters follow in v1.2+ as separate packages.
-   **Alternatives considered**:

    | Option | Considered | Outcome |
    |--------|------------|---------|
    | **SQLite (aiosqlite)** | ✅ Selected | Zero-config, file-based, sufficient for single-agent |
    | Redis | Deferred to v1.2+ | Excellent for multi-agent, but requires running Redis server |
    | PostgreSQL | Deferred to v2.0 | Production-grade, but heavy for dev/testing |
    | TinyDB | Rejected | Pure Python, slow, no async, not production-suitable |
    | LevelDB/RocksDB | Rejected | Key-value only, no SQL queries for metering aggregation |

-   **Why not Redis first?**: The target audience (AI startups, individual developers) should be able to run `uv run asap serve` without installing Redis. SQLite provides persistence with zero external dependencies.
-   **Why not sync SQLite?**: The `SnapshotStore` Protocol currently uses sync methods (inherited from v1.0 InMemorySnapshotStore). `aiosqlite` lets us use async internally while maintaining the sync interface. The CP-1 checkpoint (post-v1.1) will evaluate whether to evolve the Protocol to async — a controlled breaking change before marketplace adoption grows.
-   **Reference**: [SD-9](../../product-specs/roadmap-to-marketplace.md), [ADR-13](../../product-specs/ADR.md#question-13-state-management-strategy-for-marketplace)

### 2.5 Discovery: Well-Known URI + Health Endpoint + Lite Registry
-   **Decision**: RFC 8615 well-known URIs + simple health endpoint + static Lite Registry on GitHub Pages
-   **Rationale**:
    -   **No infrastructure**: Agents discover each other via HTTP — no registry, no DNS, no service mesh required.
    -   **Kubernetes-aligned**: `/.well-known/asap/health` follows the `/healthz` pattern that platform engineers expect.
    -   **TTL-based freshness**: `ttl_seconds` in manifest tells consumers how long to trust cached data.
    -   **Lite Registry (SD-11)**: Bridges the "Discovery Abyss" between v1.1 (identity) and v1.2 (full Registry API). Static `registry.json` on GitHub Pages, agents listed via PR. Multi-endpoint schema supports HTTP + WebSocket. SDK provides `discover_from_registry()` method.
-   **Why GitHub Pages for Lite Registry?**:
    -   Zero infrastructure cost — hosted as static file
    -   PR-based submissions create social proof and community engagement (like Go modules before `proxy.golang.org`)
    -   Version-controlled — full history of agent registrations
    -   Machine-readable — JSON, not a human-curated "awesome list"
    -   Migration path — v1.2 Registry API can seed itself from this file
-   **Alternatives deferred**: DNS-SD/mDNS (niche, LAN-only), centralized registry (v1.2). See [SD-10](../../product-specs/roadmap-to-marketplace.md), [SD-11](../../product-specs/roadmap-to-marketplace.md), [ADR-14](../../product-specs/ADR.md#question-14-agent-liveness--health-protocol), [ADR-15](../../product-specs/ADR.md#question-15-lite-registry-for-v11-discovery-gap).

### 2.6 Identity Binding: Custom Claims
-   **Decision**: **JWT Custom Claims** for mapping IdP identities to ASAP agent IDs
-   **Rationale**:
    -   **The problem**: IdP-generated `sub` claims (e.g., `google-oauth2|12345`) never match ASAP `agent_id` values (e.g., `urn:asap:agent:bot`). A strict `sub == agent_id` binding is impossible in practice.
    -   **Custom Claims** (recommended): Agent configures IdP to include `https://asap.ai/agent_id` as a private claim in the JWT. ASAP server validates this claim matches the requesting agent's manifest `id`.
    -   **Allowlist fallback**: `ASAP_AUTH_SUBJECT_MAP` env var for environments where custom claims aren't possible.
-   **Why Custom Claims over strict binding?**:
    -   Portable across IdPs (Auth0, Keycloak, Azure AD all support custom claims)
    -   Standards-based (RFC 7519 allows private claims with namespace-prefixed keys)
    -   More flexible than hardcoded config files
    -   Works with existing IdP admin UIs (no custom code needed on IdP side)
-   **Reference**: [ADR-17](../../product-specs/ADR.md#question-17-trust-model-and-identity-binding-in-v11)

---

## 3. Trust & Intelligence (v1.2 - "Brain")

We needed to evaluate agent quality, ensure safety, and establish verifiable identity.

### 3.1 Signing: Ed25519
-   **Decision**: **Ed25519** (via `cryptography>=41.0`)
-   **Rationale**:
    -   **Modern**: 64-byte signatures (vs RSA's 256+), faster to verify.
    -   **MCP-aligned**: MCP, SSH, and Signal all use Ed25519. Alignment reduces ecosystem friction.
    -   **Single curve**: No "which curve?" confusion (unlike ECDSA with P-256, P-384, etc.).
-   **Alternatives rejected**: ECDSA (multiple curves = complexity), RSA-2048/4096 (slow, large signatures, legacy).
-   **Reference**: [SD-4](../../product-specs/roadmap-to-marketplace.md)

### 3.2 Evaluations: Hybrid (Native + DeepEval)
-   **Decision**: **Hybrid Approach**
-   **Rationale**:
    -   **Native (Shell)**: For protocol compliance (schema checks, state transitions), we wrote our own `pytest` harness. Third-party tools don't understand our binary wire format.
    -   **DeepEval (Brain)**: For "Intelligence" (Hallucination, Bias), we avoided reinventing the wheel. DeepEval gives us research-backed metrics out of the box.
    -   **pytest-native**: DeepEval approaches evals as "Unit Tests for LLMs", aligning perfectly with ASAP's engineering rigor and existing test infrastructure.
-   **Reference**: [ADR-10](../../product-specs/ADR.md#question-10-build-vs-buy-for-agent-evals)

### 3.3 Registry Storage: PostgreSQL (planned)
-   **Decision**: **PostgreSQL** for centralized Registry data
-   **Rationale**:
    -   **Marketplace metadata only**: The Registry stores manifests, trust scores, SLA metrics — not agent task state (per SD-9 Hybrid strategy).
    -   **Full-text search**: `GET /registry/agents?skill=X` requires efficient text search. PostgreSQL's `tsvector` is built-in.
    -   **Horizontal scaling**: PostgreSQL supports read replicas, connection pooling (PgBouncer), and partitioning.
    -   **Mature**: Battle-tested for SaaS workloads. Every cloud provider offers managed Postgres.
-   **Why not SQLite for Registry?**: SQLite is single-writer. The Registry needs concurrent writes from multiple agents registering simultaneously.

---

## 4. Web Marketplace (v2.0 - "Product")

The shift from "Protocol" to "Product" required a modern, SEO-friendly web stack.

### 4.1 Frontend: Next.js 15 (App Router)
-   **Decision**: **Next.js** (over Vite/React SPA)
-   **Rationale**:
    -   **SEO**: The Agent Registry must be indexable by Google. Server-Side Rendering (SSR) is non-negotiable here.
    -   **React Server Components (RSC)**: Allows fetching Registry data directly in the component, simplifying the architecture (no client-side effect chains for static data).
    -   **Vercel Ecosystem**: The project infrastructure (monorepo, edge functions) aligns natively with Next.js.

### 4.2 Language: TypeScript
-   **Decision**: **TypeScript** (Strict)
-   **Rationale**:
    -   **Shared Types**: We can generate TypeScript interfaces from the Python Pydantic models (via `datamodel-code-generator`), ensuring the Frontend is always in sync with the Protocol.
    -   **Safety**: Large-scale frontend apps without types are unmaintainable.

### 4.3 Styling: TailwindCSS v4 + Shadcn/UI
-   **Decision**: **Tailwind + Shadcn**
-   **Rationale**:
    -   **Velocity**: Building a "Premium" look with Vanilla CSS takes months. Shadcn provides accessible, high-quality components (Radix primitives) that we can fully customize.
    -   **Modernity**: Tailwind v4 brings compiler performance improvements.
    -   **Standard**: This is currently the effective industry standard for modern React apps.

### 4.4 Authentication (Web): GitHub + WebCrypto (Hybrid)
-   **Decision**: **Hybrid Flow** (Proposed)
-   **Rationale**:
    -   **The Bootstrap Problem**: Developers don't want to use CLI tools to sign up.
    -   **Solution**: "Sign in with GitHub" to create the account ⇒ Browser generates ASAP Protocol keys (WebCrypto API) locally for agent operations. Low friction, high security.

### 4.5 Payments: Stripe
-   **Decision**: **Stripe**
-   **Rationale**:
    -   **SaaS standard**: Subscriptions ($49/mo Verified badge), checkout flows, and invoicing are built-in.
    -   **Developer-friendly**: Excellent API, SDK, and documentation.
    -   **No alternatives needed**: Stripe handles all payment scenarios for Freemium → Verified tier (SD-2). Multiple payment providers deferred until demand justifies complexity.

### 4.6 Hosting: Vercel (Frontend) + Railway (API)
-   **Decision**: **Vercel + Railway**
-   **Rationale**:
    -   **Vercel**: Native Next.js deployment. Edge functions, CDN, preview deployments. Ideal for solo/small team.
    -   **Railway**: Simple container deployment for FastAPI. Auto-scaling, managed Postgres. Simpler than AWS/GCP for early stage.
    -   **No Kubernetes (yet)**: K8s manifests provided optionally, but not required. Premature infrastructure complexity for pre-traction stage.

---

## 5. Cross-cutting: Storage Strategy (SD-9)

A key architectural decision spanning all versions. See [ADR-13](../../product-specs/ADR.md#question-13-state-management-strategy-for-marketplace).

### 5.1 The Hybrid Model

ASAP follows a **layered storage strategy** — we define interfaces and provide reference implementations, but agents own their data:

| Version | Storage Need | Technology | Why |
|---------|-------------|------------|-----|
| v1.0 | Task snapshots (dev) | InMemorySnapshotStore | Zero-config, testing |
| v1.1 | Task snapshots (persistent) | **SQLite** (aiosqlite) | Zero-config persistence, file-based |
| v1.1 | Metering interface | MeteringStore Protocol | Foundation for v1.3 |
| v1.2 | Registry metadata | **PostgreSQL** | Concurrent writes, full-text search |
| v1.3 | Usage metering | SQLite or PostgreSQL (via MeteringStore) | Agent's choice |
| v1.3 | Audit logs | Append-only store | Hash chain integrity |
| v2.0 | Marketplace data | **PostgreSQL** (managed) | Production SaaS |
| v2.0+ | ASAP Cloud (premium) | Managed storage | "Vercel for Agents" monetization |

### 5.2 The "No Lock-in" Principle

Every storage component uses a Python `Protocol` (structural typing):

```python
@runtime_checkable
class SnapshotStore(Protocol):
    def save(self, snapshot: StateSnapshot) -> None: ...
    def get(self, task_id: TaskID, version: int | None = None) -> StateSnapshot | None: ...
    def list_versions(self, task_id: TaskID) -> list[int]: ...
    def delete(self, task_id: TaskID, version: int | None = None) -> bool: ...
```

Agents can implement this with **any** backend. We provide:
- `InMemorySnapshotStore` — testing
- `SQLiteSnapshotStore` — development, small production (v1.1)
- `RedisSnapshotStore` — multi-agent, high-throughput (v1.2+ separate package)
- `PostgresSnapshotStore` — production (v2.0+ separate package)

### 5.3 Open Decision: Sync vs Async Protocol

The `SnapshotStore` Protocol currently uses **sync** methods (inherited from v1.0). The SQLite implementation wraps async (`aiosqlite`) internally. This works but is not ideal.

**Options**:
1. Keep sync Protocol — simpler for implementers, limits async backends
2. Evolve to async Protocol — breaking change, enables native async storage
3. Dual Protocol — `SnapshotStore` (sync) + `AsyncSnapshotStore` (async)

**Decision**: Deferred to CP-1 checkpoint (post-v1.1 release). Will decide based on implementation experience.

---

## Summary

| Layer | Technology | Key Driver | Version | Reference |
|-------|------------|------------|---------|-----------|
| **Language** | Python 3.13+, mypy strict | AI ecosystem, correctness | v1.0 | |
| **Data** | Pydantic v2 | Validation + Schema | v1.0 | |
| **Communication** | JSON-RPC 2.0 | A2A/MCP alignment | v1.0 | ADR-2 |
| **API** | FastAPI | Async, Pydantic native | v1.0 | |
| **Auth (protocol)** | Authlib, joserfc | OAuth2 M2M, JWKS | v1.1 | ADR-12 |
| **Real-time** | websockets ≥12.0 | Bidirectional, low latency | v1.1 | SD-3 |
| **State Storage** | aiosqlite (SQLite) | Zero-config persistence | v1.1 | SD-9, ADR-13 |
| **Discovery** | Well-known URI + Health + Lite Registry | No infrastructure needed + early discoverability | v1.1 | SD-10, SD-11, ADR-14, ADR-15 |
| **Identity Binding** | Custom Claims + allowlist | IdP sub → agent_id mapping | v1.1 | ADR-17 |
| **Signing** | cryptography (Ed25519) | Modern, fast, MCP-aligned | v1.2 | SD-4 |
| **Evals** | pytest + DeepEval | Shell + Brain hybrid | v1.2 | ADR-10 |
| **Registry DB** | PostgreSQL | Concurrent writes, FTS | v1.2 | |
| **Web** | Next.js 15, TypeScript | SEO, type safety | v2.0 | |
| **UI** | Tailwind v4, Shadcn | Development velocity | v2.0 | |
| **Auth (web)** | GitHub + WebCrypto | Low friction signup | v2.0 | |
| **Payments** | Stripe | SaaS standard | v2.0 | SD-2 |
| **Hosting** | Vercel + Railway | Simple, scalable | v2.0 | |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-05 | Initial document |
| 2026-02-07 | Strategic review: added OAuth2 library (Authlib/joserfc, ADR-12), State Storage (SQLite/aiosqlite, SD-9), Discovery (health endpoint, SD-10), Ed25519 (SD-4), Registry DB (PostgreSQL), Payments (Stripe), Hosting (Vercel/Railway), cross-cutting storage strategy (Section 5), updated Python version to 3.13+ |
| 2026-02-07 | Added Lite Registry rationale (GitHub Pages, SD-11, ADR-15), Custom Claims identity binding (ADR-17), updated summary table |
