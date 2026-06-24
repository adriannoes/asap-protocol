# Sprint S4: Compliance Harness (v2.5.0)

**PRD**: [MCP-AUTH-005, compliance section](../../../product/prd/prd-v2.5.0-mcp-auth-bridge.md)
**Branch**: `feat/v2.5.0-s4-compliance` → merge into **`release/2.5.0`**
**Depends on**: [S3 example](./sprint-S3-docs-examples.md)

**Trigger:** Release gate for v2.5.0.
**Enables:** S5 version bump and PyPI publish.
**Depends on:** `asap-compliance` package; protected MCP example from S3.

---

## Relevant Files

### New / modify
- `asap-compliance/asap_compliance/validators/mcp_auth.py` — MCP auth bridge checks
- `asap-compliance/tests/test_mcp_auth.py`
- `examples/mcp_auth_bridge/` — ensure Compliance Harness v2 compatible endpoint or script hook
- `asap-compliance/asap_compliance/validators/__init__.py` — export new validator

### Reference
- `asap-compliance/asap_compliance/validators/handshake.py`
- `examples/openapi_petstore/` — compliance score pattern

---

## Tasks

### 1.0 Validator design

- [ ] 1.1 Define MCP auth compliance checks
  - **File**: `asap-compliance/asap_compliance/validators/mcp_auth.py` (create)
  - **What**: Black-box checks: (a) unauthenticated `tools/call` on protected tool returns error; (b) valid JWT succeeds; (c) wrong capability denied. Config: stdio subprocess or test server URL
  - **Why**: MCP-AUTH-005
  - **Pattern**: Return `list[CheckResult]` like `validate_handshake_async`
  - **Verify**: Unit tests with mocked server responses first

### 2.0 Integration with harness

- [ ] 2.1 Wire validator into compliance CLI
  - **File**: `asap-compliance/asap_compliance/validators/__init__.py` + main runner if exists
  - **What**: Optional profile `mcp-auth-bridge` targeting example server
  - **Verify**: `uv run` compliance against `examples/mcp_auth_bridge` scores required checks

- [ ] 2.2 Example compliance script or README section
  - **File**: `examples/mcp_auth_bridge/README.md`
  - **What**: Document command to run harness v2 and expected score
  - **Verify**: CI or local script passes

### 3.0 Regression tests

- [ ] 3.1 Full adapter test suite in CI
  - **File**: root CI workflow or existing pytest job
  - **What**: Ensure `tests/adapters/mcp/` runs on every PR to `release/2.5.0`
  - **Verify**: PR check green

---

## Acceptance Criteria (S4)

- [ ] MCP auth validator returns pass/fail `CheckResult` for auth required + valid JWT paths
- [ ] Example achieves compliance harness target (document threshold, e.g. 1.0 on MCP profile)
- [ ] `pytest asap-compliance/tests/test_mcp_auth.py -v` green
