# Sprint S2: Capability Mapping & Constraint Enforcement (v2.5.0)

**PRD**: [MCP-MAP-*, §4.5–4.6](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s2-capability-map` → merge into **`release/2.5.0`**
**Depends on**: [S1 core middleware](./sprint-S1-core-middleware.md)

**Trigger:** Authenticated `tools/call` after S1.
**Enables:** S3 example with real grants; S4 compliance.
**Depends on:** `CapabilityRegistry.check_grant` and `validate_constraints` from `auth/capabilities.py`; S1 auth context.

---

## Execution notes

> **Status:** S2 ready — S1 merged on `release/2.5.0` (commit `60e2e85`).
> **Branch:** `feat/v2.5.0-s2-capability-map` → PR into `release/2.5.0`.

### Dependency phases

```text
Phase 1 (gate)          Phase 2 (parallel tests)           Phase 3 (single owner)              Phase 4
──────────────          ────────────────────────           ──────────────────────              ───────
1.1 resolve_capability ─► 1.2/1.3 mapping tests (red)  ──┐
       + unit tests       2.1/2.2 grant tests (red)   ──┼──► protected_server wiring
                                                          │    (1.2 + 1.3 + 2.1 + 2.2)
                                                          └──► 3.1 hide_unauthorized (MAY/defer)
```

### Sequential vs parallel summary

| Must be sequential | Safe to parallelize (after 1.1) |
|--------------------|----------------------------------|
| **1.1 → Phase 2** (resolver before middleware/tests that import it) | Mapping and grant tests can split across `test_capability_map.py` and `test_auth_middleware.py` |
| **Phase 2 → implementation** (TDD red before green) | — |
| **1.2 + 1.3 + 2.1 + 2.2 impl** (one `_handle_tools_call` + `from_server`) | Keep implementation in one pass to avoid conflicts in the same handler |
| **2.x → 3.1** (list filter needs grant gate) | 3.1 may defer per design lock §6 |

### Implementation notes

- **Design lock is locked:** Grant gate uses `CapabilityRegistry.check_grant` only — do not call `validate_constraints` in middleware (only in unit tests for formatting helpers).
- **JWT capabilities claim:** When `enforce_grants=True`, resolved capability MUST appear in JWT `capabilities` claim **and** pass `check_grant` (MCP-AUTH-003).
- **Error codes:** Use `errors.tool_error_result(CAPABILITY_DENIED|CONSTRAINT_VIOLATION, …)` — constants already in S0.
- **S1 tests stay green:** Keep `enforce_grants=False` in existing S1 tests; add new S2 tests with `enforce_grants=True` and seeded grants.
- **Startup validation (1.3):** When `validate_tools_at_startup=True`, every registered tool must resolve to non-empty capability and `config.capability_registry.describe(capability)` must return non-`None`.
- **3.1 defer path:** stdio `tools/list` has no standard JWT carriage — if not implementing, document in design lock §6 and mark 3.1 deferred with test skip + comment.
- **Verify gate:** `uv run pytest tests/adapters/mcp/ -v` green + `uv run pytest --cov=asap.adapters.mcp --cov-fail-under=90` + `uv run mypy src/asap/adapters/mcp/` clean.

---

## Relevant Files

### New / modify
- `src/asap/adapters/mcp/capability_map.py` — resolve tool → capability name; `format_constraint_violations`
- `src/asap/adapters/mcp/auth_middleware.py` — `bridge_tool_capability_map` on `MCPAuthConfig`
- `src/asap/adapters/mcp/protected_server.py` — bridge registry, startup validation, grant gate
- `tests/adapters/mcp/test_capability_map.py`
- `tests/adapters/mcp/test_auth_middleware.py` — extend with grant/constraint cases

### Reference
- `src/asap/auth/capabilities.py` — `CapabilityRegistry`, `CapabilityGrant`, `validate_constraints`
- `src/asap/auth/agent_jwt.py` — `CAPABILITIES_CLAIM` in JWT

---

## Tasks

### 1.0 Capability resolution

- [x] 1.1 Implement `resolve_capability(tool_name, config) -> str`
  - **File**: `src/asap/adapters/mcp/capability_map.py` (create)
  - **What**: Check `tool_capability_map` first; default identity `tool_name == capability`
  - **Why**: MCP-MAP-001
  - **Verify**: `pytest tests/adapters/mcp/test_capability_map.py -v`

- [x] 1.2 Optional per-tool capability on register (SHOULD)
  - **File**: `src/asap/adapters/mcp/auth_middleware.py` or extend `register_tool` wrapper
  - **What**: Allow `protect_server` to accept optional metadata registry `tool_name -> capability` set at register time
  - **Why**: MCP-MAP-002
  - **Verify**: Test explicit map overrides default

- [x] 1.3 Startup validation (SHOULD)
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: On `protect_server`, if `config.validate_tools_at_startup`, ensure every registered tool resolves to a non-empty capability and `config.capability_registry.describe(capability)` is present unless an explicit defer is recorded in the design lock.
  - **Why**: MCP-MAP-003
  - **Verify**: Test fails fast when map incomplete

### 2.0 Grant enforcement

- [x] 2.1 Cross-check JWT capabilities claim vs grant store
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: When `enforce_grants=True`, call `config.capability_registry.check_grant(agent_id, resolved_capability, parsed.arguments)` and also honor the JWT `capabilities` claim subset.
  - **Why**: MCP-AUTH-003
  - **Verify**: Test denied grant → `asap:capability_denied`

- [x] 2.2 Constraint validation on arguments
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Use violations returned by `CapabilityRegistry.check_grant`; call `validate_constraints(grant.constraints, parsed.arguments)` directly only in unit tests for formatting helpers. Format violations into `asap:constraint_violation` messages.
  - **Why**: PRD §4.5
  - **Integration**: Uses same constraint dict shape as ASAP task handlers
  - **Verify**: Test `max` constraint exceeded

### 3.0 Optional tools/list filtering (MAY)

- [x] 3.1 `hide_unauthorized_tools` for tools/list — **deferred per design lock §6**
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: If enabled and JWT present on list call (or session from initialize — document limitation), filter tool list
  - **Why**: MCP-MAP-004
  - **Verify**: Default-off test + skipped future-behavior test in `test_auth_middleware.py`; defer note in `auth_middleware.py` / `protected_server.py`

---

## Acceptance Criteria (S2)

- [x] Tool→capability mapping with explicit map + default identity
- [x] Denied/inactive grants, JWT capability-claim mismatches, and constraint violations return correct `asap:*` codes
- [x] Coverage ≥90% on `src/asap/adapters/mcp/` (run `pytest --cov=asap.adapters.mcp`)
- [x] All S1 tests still green
- [x] MCP-MAP-004 (`hide_unauthorized_tools`) deferred with tests + design-lock §6 note (default `False` leaves `tools/list` unchanged)
