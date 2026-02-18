# ASAP Protocol: Technology Stack & Architecture Decisions

This document provides a historical and technical rationale for the technology choices made throughout the evolution of the ASAP Protocol, from its core (v1.0) to the Marketplace (v2.0).

> **Goal**: Explain *why* we chose these tools, offering context for future contributors and architects.
>
> **Last Updated**: 2026-02-12 (Lean Marketplace pivot)

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
-   **Why not Rust/Go?**: ASAP is I/O-bound, not CPU-bound. Critical performance paths already use Rust internally via dependencies (pydantic-core, orjson). Custom native extensions deferred until profiling identifies specific bottlenecks. See [ADR-9](../../product-specs/decision-records/04-technology.md).

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
-   **Alternatives rejected**: REST (paradigm mismatch for agent actions), gRPC (limited browser support, heavier tooling). See [ADR-2](../../product-specs/decision-records/02-protocol.md).
-   > **Note:** JSON-RPC 2.0 applies to agent-to-agent transport (`POST /asap`, `WS /asap/ws`).
    Operator-facing APIs (health, metrics, usage, SLA, delegations) use standard REST
    for compatibility with dashboards, Prometheus, and Kubernetes probes.

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
-   **Reference**: [ADR-12](../../product-specs/decision-records/04-technology.md)

### 2.3 Real-time: WebSockets
-   **Decision**: **WebSockets** (via `websockets>=12.0`)
-   **Rationale**:
    -   **Bi-directional**: Essential for "Interrupts" (Human-in-the-loop stopping an agent) and streaming partial LLM tokens.
    -   **Low Overhead**: Eliminates polling latency for agent-to-agent negotiation.
    -   **Sufficient for scale**: Handles direct connections well for <50 agents. Message broker (NATS/Kafka) deferred to v2.0+ for larger deployments.
-   **Alternatives deferred**: NATS/Kafka (overkill for startups, adds infrastructure cost). See [SD-3](../../product-specs/strategy/roadmap-to-marketplace.md).
-   **Reference**: [ADR-3](../../product-specs/decision-records/01-architecture.md)

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
-   **Reference**: [SD-9](../../product-specs/strategy/roadmap-to-marketplace.md), [ADR-13](../../product-specs/decision-records/01-architecture.md)

### 2.5 Discovery: Well-Known URI + Health Endpoint + Lite Registry
-   **Decision**: RFC 8615 well-known URIs + simple health endpoint + static Lite Registry on GitHub Pages
-   **Rationale**:
    -   **No infrastructure**: Agents discover each other via HTTP — no registry, no DNS, no service mesh required.
    -   **Kubernetes-aligned**: `/.well-known/asap/health` follows the `/healthz` pattern that platform engineers expect.
    -   **TTL-based freshness**: `ttl_seconds` in manifest tells consumers how long to trust cached data.
    -   **Lite Registry (SD-11)**: Bridges the "Discovery Abyss" between v1.1 (identity) and full Registry API (v2.1). Static `registry.json` on GitHub Pages, agents listed via PR. Multi-endpoint schema supports HTTP + WebSocket. SDK provides `discover_from_registry()` method.
-   **Why GitHub Pages for Lite Registry?**:
    -   Zero infrastructure cost — hosted as static file
    -   PR-based submissions create social proof and community engagement (like Go modules before `proxy.golang.org`)
    -   Version-controlled — full history of agent registrations
    -   Machine-readable — JSON, not a human-curated "awesome list"
    -   Migration path — v2.1 Registry API can seed itself from this file
-   **Alternatives deferred**: DNS-SD/mDNS (niche, LAN-only), centralized registry (v1.2). See [SD-10](../../product-specs/strategy/roadmap-to-marketplace.md), [SD-11](../../product-specs/strategy/roadmap-to-marketplace.md), [ADR-14](../../product-specs/decision-records/01-architecture.md), [ADR-15](../../product-specs/decision-records/05-product-strategy.md).

### 2.6 Identity Binding: Custom Claims
-   **Decision**: **JWT Custom Claims** for mapping IdP identities to ASAP agent IDs
-   **Rationale**:
    -   **The problem**: IdP-generated `sub` claims (e.g., `google-oauth2|12345`) never match ASAP `agent_id` values (e.g., `urn:asap:agent:bot`). A strict `sub == agent_id` binding is impossible in practice.
    -   **Custom Claims** (recommended): Agent configures IdP to include a custom claim (default: `https://github.com/adriannoes/asap-protocol/agent_id`) in the JWT. ASAP server validates this claim matches the requesting agent's manifest `id`. Future: `https://asap-protocol.com/agent_id` will be the canonical namespace when the domain is available.
    -   **Allowlist fallback**: `ASAP_AUTH_SUBJECT_MAP` env var for environments where custom claims aren't possible.
