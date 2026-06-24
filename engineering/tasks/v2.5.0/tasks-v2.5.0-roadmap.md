# Tasks: v2.5.0 MCP Auth Bridge — Sprint Index

**Status: 🟢 READY** — parent tasks + per-sprint sub-tasks defined; integration branch **`release/2.5.0`**.

Based on [PRD v2.5.0 MCP Auth Bridge](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md). Each sprint maps to a PR into **`release/2.5.0`** (see [BRANCHING.md](./BRANCHING.md)); merge to `main` only after S5.

## Prerequisites

- [x] v2.4.1 Security Hardening shipped (2026-06-14) — [tasks-v2.4.1-security-hardening.md](../private/v2.4.1/tasks-v2.4.1-security-hardening.md)
- [x] Agent JWT + Host JWT stable (`auth/agent_jwt.py`, v2.2+)
- [x] Capability grants + constraint validation (`auth/capabilities.py`, v2.2+)
- [x] `MCPServer` stdio + `tools/call` (`mcp/server.py`, MCP 2025-11-25)
- [ ] S0 design lock: confirm `tools/call` interception point in `MCPServer` (may need thin refactor)

## Sprint Plan

| Sprint | Focus | PRD sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S0** | [Design lock & scaffold](./sprint-S0-design-lock.md) | §6 API, MCP-AUTH-005 | P0 | 🔵 Planned |
| **S1** | [Core auth middleware](./sprint-S1-core-middleware.md) | MCP-AUTH-001..004, 006..007 | P0 | 🔵 Planned |
| **S2** | [Capability mapping & errors](./sprint-S2-capability-mapping.md) | MCP-MAP-*, §4.5–4.6 | P0 | 🔵 Planned |
| **S3** | [Docs, examples & discovery](./sprint-S3-docs-examples.md) | MCP-DISC-*, MCP-DOC-* | P0/P1 | 🔵 Planned |
| **S4** | [Compliance & integration tests](./sprint-S4-compliance.md) | MCP-DISC-003, harness | P1 | 🔵 Planned |
| **S5** | [Release v2.5.0](./sprint-S5-release.md) | DoD, metrics | P0 | 🔵 Planned |

> **Note:** `@asap-protocol/mcp-auth` (TypeScript, MCP-TS-*) is SHOULD — spike in S4 or defer to v2.5.0.1 with documented gap in CHANGELOG.

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

- [ ] **1.0 Design lock & package scaffold (S0)**
  - **Trigger:** Kickoff v2.5.0 after v2.4.1 ship.
  - **Enables:** S1 middleware implementation in `asap.adapters.mcp`.
  - **Depends on:** Stable `verify_agent_jwt`, `MCPServer` in tree.
  - **Acceptance criteria:**
    - [ ] Package `src/asap/adapters/mcp/` exists with `MCPAuthConfig` dataclass and public exports
    - [ ] Design note documents `tools/call` hook strategy (wrap vs refactor)
    - [ ] Default `jwt_extractor` interface defined ( `_meta.asap_agent_jwt` + dev env fallback)

- [ ] **2.0 Core auth middleware (S1)**
  - **Trigger:** S0 complete.
  - **Enables:** S2 capability checks; protected `tools/call` path.
  - **Depends on:** Task 1.0; `auth/agent_jwt.verify_agent_jwt`.
  - **Acceptance criteria:**
    - [ ] `protect_server(server, config)` wraps `tools/call` without breaking unprotected servers
    - [ ] Missing/invalid JWT returns MCP `CallToolResult` with `isError: true` and `asap:*` codes
    - [ ] `public_tools` allowlist skips JWT for named tools only
    - [ ] Unit tests: missing token, expired token, success path

