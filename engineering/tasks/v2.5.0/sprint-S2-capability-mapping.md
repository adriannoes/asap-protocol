# Sprint S2: Capability Mapping & Constraint Enforcement (v2.5.0)

**PRD**: [MCP-MAP-*, §4.5–4.6](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s2-capability-map` → merge into **`release/2.5.0`**
**Depends on**: [S1 core middleware](./sprint-S1-core-middleware.md)

**Trigger:** Authenticated `tools/call` after S1.
**Enables:** S3 example with real grants; S4 compliance.
**Depends on:** `CapabilityRegistry.check_grant` and `validate_constraints` from `auth/capabilities.py`; S1 auth context.

---

## Relevant Files

### New / modify
- `src/asap/adapters/mcp/capability_map.py` — resolve tool → capability name
- `src/asap/adapters/mcp/auth_middleware.py` — wire grant check + constraints
- `tests/adapters/mcp/test_capability_map.py`
- `tests/adapters/mcp/test_auth_middleware.py` — extend with grant/constraint cases

### Reference
- `src/asap/auth/capabilities.py` — `CapabilityRegistry`, `CapabilityGrant`, `validate_constraints`
- `src/asap/auth/agent_jwt.py` — `CAPABILITIES_CLAIM` in JWT

---

## Tasks

### 1.0 Capability resolution

- [ ] 1.1 Implement `resolve_capability(tool_name, config) -> str`
  - **File**: `src/asap/adapters/mcp/capability_map.py` (create)
  - **What**: Check `tool_capability_map` first; default identity `tool_name == capability`
  - **Why**: MCP-MAP-001
  - **Verify**: `pytest tests/adapters/mcp/test_capability_map.py -v`

- [ ] 1.2 Optional per-tool capability on register (SHOULD)
  - **File**: `src/asap/adapters/mcp/auth_middleware.py` or extend `register_tool` wrapper
  - **What**: Allow `protect_server` to accept optional metadata registry `tool_name -> capability` set at register time
  - **Why**: MCP-MAP-002
  - **Verify**: Test explicit map overrides default

- [ ] 1.3 Startup validation (SHOULD)
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: On `protect_server`, if `config.validate_tools_at_startup`, ensure every registered tool resolves to a non-empty capability and `config.capability_registry.describe(capability)` is present unless an explicit defer is recorded in the design lock.
  - **Why**: MCP-MAP-003
  - **Verify**: Test fails fast when map incomplete

### 2.0 Grant enforcement

- [ ] 2.1 Cross-check JWT capabilities claim vs grant store
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: When `enforce_grants=True`, call `config.capability_registry.check_grant(agent_id, resolved_capability, parsed.arguments)` and also honor the JWT `capabilities` claim subset.
  - **Why**: MCP-AUTH-003
  - **Verify**: Test denied grant → `asap:capability_denied`

- [ ] 2.2 Constraint validation on arguments
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: Use violations returned by `CapabilityRegistry.check_grant`; call `validate_constraints(grant.constraints, parsed.arguments)` directly only in unit tests for formatting helpers. Format violations into `asap:constraint_violation` messages.
  - **Why**: PRD §4.5
  - **Integration**: Uses same constraint dict shape as ASAP task handlers
  - **Verify**: Test `max` constraint exceeded

### 3.0 Optional tools/list filtering (MAY)

- [ ] 3.1 `hide_unauthorized_tools` for tools/list
  - **File**: `src/asap/adapters/mcp/auth_middleware.py`
  - **What**: If enabled and JWT present on list call (or session from initialize — document limitation), filter tool list
  - **Why**: MCP-MAP-004
  - **Verify**: Test or document as deferred if stdio list has no JWT — mark in design lock

---

## Acceptance Criteria (S2)

- [ ] Tool→capability mapping with explicit map + default identity
- [ ] Denied/inactive grants, JWT capability-claim mismatches, and constraint violations return correct `asap:*` codes
- [ ] Coverage ≥90% on `src/asap/adapters/mcp/` (run `pytest --cov=asap.adapters.mcp`)
- [ ] All S1 tests still green
