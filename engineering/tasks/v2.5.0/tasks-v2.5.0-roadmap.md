# Tasks: v2.5.0 MCP Auth Bridge — Sprint Index

**Status: 🟡 IN PROGRESS** — S0–S4 merged on **`release/2.5.0`** (`a60c1e9`, incl. post-S4 refactor [PR #234](https://github.com/adriannoes/asap-protocol/pull/234)); **S5 release** next ([sprint-S5-release.md](./sprint-S5-release.md)).

Based on [PRD v2.5.0 MCP Auth Bridge](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md). Each sprint maps to a PR into **`release/2.5.0`** (see [BRANCHING.md](./BRANCHING.md)); merge to `main` only after S5.

## Prerequisites

- [x] v2.4.1 Security Hardening shipped (2026-06-14) — [prd-v2.4.1-security-hardening.md](../../../product/prd/prd-v2.4.1-security-hardening.md)
- [x] Agent JWT + Host JWT stable (`auth/agent_jwt.py`, v2.2+)
- [x] Capability grants + constraint validation (`CapabilityRegistry.check_grant`, `validate_constraints`, v2.2+)
- [x] `MCPServer` stdio + `tools/call` (`mcp/server.py`, MCP 2025-11-25)
- [x] S0 design lock: confirm wrapper strategy, `CapabilityRegistry` injection, and `_meta` parser changes before S1

## Sprint Plan

| Sprint | Focus | PRD sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S0** | [Design lock & scaffold](./sprint-S0-design-lock.md) | §6 API, MCP-AUTH-005 | P0 | ✅ Done |
| **S1** | [Core auth middleware](./sprint-S1-core-middleware.md) | MCP-AUTH-001..004, 006 and auth portions of 007 | P0 | ✅ Done (merged `60e2e85`, PR #229) |
| **S2** | [Capability mapping & errors](./sprint-S2-capability-mapping.md) | MCP-MAP-*, §4.5–4.6 | P0 | ✅ Done (merged `8352936`, PR #231; MCP-MAP-004 deferred) |
| **S3** | [Docs, examples & discovery](./sprint-S3-docs-examples.md) | MCP-DISC-*, MCP-DOC-* | P0/P1 | ✅ Done (merged `175ae02`, PR #232) |
| **S4** | [Compliance & integration tests](./sprint-S4-compliance.md) | MCP-DISC-003, harness | P1 | ✅ Done (merged `4b67b50`, [PR #233](https://github.com/adriannoes/asap-protocol/pull/233)) |
| **S5** | [Release v2.5.0](./sprint-S5-release.md) | DoD, metrics | P0 | 🔵 **Active** — branch `feat/v2.5.0-s5-release` |

> **Note:** `@asap-protocol/mcp-auth` (TypeScript, MCP-TS-*) is SHOULD. S4 spike **decided DEFER to v2.5.0.1** ([typescript-mcp-auth-spike.md](./typescript-mcp-auth-spike.md)); S5 records defer in CHANGELOG/backlog — does not block Python tag.

## Dependency Graph

```
S0 (scaffold + design lock)
 │
 ├──► S1 (protect_server + verify_agent_jwt)
 │         │
 │         └──► S2 (tool→capability + constraints + errors)
 │                   │
 │                   ├──► S3 (docs + example server + discovery)
 │                   │         │
 │                   │         └──► S4 (compliance harness)
 │                   │                   │
 │                   └───────────────────┴──► S5 (release)
```

S1 depends on S0. S2 depends on S1. S3 depends on S2 (example server calls protected API). S4 depends on S2+S3. S5 depends on S1–S4.

## Parent Tasks (high-level)

Detailed sub-tasks live in per-sprint files (`sprint-S0` … `sprint-S5`).

- [x] **1.0 Design lock & package scaffold (S0)**
  - **Trigger:** Kickoff v2.5.0 after v2.4.1 ship.
  - **Enables:** S1 middleware implementation in `asap.adapters.mcp`.
  - **Depends on:** Stable `verify_agent_jwt`, `MCPServer` in tree.
  - **Acceptance criteria:**
    - [x] Package `src/asap/adapters/mcp/` exists with `MCPAuthConfig` dataclass and public exports
    - [x] `MCPAuthConfig` includes `host_store`, `agent_store`, `capability_registry`, `jti_replay_cache`, and `expected_audience`
    - [x] Design note documents `tools/call` hook strategy (wrap vs refactor) and grant-check flow
    - [x] Default `jwt_extractor` interface defined ( `_meta.asap_agent_jwt` + dev env fallback)

- [x] **2.0 Core auth middleware (S1)**
  - **Trigger:** S0 complete.
  - **Enables:** S2 capability checks; protected `tools/call` path.
  - **Depends on:** Task 1.0; `auth/agent_jwt.verify_agent_jwt`.
  - **Acceptance criteria:**
    - [x] `protect_server(server, config)` wraps `tools/call` without breaking unprotected servers
    - [x] Missing/invalid JWT returns MCP `CallToolResult` with `isError: true` and `asap:*` codes
    - [x] `public_tools` allowlist skips JWT for named tools only
    - [x] Unit tests: missing token, expired token, tampered token, success path

- [x] **3.0 Capability mapping & constraint enforcement (S2)**
  - **Trigger:** S1 `protect_server` dispatches authenticated calls.
  - **Enables:** S3 example server with real grants; S4 compliance cases.
  - **Depends on:** Task 2.0; `CapabilityRegistry.check_grant` / `auth/capabilities.validate_constraints`.
  - **Acceptance criteria:**
    - [x] `tool_capability_map` + default identity mapping (tool name == capability)
    - [x] Denied grants, JWT capability-claim mismatches, and constraint violations return the correct `asap:*` codes
    - [x] Optional startup validation: every registered tool resolves to a capability (MCP-MAP-003)
    - [x] Test coverage ≥90% on `asap.adapters.mcp`

- [x] **4.0 Documentation, examples & discovery (S3)**
  - **Trigger:** Protected server runnable locally.
  - **Enables:** External adopters; S4 harness documentation paths.
  - **Depends on:** Task 3.0.
  - **Acceptance criteria:**
    - [x] `docs/adapters/mcp-auth-bridge.md` published (architecture, token carriage, config reference)
    - [x] `examples/mcp_auth_bridge/` runs: `uv run python examples/mcp_auth_bridge/server.py`
    - [x] `docs/mcp-integration.md` distinguishes Mode A (native MCP) vs Mode B (ASAP envelope)
    - [x] Manifest ↔ tool alignment pattern documented, including `skills[].id` ↔ MCP tool snippets (MCP-DISC-001/002)
    - [x] Migration note states unprotected MCP servers remain valid and protection is opt-in (MCP-DOC-004)

- [ ] **5.0 Compliance, quality & release (S4–S5)**
  - **Trigger:** Example server + docs merged.
  - **Enables:** v2.5.1 Adapter Lab II (blocked until tag).
  - **Depends on:** Tasks 2.0–4.0.
  - **Acceptance criteria:**
    - [x] `asap-compliance` includes `mcp-auth-bridge` profile cases for stdio MCP, including manifest tools ⊆ registered tools (merged `4b67b50`, [PR #233](https://github.com/adriannoes/asap-protocol/pull/233))
    - [x] Post-S4 refactor: unified capability metadata, `MCPAuthConfig` in `config.py`, split adapter tests (merged `a60c1e9`, [PR #234](https://github.com/adriannoes/asap-protocol/pull/234))
    - [x] TS middleware: **deferred to v2.5.0.1** per [typescript-mcp-auth-spike.md](./typescript-mcp-auth-spike.md) (MCP-TS-001..003; not a release blocker)
    - [ ] `pyproject.toml` → **2.5.0**; tag `v2.5.0` published (S5)
    - [ ] `AGENTS.md` knowledge map updated; CHANGELOG `[2.5.0]` with TS defer subsection (S5)
    - [ ] Pre-push CI suite green on `release/2.5.0` (ruff, mypy, pytest ≥85% cov, pip-audit) (S5)
    - [ ] `release/2.5.0` → `main` merge + maintainer PyPI publish (S5)

## Relevant Files (overview)

### New (expected)

- `src/asap/adapters/mcp/__init__.py` — public exports (`protect_server`, `MCPAuthConfig`, `ProtectedMCPServer`)
- `src/asap/adapters/mcp/config.py` — `MCPAuthConfig`, `resolve_jwt_extractor` (extracted PR #234)
- `src/asap/adapters/mcp/auth_middleware.py` — JWT extraction, `protect_server`, error mapping
- `src/asap/adapters/mcp/capability_map.py` — tool → capability resolution; constraint violation formatting
- `src/asap/adapters/mcp/protected_server.py` — bridge registry, startup validation, grant gate
- `src/asap/adapters/mcp/errors.py` — ASAP MCP error code constants
- `tests/adapters/mcp/test_jwt_gate.py`, `test_grant_enforcement.py`, `test_capability_startup.py` — auth path tests (split PR #234)
- `tests/adapters/mcp/test_capability_map.py` — mapping + constraint tests
- `tests/adapters/mcp/test_stdio_integration.py` — protected stdio MCP integration (S4)
- `examples/mcp_auth_bridge/` — runnable protected MCP server (shipped S3)
- `examples/mcp_auth_bridge/server.py`, `client.py`, `README.md` — reference protected stdio server + JWT flow
- `docs/adapters/mcp-auth-bridge.md` — integration guide (shipped S3)
- `tests/examples/test_mcp_auth_bridge_example.py` — example smoke test (shipped S3)

### Modify (expected)

- `src/asap/mcp/server.py` — hook point for `tools/call` interception (if refactor needed)
- `src/asap/mcp/protocol.py` — `_meta` on `CallToolRequestParams` if types need extension
- `docs/mcp-integration.md` — Mode A vs Mode B (updated S3)
- `docs/index.md` — Adoption tools link to MCP auth bridge guide (updated S3)
- `asap-compliance/` — release-gate `mcp_auth` profile for stdio MCP
- `src/asap/testing/compliance.py` — unchanged unless shared HTTP harness support is explicitly needed
- `AGENTS.md`, `CHANGELOG.md`, `pyproject.toml`

### Reference (read-only patterns)

- `src/asap/auth/agent_jwt.py` — `verify_agent_jwt`, `JtiReplayCache`
- `src/asap/auth/capabilities.py` — grants, `CapabilityRegistry.check_grant`, `validate_constraints`
- `src/asap/adapters/openapi/` — adapter package layout precedent
- `src/asap/mcp/server.py` — existing `MCPServer.register_tool`

### Notes

- Unit tests mirror `src/asap/adapters/mcp/` under `tests/adapters/mcp/`.
- Run: `uv run pytest tests/adapters/mcp/ -v`

## Definition of Done (v2.5.0)

- [ ] All parent tasks 1.0–5.0 complete (1.0–4.0 + S4 ✅; 5.0 pending S5 release)
- [x] PRD requirements MCP-AUTH-001..006, MCP-MAP-001..003, MCP-DOC-001..004 satisfied (MCP-MAP-004 / `hide_unauthorized_tools` deferred per design lock §6)
- [x] PRD discovery requirements MCP-DISC-001..003 satisfied or explicitly deferred with rationale (MCP-DISC-001/002 ✅ in S3; MCP-DISC-003 ✅ in S4 `mcp-auth-bridge` harness, PR #233)
- [x] Unprotected `MCPServer` usage unchanged (opt-in via `protect_server`)
- [x] No wire-protocol breaking changes

## Estimated Effort

| Sprint | Effort |
|--------|--------|
| S0 Design lock | 1–2 days |
| S1 Core middleware | 3–4 days |
| S2 Capability mapping | 2–3 days |
| S3 Docs + example | 2 days |
| S4 Compliance | 1–2 days |
| S5 Release | 0.5–1 day |

**Total target:** ~2–3 weeks (solo maintainer).

## Related

- **PRD:** [prd-v2.5.0-mcp-auth-bridge.md](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
- **Train:** [prd-v2.5-roadmap.md](../../../product/prd/prd-v2.5-roadmap.md)
- **Existing MCP:** [docs/mcp-integration.md](../../../docs/mcp-integration.md), `src/asap/mcp/server.py`

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Draft roadmap from PRD §7 |
| 2026-06-22 | Parent tasks 1.0–5.0 added (Phase 1) |
| 2026-06-22 | Phase 2: sprint S0–S5 sub-tasks; `release/2.5.0` integration branch |
| 2026-06-24 | Reconciled task plan with PRD paths, repo APIs, compliance scope, and TypeScript spike/defer gate |
| 2026-06-24 | S0 complete on `release/2.5.0`; S1 branch `feat/v2.5.0-s1-middleware` opened with parallel agent workstreams |
| 2026-06-24 | S2 branch `feat/v2.5.0-s2-capability-map` opened; parallel workstreams documented in sprint-S2 |
| 2026-06-24 | S2 merged on `release/2.5.0` (`8352936`); S3 branch `feat/v2.5.0-s3-docs-examples` opened with parallel workstreams |
| 2026-06-24 | S1/S2 merge refs reconciled; S3 impl complete — [PR #232](https://github.com/adriannoes/asap-protocol/pull/232) open into `release/2.5.0`; parent tasks 1.0–4.0 marked done |
| 2026-06-24 | S4 acceptance gate green on `feat/v2.5.0-s4-compliance` (pytest + ruff + mypy); PR pending merge into `release/2.5.0` |
| 2026-06-24 | S4 merged on `release/2.5.0` (`4b67b50`, [PR #233](https://github.com/adriannoes/asap-protocol/pull/233)); `mcp-auth-bridge` compliance profile, stdio integration tests, CI on `release/2.5.0`, TS `@asap-protocol/mcp-auth` defer to v2.5.0.1; S5 release pending |
| 2026-06-24 | Post-S4 refactor merged (`a60c1e9`, [PR #234](https://github.com/adriannoes/asap-protocol/pull/234)); `MCPAuthConfig` → `config.py`, adapter tests split; branch synced with `origin/release/2.5.0`; S5 active |
| 2026-06-24 | S5 release prep — [PR #235](https://github.com/adriannoes/asap-protocol/pull/235) (`feat/v2.5.0-s5-release` → `release/2.5.0`): version 2.5.0, CHANGELOG, docs sync; awaiting review |
