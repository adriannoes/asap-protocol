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

### Expert Assessment

**Rationale for Next.js**:
- SEO is critical for a marketplace. SSR (Server Side Rendering) is required.
- Integration: Vercel owns Next.js and makes deployment seamless.
- Ecosystem: Massive library of components (shadcn/ui, Tailwind).

### Recommendation: Next.js + Tailwind + Vercel

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

---

## Question 13: How to handle deep nested npm vulnerabilities in our Next.js frontend?

### The Question
When running `npm audit`, we frequently encounter vulnerabilities deep within the dependency tree (e.g., in `eslint` dependencies like `minimatch` or `ajv`). The CLI suggests running `npm audit fix --force`, which upgrades the root `eslint` package to a new major version. Should we do this to maintain zero vulnerabilities?

### Analysis

**Current Stack Constraints**:
- Next.js 16.1.6 and its official linting package (`eslint-config-next`) strongly depend on `eslint@9.x`.
- React 19.2.3 and `@typescript-eslint/parser` also have strict peer dependencies on `eslint@9.x`.

**Impact of `npm audit fix --force`**:
1. It forcibly upgrades ESLint to `10.x`.
2. This breaks the peer dependencies for Next.js, React, and TypeScript linting configurations.
3. The Build process completely breaks due to mismatched or unsupported linting plugins.

**Alternative**: Use npm `overrides`.
The `"overrides"` object in `package.json` allows us to force specific versions of deeply nested transitive dependencies (e.g., forcing `minimatch` to `>=10.2.1`) without altering the top-level libraries that rely on them.

### Expert Assessment

The primary applications (Next.js, React, Tailwind) are inherently modernized out of the box. Breaking the framework's core utility packages (like ESLint configs) just to satisfy an automated audit for indirect dev-dependencies is a drastic anti-pattern. 

Security is important, but stability is paramount in a Next.js App Router environment. Forced major version bumps of central infrastructural packages (like Linting) create massive technical debt and block feature delivery.

### Recommendation: **Use NPM Overrides**

Never use `npm audit fix --force` if it bumps major framework-aligned packages like `eslint` or `typescript`. Instead, surgically patch deep vulnerabilities using `"overrides"` in `package.json` while maintaining minor/patch automated updates for the rest of the application.

### Decision

> [!IMPORTANT]
> **ADR-19**: Adopt surgical NPM overrides for nested frontend vulnerabilities instead of forced major version bumps.
>
> **Rationale**: Our modern frontend stack (Next.js 16, React 19, Auth.js v5) relies on highly specific peer dependency graphs. `npm audit fix --force` natively disrupts these graphs by bumping root packages (like ESLint 9 to 10), failing the build. Using `"overrides"` allows us to resolve the security alerts without breaking the framework's official tooling. Future maintenance should rely on automated patch/minor dependency updates (e.g. via Dependabot) and manual, isolated sprints for any Major version bumps.
>
> **Date**: 2026-02-20

---

## Question 23: Mypy Strategy for src, scripts, and tests

### The Question

The CI runs `uv run mypy src/` and passes. Running mypy on the full repo (`mypy .`) fails with ~500 errors in `tests/` and a module name conflict involving `scripts/`. How should we structure mypy checks across src, scripts, and tests?

### Analysis

**Current state**:

| Directory | Mypy (strict) | Notes |
|-----------|---------------|-------|
| `src/` | ✅ 0 errors | CI checks this |
| `scripts/` | ✅ 0 errors | Not in CI; module conflict when running `mypy .` |
| `tests/` | ❌ ~263 errors | 51 files; no-any-return, type-arg, unused-ignore, misc |

**Root cause of conflict**: `scripts/` lacked `__init__.py`. When mypy runs on the full tree, `scripts/process_registration.py` was seen under two module names (`process_registration` vs `scripts.process_registration`) because `tests/scripts/` imports `from scripts.process_registration`.

**Alternatives considered**:

1. **scripts/__init__.py**: Makes `scripts/` an explicit package. Resolves conflict, aligns with `tests/` structure. Simple and standard.
2. **explicit_package_bases**: Mypy option to declare package roots without `__init__.py`. More config, less common; `tests/scripts/` already imports `scripts` as a package at runtime.
3. **Exclude tests from mypy**: Keep CI as-is. Tests remain untyped; no incremental improvement.

### Expert Assessment

- **Scripts**: Few files, automate protocol operations. Same quality bar as `src/` is justified.
- **Tests**: Strict mode is punitive for mocks, fixtures, and pytest patterns. A relaxed profile (disallow_untyped_defs=false, warn_return_any=false, disable no-any-return) balances type safety with pragmatism.
- **Fixtures**: `conftest.py` and shared test utilities should remain strictly typed; they are the foundation.

### Recommendation: **Tiered Mypy Strategy**

1. **Scripts (immediate)**: Add `scripts/__init__.py` to resolve module conflict. Include `scripts/` in CI mypy (same strict config as `src/`).
2. **Tests (next sprint)**: Add `[[tool.mypy.overrides]]` for `tests.*` with relaxed settings. Include `tests/` in CI. Fix `unused-ignore` by removing obsolete `# type: ignore` comments.
3. **Fixtures**: Keep `conftest.py` and test utilities strictly typed.

### Decision

> [!IMPORTANT]
> **ADR-23**: Tiered mypy strategy for src, scripts, and tests.
>
> **Rationale**: `src/` and `scripts/` share strict mode because both are production-facing. Tests use a relaxed profile to accommodate mocks and pytest idioms while still catching type errors in test bodies. `scripts/__init__.py` resolves the module name conflict when running mypy on the full repo.
>
> **Implementation**:
> - `scripts/__init__.py`: Created to make `scripts/` an explicit package.
> - CI: `uv run mypy src/ scripts/ tests/`.
> - `src/` and `scripts/`: Strict mode (same config).
> - Tests: Override `tests.*` with relaxed profile: disallow_untyped_defs=false, warn_return_any=false, disallow_any_generics=false, plus disable_error_code for no-any-return, misc, attr-defined, arg-type, override, no-untyped-def, return, index, call-arg, comparison-overlap, union-attr, method-assign, assignment, operator, return-value, redundant-cast, truthy-function, name-defined.
> - Fixtures: `conftest.py` and shared test utilities remain strictly typed.
>
> **Date**: 2026-02-21
