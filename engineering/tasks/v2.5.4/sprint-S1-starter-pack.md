# Sprint S1: Thin starter pack (v2.5.4)

**PRD**: DIST-003 (D2, D3)  
**Branch**: `feat/v2.5.4-s0-s2-starters-guide` (combined S0–S2) → **`release/2.5.4`**  
**Depends on**: [S0](./sprint-S0-scope-lock.md)  
**Status**: Done

**Trigger:** S0 locks starter trio and thin-wrapper shape.  
**Enables:** S2 guide links; S3 homepage CTAs.  
**Depends on:** Parent examples/apps remain canonical sources.

---

## Goal

Ship three **thin** starters under `examples/starters/` that wrap existing OpenAPI, TypeScript consumer, and MCP Auth Bridge paths—no new scaffold CLI.

---

## Design constraints

- Prefer wrap/re-export or a short script that invokes the parent example over copying large trees.
- Each starter: `README.md` (English) + entrypoint + `.env.example` only if secrets/config are required.
- Smoke must be headless and finish in ≤60s with a single documented command.
- HTTPS/TLS note where network is involved; no private GTM (DIST-006).
- Full Next.js demo stays at `apps/example-nextjs/`; TypeScript starter may be a thin Node CLI derived from those patterns.

---

## Tasks

- [x] **2.1 Starters index**
  - [x] Create `examples/starters/README.md` listing the three starters + links to parent examples/docs

- [x] **2.2 OpenAPI provider starter**
  - [x] Path: `examples/starters/openapi-provider/`
  - [x] Source: `examples/openapi_petstore/` (+ `docs/adapters/openapi.md`)
  - [x] README smoke command; avoid second OpenAPI fragment source of truth

- [x] **2.3 TypeScript consumer starter**
  - [x] Path: `examples/starters/typescript-consumer/`
  - [x] Source: `apps/example-nextjs/` patterns + `@asap-protocol/client` + `docs/sdks/typescript.md`
  - [x] Prefer thin Node discover/execute smoke; README may point to full Next app
  - [x] Do **not** base on Mastra / OpenAI Agents apps

- [x] **2.4 MCP Auth Bridge starter**
  - [x] Path: `examples/starters/mcp-auth-bridge/`
  - [x] Source: `examples/mcp_auth_bridge/` (+ `docs/adapters/mcp-auth-bridge.md`)
  - [x] Preserve Auth Bridge security pointers from parent README/docs

- [x] **2.5 Smoke verification**
  - [x] Document and run one smoke per starter (headless)
  - [x] Note any optional secrets as env placeholders only (no real credentials)

Smoke evidence (2026-07-18, local):
| Starter | Command | Result |
|---------|---------|--------|
| OpenAPI | `uv run python examples/starters/openapi-provider/run.py` | PASS |
| MCP Auth Bridge | `uv run python examples/starters/mcp-auth-bridge/run.py` | PASS |
| TypeScript | `pnpm install` → `pnpm --filter @asap-protocol/client run build` → `pnpm --filter @asap-protocol/starter-typescript-consumer run smoke` | PASS (workspace member as of S5 quality pass) |
DIST-006 grep on `examples/starters/`: no pricing/fundraising/GTM matches. Optional live: `ASAP_PROVIDER_URL` in `.env.example` only.

---

## Acceptance criteria

- [x] Three directories exist at the locked paths
- [x] Index README present
- [x] Each starter has a documented smoke that passes locally
- [x] DIST-003 satisfied; DIST-006 clean on starter READMEs
- [x] Parent examples remain the canonical deep implementations

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-18 | T2 | Approved with caveats (r2) | [review-v2.5.4-S0-S2-starters-guide-20260718-r2.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718-r2.md) |
| 2026-07-18 | C.7 | Rejected (r1) — fixes applied pending r2 | [review-v2.5.4-S0-S2-starters-guide-20260718.md](../../../code-review/private/review-v2.5.4-S0-S2-starters-guide-20260718.md) |

## Relevant files

- `examples/starters/**`
- `examples/openapi_petstore/`
- `examples/mcp_auth_bridge/`
- `apps/example-nextjs/`
- `packages/typescript/client`
- `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md`, `docs/sdks/typescript.md`
