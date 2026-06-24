# Spike: `@asap-protocol/mcp-auth` (S4 Task 4.1)

> **Status**: COMPLETE (S4)
> **PRD**: [MCP-TS-001..003](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md#54-typescript-should)
> **Sprint**: [sprint-S4-compliance.md](./sprint-S4-compliance.md) task 4.1
> **Decision**: **DEFER to v2.5.0.1** (see §6; durable record in [PRD v2.5.1 §3](../../../product/prd/prd-v2.5.1-adapter-lab-ii.md#3-carry-over-from-v250-asap-protocolmcp-auth))

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Ship `@asap-protocol/mcp-auth` in v2.5.0? | **No — defer to v2.5.0.1** |
| Block v2.5.0 Python release? | **No** — MCP-TS-* are SHOULD; Python stdio bridge is the release gate |
| Minimum viable scope (when shipped) | Bearer extraction + ASAP Agent JWT verify + `asap:*` error mapping on `tools/call` |
| Estimated effort (v2.5.0.1) | ~3–5 maintainer days (package scaffold, verifier, middleware hook, tests, publish CI) |

---

## 2. Current TypeScript package layout

### 2.1 Monorepo structure

```text
packages/typescript/
├── client/           → @asap-protocol/client
├── mastra/           → @asap-protocol/mastra
└── openai-agents/    → @asap-protocol/openai-agents
```

Registered in `pnpm-workspace.yaml` as `packages/typescript/*` plus explicit adapter paths.

### 2.2 Naming and publishing conventions

| Convention | Value in repo |
|------------|---------------|
| Scope | `@asap-protocol/*` (public npm) |
| Multi-word packages | kebab-case (`mcp-auth` fits) |
| Version (current) | `2.4.1` on all three packages |
| License | Apache-2.0 |
| Node | `>=18` |
| Module system | `"type": "module"` + **tshy** dual ESM/CJS (`dist/esm`, `dist/commonjs`) |
| Tests | vitest + coverage |
| Lint | eslint 9 + typescript-eslint |
| Adapter pattern | `peerDependencies` on framework SDK + `workspace:*` devDep on `@asap-protocol/client` |
| Publish | `.github/workflows/publish-typescript.yml` — tags `v2.3.*` / `v2.4.*` only; syncs version from tag to all three packages |

### 2.3 `@asap-protocol/client` relevance

The client is the natural foundation for JWT crypto:

- **Has**: `jose` (^6.0.10), Ed25519 keygen (`ed25519-keypair.ts`), Host/Agent JWT **minting** (`identity.ts`), Bearer header helper in `capabilities.ts`
- **Lacks**: public `verifyAgentJwt()` API (only test-side `jwtVerify` usage); no `CapabilityRegistry` / grant-check port; no MCP `CallToolResult` helpers

A v2.5.0.1 `@asap-protocol/mcp-auth` would depend on `@asap-protocol/client` for shared JWT types/constants and likely add verification there or in `mcp-auth` directly.

### 2.4 No existing MCP auth surface

- No `packages/typescript/mcp-auth/` directory
- No `createMcpAuthMiddleware` symbol anywhere in the repo
- `docs/adapters/mcp-auth-bridge.md` documents **Python stdio only** (no HTTP/SSE TS section)
- v2.5.0 example is `examples/mcp_auth_bridge/server.py` (stdio)

---

## 3. `@modelcontextprotocol/sdk` dependency survey

### 3.1 Where it appears

| Location | Version | Direct? |
|----------|---------|---------|
| Root `pnpm-lock.yaml` | **1.29.0** | Transitive (via `@mastra/core`) |
| `apps/web/package-lock.json` | 1.26.0 | Transitive |
| `packages/typescript/*/package.json` | — | **Not declared** |

None of the published ASAP TypeScript packages list `@modelcontextprotocol/sdk` as a direct or peer dependency today.

### 3.2 SDK stack (lockfile resolution for 1.29.0)

- Runtime: `hono`, `express` 5.x, `jose` 6.2.x, `zod` 3.x or 4.x (peer)
- Transports: stdio, SSE, Streamable HTTP (modern path per MCP TS SDK docs)

### 3.3 Compatibility assessment for HTTP/SSE Bearer middleware

**Feasible, but not drop-in for ASAP semantics.**

The MCP SDK ships OAuth-oriented HTTP middleware (`requireBearerAuth`) that:

1. Validates `Authorization: Bearer <token>` via an `OAuthTokenVerifier` callback
2. Attaches `AuthInfo` to the HTTP request (`req.auth` / `ctx.http.authInfo`)
3. On failure returns **HTTP 401/403** with `WWW-Authenticate` OAuth challenge JSON — not MCP `CallToolResult` with `isError: true`

ASAP MCP Auth Bridge (Python reference) instead:

1. Intercepts **`tools/call`** (not only the HTTP handshake)
2. Verifies **Agent JWT** (EdDSA, `typ: agent+jwt`, `capabilities` claim, JTI replay)
3. Checks **capability grants** per tool + argument constraints
4. Returns **`CallToolResult`** text codes: `asap:auth_required`, `asap:invalid_token`, `asap:capability_denied`, `asap:constraint_violation`

**Gap:** SDK Bearer middleware covers transport-level OAuth; ASAP needs a **tool-dispatch wrapper** analogous to Python `ProtectedMCPServer._handle_tools_call`. The SDK does not expose a single `createMcpAuthMiddleware` hook — integration is compose-your-own: `requireBearerAuth` + custom tool handler wrapper + grant store injection.

**Version pin recommendation (v2.5.0.1):** `peerDependency` on `@modelcontextprotocol/sdk` `^1.29.0` (align with lockfile; test against zod 3 and 4 peer variants).

**Risk:** SDK auth APIs evolved across 1.26 → 1.29; pin and test on upgrade. MCP OAuth middleware ≠ ASAP Agent JWT — document clearly in package README.

---

## 4. Minimum implementation scope (MCP-TS-001..003)

If shipped in **v2.5.0.1**, the smallest useful package:

### 4.1 Package scaffold

```text
packages/typescript/mcp-auth/
├── package.json          # name: @asap-protocol/mcp-auth
├── src/
│   ├── index.ts
│   ├── middleware.ts     # createMcpAuthMiddleware
│   ├── bearer.ts         # extractBearerToken(req)
│   ├── errors.ts         # ASAP_* constants + toolErrorResult()
│   ├── verify.ts         # verifyAgentJwt wrapper (jose)
│   └── types.ts          # McpAuthConfig, re-exports from SDK where needed
└── test/
    └── middleware.test.ts
```

### 4.2 Public API (locked for spike)

```typescript
export interface McpAuthConfig {
  /** Host/agent public keys or stores — mirror Python MCPAuthConfig subset */
  verifyAgentJwt: (token: string) => Promise<VerifiedAgent>;
  toolCapabilityMap?: Record<string, string>;
  publicTools?: ReadonlySet<string>;
  checkGrant?: (
    agentId: string,
    capability: string,
    args: Record<string, unknown>,
  ) => Promise<GrantCheckResult>;
  expectedAudience?: string | string[];
}

/** Wrap SDK HTTP/SSE server tool dispatch with ASAP auth + grant checks. */
export function createMcpAuthMiddleware(
  config: McpAuthConfig,
): McpAuthMiddleware;
```

### 4.3 MUST behaviors (parity with Python)

| # | Behavior | Python reference |
|---|----------|------------------|
| 1 | Extract Bearer from `Authorization` header on HTTP/SSE requests | PRD §4.3; opposite of stdio `_meta.asap_agent_jwt` |
| 2 | Map missing token → `asap:auth_required` in `CallToolResult` | `asap.adapters.mcp.errors.AUTH_REQUIRED` |
| 3 | Map invalid/expired JWT → `asap:invalid_token` | `INVALID_TOKEN` |
| 4 | Map missing grant / capability → `asap:capability_denied` | `CAPABILITY_DENIED` |
| 5 | Map constraint fail → `asap:constraint_violation` | `CONSTRAINT_VIOLATION` |
| 6 | Re-export SDK types used by middleware signatures | MCP-TS-003 |

### 4.4 Explicitly out of minimum scope

- Full in-memory `CapabilityRegistry` port (inject `checkGrant` callback; operators bring store)
- `initialize` session-token handshake (deferred repo-wide)
- `hide_unauthorized_tools` / `tools/list` filtering
- Runnable HTTP/SSE example server (nice-to-have for v2.5.0.1 docs)
- stdio `_meta.asap_agent_jwt` in TS (Python-only carriage for v2.5.0)

### 4.5 Error payload shape (must match Python)

```json
{
  "content": [{"type": "text", "text": "asap:auth_required"}],
  "isError": true
}
```

Detail appended after `:` when present (e.g. `asap:invalid_token: expired`).

---

## 5. Why not ship in v2.5.0

| Factor | Assessment |
|--------|------------|
| PRD priority | MCP-TS-001..003 are **SHOULD**; Python MCP-AUTH-* / MCP-DOC-* are **MUST** |
| Release focus | v2.5.0 PRD §1.4: stdio first; HTTP/SSE MCP in Python core **out of scope** |
| S4/S5 scope | S4 = compliance gate (Python `mcp-auth-bridge` profile); S5 = version bump + tag — not greenfield npm package |
| Implementation gap | No package, no verifier API, no HTTP MCP example, no compliance harness for TS |
| Architectural mismatch | SDK `requireBearerAuth` = OAuth HTTP errors; ASAP = per-`tools/call` grant checks + `CallToolResult` codes — needs careful wrapper, not a afternoon spike |
| CI / publish | `publish-typescript.yml` triggers on `v2.3.*` / `v2.4.*` only; adding a fourth package + `v2.5.*` tags is S5-adjacent work |
| Release train note | [tasks-v2.5.0-roadmap.md](./tasks-v2.5.0-roadmap.md) already states S4 spike → S5 ship **or** v2.5.0.1 defer |
| User value | v2.5.0 delivers complete stdio story (`protect_server`, example, compliance); TS HTTP adopters are secondary and can wait one patch |

**Conclusion:** Deferring does not block PRD Definition of Done for v2.5.0 Python deliverables or the `mcp-auth-bridge` compliance profile.

---

## 6. Recommendation

### **DEFER `@asap-protocol/mcp-auth` to v2.5.0.1**

**Rationale (one line):** v2.5.0 ships the Python stdio MCP Auth Bridge as the release gate; TypeScript HTTP/SSE middleware is SHOULD-scope work that needs a new package, JWT verifier port, and SDK integration testing — better as a focused v2.5.0.1 patch than a risk to the v2.5.0 tag.

---

## 7. S5 actions (based on DEFER decision)

### 7.1 During S5 release (required)

- [x] **CHANGELOG.md** — Under v2.5.0, add subsection *TypeScript*: state MCP-TS-001..003 **deferred to v2.5.0.1** with link to this spike (S5 — PR #235)
- [x] **docs/adapters/mcp-auth-bridge.md** — One paragraph: Python stdio shipped; `@asap-protocol/mcp-auth` for HTTP/SSE planned v2.5.0.1 (link spike) (S5 — PR #235)
- [x] **product/checkpoints.md** — Note TS middleware defer; not a v2.5.0 blocker (S5 §3.3)
- [ ] **Do not** add `packages/typescript/mcp-auth` or bump TS packages to 2.5.0 for this feature

### 7.2 S5 task 4.1 (post-release backlog)

- [x] Create GitHub issue or `engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md` tracking:
  - MCP-TS-001: `createMcpAuthMiddleware`
  - MCP-TS-002: Bearer + error mapping parity
  - MCP-TS-003: SDK type re-exports
  - Target: **v2.5.0.1** npm + docs
- [ ] Link issue from CHANGELOG defer note

### 7.3 v2.5.0.1 implementation checklist (future sprint)

| Task | Owner hint |
|------|------------|
| Add `verifyAgentJwt` to `@asap-protocol/client` (or `mcp-auth`) | Port Python `verify_agent_jwt` semantics |
| Scaffold `packages/typescript/mcp-auth` | Mirror mastra/openai-agents layout |
| Implement `createMcpAuthMiddleware` | Compose SDK HTTP transport + tools/call wrapper |
| vitest: Bearer extract, four error codes, success path | Mock grant callback |
| Extend `publish-typescript.yml` | `v2.5.*` tags + fourth package dry-run/publish |
| `docs/integrations/mcp-auth-typescript.md` | HTTP/SSE setup guide |
| Optional: minimal Express/Hono example | `apps/example-mcp-auth/` or docs snippet |

### 7.4 If decision had been SHIP (not chosen)

S5 would additionally require: implement minimum scope §4, extend publish workflow, bump all `@asap-protocol/*` to 2.5.0 on tag, and document in CHANGELOG as shipped. **Rejected** for v2.5.0 timeline.

---

## 8. References

- [PRD v2.5.1 — §3 carry-over (durable defer record)](../../../product/prd/prd-v2.5.1-adapter-lab-ii.md#3-carry-over-from-v250-asap-protocolmcp-auth)
- [PRD v2.5.0 MCP Auth Bridge — §5.4 TypeScript](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
- [Python errors module](../../../src/asap/adapters/mcp/errors.py)
- [Adapter guide (stdio)](../../../docs/adapters/mcp-auth-bridge.md)
- [S5 release tasks](./sprint-S5-release.md)
- [MCP TS SDK `requireBearerAuth`](https://github.com/modelcontextprotocol/typescript-sdk/tree/main/packages/middleware/express/src/auth) — OAuth transport middleware (reference only)

---

## Change log

| Date | Change |
|------|--------|
| 2026-06-24 | S4 Agent E spike — **DEFER to v2.5.0.1** |