- [ ] **3.0 Capability mapping & constraint enforcement (S2)**
  - **Trigger:** S1 `protect_server` dispatches authenticated calls.
  - **Enables:** S3 example server with real grants; S4 compliance cases.
  - **Depends on:** Task 2.0; `auth/capabilities.validate_constraints`.
  - **Acceptance criteria:**
    - [ ] `tool_capability_map` + default identity mapping (tool name == capability)
    - [ ] Denied grant and constraint violation return `asap:capability_denied` / `asap:constraint_violation`
    - [ ] Optional startup validation: every registered tool resolves to a capability (MCP-MAP-003)
    - [ ] Test coverage ≥90% on `asap.adapters.mcp`

- [ ] **4.0 Documentation, examples & discovery (S3)**
  - **Trigger:** Protected server runnable locally.
  - **Enables:** External adopters; S4 harness documentation paths.
  - **Depends on:** Task 3.0.
  - **Acceptance criteria:**
    - [ ] `docs/adapters/mcp-auth-bridge.md` published (architecture, token carriage, config reference)
    - [ ] `examples/mcp_auth_bridge/` runs: `uv run python examples/mcp_auth_bridge/server.py`
    - [ ] `docs/mcp-integration.md` distinguishes Mode A (native MCP) vs Mode B (ASAP envelope)
    - [ ] Manifest ↔ tool alignment pattern documented (MCP-DISC-001/002)

- [ ] **5.0 Compliance, quality & release (S4–S5)**
  - **Trigger:** Example server + docs merged.
  - **Enables:** v2.5.1 Adapter Lab II (blocked until tag).
  - **Depends on:** Tasks 2.0–4.0.
  - **Acceptance criteria:**
    - [ ] Compliance harness includes `mcp_auth` module case (green in CI)
    - [ ] `pyproject.toml` / npm → **2.5.0**; tag `v2.5.0` published
    - [ ] `AGENTS.md` knowledge map updated; CHANGELOG `[2.5.0]`
    - [ ] Pre-push CI suite green (ruff, mypy, pytest, TS if touched)
    - [ ] TS middleware: shipped OR explicit defer note in CHANGELOG

## Relevant Files (overview)

### New (expected)

- `src/asap/adapters/mcp/__init__.py` — public exports (`protect_server`, `MCPAuthConfig`)
- `src/asap/adapters/mcp/auth_middleware.py` — JWT extraction, `protect_server`, error mapping
- `src/asap/adapters/mcp/capability_map.py` — tool → capability resolution
- `src/asap/adapters/mcp/errors.py` — ASAP MCP error code constants
- `tests/adapters/mcp/test_auth_middleware.py` — auth path tests
- `tests/adapters/mcp/test_capability_map.py` — mapping + constraint tests
- `examples/mcp_auth_bridge/` — runnable protected MCP server
- `docs/adapters/mcp-auth-bridge.md` — integration guide

### Modify (expected)

- `src/asap/mcp/server.py` — hook point for `tools/call` interception (if refactor needed)
- `src/asap/mcp/protocol.py` — `_meta` on `CallToolRequestParams` if types need extension
- `docs/mcp-integration.md` — Mode A vs Mode B
- `asap-compliance/` + `tests/testing/compliance.py` — harness case
- `AGENTS.md`, `CHANGELOG.md`, `pyproject.toml`

### Reference (read-only patterns)

- `src/asap/auth/agent_jwt.py` — `verify_agent_jwt`, `JtiReplayCache`
- `src/asap/auth/capabilities.py` — grants, `validate_capability_constraints`
- `src/asap/adapters/openapi/` — adapter package layout precedent
- `src/asap/mcp/server.py` — existing `MCPServer.register_tool`

### Notes

- Unit tests mirror `src/asap/adapters/mcp/` under `tests/adapters/mcp/`.
- Run: `PYTHONPATH=src uv run pytest tests/adapters/mcp/ -v`

## Definition of Done (v2.5.0)

- [ ] All parent tasks 1.0–5.0 complete
- [ ] PRD requirements MCP-AUTH-001..007, MCP-MAP-001..003, MCP-DOC-001..004 satisfied
- [ ] Unprotected `MCPServer` usage unchanged (opt-in via `protect_server`)
- [ ] No wire-protocol breaking changes

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
