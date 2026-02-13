# ASAP Protocol: Technology Stack Decisions

> **Category**: Implementation & Dependencies
> **Focus**: Language, Frameworks, Tools

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

## Question 11: What Tech Stack for v2.0 Web Marketplace?

### The Question
v2.0 launches the Agent Marketplace. What technology stack should we use?

### EXPERT ASSESSMENT

**Rationale for Next.js**:
- SEO is critical for a marketplace. SSR (Server Side Rendering) is required.
- Integration: Vercel owns Next.js and makes deployment seamless.
- Ecosystem: Massive library of components (shadcn/ui, Tailwind).

### RECOMMENDATION: Next.js + Tailwind + Vercel

```
Stack:
- Frontend: Next.js 15 (App Router)
- Styling: TailwindCSS + Shadcn/UI
- Hosting: Vercel (Free Tier/Pro)
- Auth: NextAuth.js (or ASAP OAuth client)
```

### Spec Amendment

> [!NOTE]
> Added to v2.0 Roadmap: Development stack locked to Next.js 15.

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