-   **Why Custom Claims over strict binding?**:
    -   Portable across IdPs (Auth0, Keycloak, Azure AD all support custom claims)
    -   Standards-based (RFC 7519 allows private claims with namespace-prefixed keys)
    -   More flexible than hardcoded config files
    -   Works with existing IdP admin UIs (no custom code needed on IdP side)
-   **Reference**: [ADR-17](../../product-specs/decision-records/03-security.md)

---

## 3. Verified Identity (v1.2 - "Signing & Compliance")

Focus shifted to verifiable agent identity and protocol compliance certification.

### 3.1 Signing: Ed25519
-   **Decision**: **Ed25519** (via `cryptography>=41.0`)
-   **Rationale**:
    -   **Modern**: 64-byte signatures (vs RSA's 256+), faster to verify.
    -   **MCP-aligned**: MCP, SSH, and Signal all use Ed25519. Alignment reduces ecosystem friction.
    -   **Single curve**: No "which curve?" confusion (unlike ECDSA with P-256, P-384, etc.).
-   **Alternatives rejected**: ECDSA (multiple curves = complexity), RSA-2048/4096 (slow, large signatures, legacy).
-   **Reference**: [SD-4](../../product-specs/strategy/roadmap-to-marketplace.md)

### 3.2 Evaluations: Protocol Compliance (Shell)
-   **Decision**: **ASAP Compliance Harness** (pytest-based)
-   **Rationale**:
    -   **Shell-only for v1.2**: Protocol compliance (schema checks, state transitions) via our own `pytest` harness. Third-party tools don't understand our wire format.
    -   **DeepEval deferred**: Intelligence evaluation (Hallucination, Bias) deferred to v2.2+. The marketplace does not require AI quality scoring to function — it requires protocol compliance.
-   **What changed**: Original plan was a Hybrid approach (Native Shell + DeepEval Brain). Lean Marketplace pivot recognized that compliance certification is the MVP blocker, not intelligence scoring.
-   **Reference**: [ADR-10](../../product-specs/decision-records/05-product-strategy.md), [deferred-backlog.md](../../product-specs/strategy/deferred-backlog.md#2-deepeval-intelligence-layer-originally-v12-sprint-t61)

### 3.3 Registry Storage: Lite Registry (deferred PostgreSQL)
-   **Decision**: **Lite Registry** (`registry.json` on GitHub Pages) continues through v2.0
-   **Rationale**:
    -   **Lean Marketplace pivot**: Full Registry API Backend with PostgreSQL deferred to v2.1.
    -   **Lite Registry sufficient**: Static JSON file handles 100+ agents without backend infrastructure.
    -   **Web App reads JSON**: Next.js can fetch `registry.json` at build time (SSG) or via ISR.
-   **Migration path**: When agent count exceeds Lite Registry capacity or dynamic features (real-time search, write API) are needed, PostgreSQL Registry API activates in v2.1.
-   **Reference**: [deferred-backlog.md](../../product-specs/deferred-backlog.md#1-registry-api-backend-originally-v12-sprints-t3t4)

---

## 4. Lean Marketplace (v2.0 - "Product")

The shift from "Protocol" to "Product" with a lean approach — no backend API, Web App reads from Lite Registry.

### 4.1 Frontend: Next.js 15 (App Router)
-   **Decision**: **Next.js** (over Vite/React SPA)
-   **Rationale**:
    -   **SEO**: The Agent Registry must be indexable by Google. Server-Side Rendering (SSR) is non-negotiable here.
    -   **React Server Components (RSC)**: Allows fetching `registry.json` directly in the component, simplifying the architecture (no client-side effect chains).
    -   **Vercel Ecosystem**: The project infrastructure (monorepo, edge functions) aligns natively with Next.js.

### 4.2 Language: TypeScript
-   **Decision**: **TypeScript** (Strict)
-   **Rationale**:
    -   **Shared Types**: We can generate TypeScript interfaces from the Python Pydantic models (via `datamodel-code-generator`), ensuring the Frontend is always in sync with the Protocol.
    -   **Safety**: Large-scale frontend apps without types are unmaintainable.

### 4.3 Design & Styling: Design-First + Tailwind/Shadcn
-   **Decision**: **Design-First Workflow** implemented via **Tailwind v4 + Shadcn/UI**
-   **Rationale**:
    -   **Design-First**: No frontend coding without approved mockups. "Engineer-art" is unacceptable for a marketplace.
    -   **Tools**: Excalidraw (Wireframes/Flows) -> Figma (High-fidelity) -> Code.
    -   **Velocity**: Building a "Premium" look from scratch takes months. Shadcn provides accessible, high-quality components (Radix primitives) that we can customized to match Figma designs.
    -   **Modernity**: Tailwind v4 brings compiler performance improvements.
    -   **Standard**: This is currently the effective industry standard for modern React apps.

### 4.4 Authentication (Web): GitHub + WebCrypto (Hybrid)
-   **Decision**: **Hybrid Flow** (Proposed)
-   **Rationale**:
    -   **The Bootstrap Problem**: Developers don't want to use CLI tools to sign up.
    -   **Solution**: "Sign in with GitHub" to create the account ⇒ Browser generates ASAP Protocol keys (WebCrypto API) locally for agent operations. Low friction, high security.

### 4.5 Payments: None (Deferred to v3.0)
-   **Decision**: **No Payments in v2.0**
-   **Rationale**:
    -   **Lean focus**: Priority is adoption and directory growth.
    -   **Lower barrier**: Verified badge is manually awarded based on merit/trust, not paid subscription.
    -   **Simplicity**: Avoids legal/tax complexity during initial growth phase.

### 4.6 Data Source: Lite Registry (GitHub Pages JSON)
-   **Decision**: **Lite Registry (`registry.json`)** as primary data source
-   **Rationale**:
    -   **No backend API needed**: Web App fetches `registry.json` at build time (SSG) or via Incremental Static Regeneration (ISR).
    -   **Zero infrastructure**: No database, no API server, no Railway — just Vercel + GitHub Pages.
    -   **Lean validation**: Proves marketplace value before investing in backend infrastructure.
-   **What changed**: Original plan had FastAPI backend + PostgreSQL + Railway. Lean Marketplace pivot removed backend entirely.
-   **Migration path**: When dynamic features are needed (real-time writes, complex search), Registry API Backend activates in v2.1.

### 4.7 Backend Logic: Next.js API Routes (Serverless)
-   **Decision**: **Next.js API Routes**
-   **Rationale**:
    -   **The "No Backend" Exception**: While we avoid a standalone backend service, some operations require server-side execution for security (hiding secrets) or webhook handling.
    -   **Use Cases**:
        -   **Auth Exchange**: Swapping OAuth codes for access tokens (to keep client_secret hidden).
    -   **Constraint**: Keep this layer minimal. No complex business logic or persistent database state.

### 4.8 Hosting: Vercel
-   **Decision**: **Vercel**
-   **Rationale**:
    -   **Zero config**: Native Next.js support.
    -   **Global Edge**: Fast content delivery.
    -   **CI/CD**: Automatic deployments from GitHub.

---

## 5. Cross-cutting: Storage Strategy (SD-9)

A key architectural decision spanning all versions. See [ADR-13](../../product-specs/decision-records/01-architecture.md).

### 5.1 The Hybrid Model

ASAP follows a **layered storage strategy** — we define interfaces and provide reference implementations, but agents own their data:

| Version | Storage Need | Technology | Why |
|---------|-------------|------------|-----|
| v1.0 | Task snapshots (dev) | InMemorySnapshotStore | Zero-config, testing |
| v1.1 | Task snapshots (persistent) | **SQLite** (aiosqlite) | Zero-config persistence, file-based |
| v1.1 | Metering interface | MeteringStore Protocol | Foundation for v1.3 |
| v1.2-v2.0 | Agent discovery | **Lite Registry** (GitHub Pages JSON) | Zero-infrastructure, PR-based |
| v1.3 | Observability metering | SQLite or PostgreSQL (via MeteringStore) | Agent's choice |
| v2.0 | Marketplace data | Lite Registry + Vercel | Static site, no backend |
| v2.1 | Registry API Backend | **PostgreSQL** (managed) | Scale demands backend |
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
| **Evals** | pytest (Compliance Harness) | Shell-only (DeepEval deferred to v2.2+) | v1.2 | ADR-10 |
| **Registry** | Lite Registry (GitHub Pages JSON) | Zero infrastructure, primary through v2.0 | v1.1-v2.0 | SD-11, ADR-15 |
| **Web** | Next.js 15, TypeScript | SEO, type safety | v2.0 | |
| **UI** | Tailwind v4, Shadcn | Development velocity | v2.0 | |
| **Auth (web)** | GitHub + WebCrypto | Low friction signup | v2.0 | |
| **Payments** | None (Deferred) | Deferred to v3.0 | v3.0 | SD-2 |
| **Data Source** | Lite Registry (`registry.json`) | No backend needed for MVP | v2.0 | SD-11 |
| **Hosting** | Vercel | Simple, scalable (no Railway for v2.0) | v2.0 | |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-05 | Initial document |
| 2026-02-07 | Strategic review: added OAuth2 library (Authlib/joserfc, ADR-12), State Storage (SQLite/aiosqlite, SD-9), Discovery (health endpoint, SD-10), Ed25519 (SD-4), Registry DB (PostgreSQL), Payments (Stripe), Hosting (Vercel/Railway), cross-cutting storage strategy (Section 5), updated Python version to 3.13+ |
| 2026-02-07 | Added Lite Registry rationale (GitHub Pages, SD-11, ADR-15), Custom Claims identity binding (ADR-17), updated summary table |
| 2026-02-12 | **Lean Marketplace pivot**: §3 renamed "Verified Identity", DeepEval deferred to v2.2+, PostgreSQL Registry deferred to v2.1, §4 updated to Lite Registry data source, Railway removed, storage strategy updated |
