# Code Review: PR #105

**PR**: [feat(auth,transport): Sprint S1 — capabilities & lifecycle](https://github.com/adriannoes/asap-protocol/pull/105)
**Branch**: `feat/capabilities-lifecycle` → `main`
**Sprint**: S1 — Capabilities & Lifecycle (v2.2 Protocol Hardening)
**Reviewer**: Senior Staff Engineer (AI-Assisted)
**Date**: 2026-03-23
**Fixes Applied**: 2026-03-23 — All 4 required fixes + deep dive items resolved

---

## 1. Executive Summary

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Tech Stack** | ✅ | Pydantic v2 (`ASAPBaseModel`), FastAPI, `joserfc`, Ed25519 — all aligned with `tech-stack-decisions.md`. No new dependencies introduced. |
| **Architecture** | ✅ | Clean layering (models → logic → transport). ~~Duplicated `_bearer_token_from_request`~~ extracted to shared `_auth_helpers.py`. `CapabilityRegistry` documented as single-process. |
| **Security** | ✅ | Lifecycle clock integration solid. ~~Swallowed exceptions~~ now return specific `ValueError`/`ValidationError` detail. ~~Unvalidated int() casts~~ replaced with FastAPI `Query()` annotations. ~~Deferred import~~ moved to top-level. |
| **Tests** | ✅ | Unit coverage 98.6% + **24 new endpoint integration tests** in `test_capability_routes.py`. 101 total S1 tests, 227 auth tests pass, 66 transport tests pass. |

> **General Feedback:** This is a well-structured PR that delivers on all S1 task requirements. The capability model is clean, constraint operators are thorough, and the lifecycle clock logic is correct and well-tested. All review findings have been addressed — see §2 Resolution Log below.

---

## 2. Required Fixes (Must Address Before Merge)

### Fix #1: No Endpoint Tests for `capability_routes.py` — ✅ RESOLVED

*   **Location:** `tests/` — missing test file for capability and reactivation endpoints
*   **Problem:** `capability_routes.py` is 369 lines of transport logic (auth dispatch, body parsing, constraint-violation serialization, capability decay on reactivation) with **zero test coverage**. The existing tests cover only the auth-layer models and pure functions, not the HTTP integration.
*   **Rationale (Expert View):** The endpoints are where auth mode switching (`/capability/list` supports 3 auth modes), error serialization (constraint violations → JSON), and the reactivation capability-decay logic all converge. Bugs in these paths won't be caught by unit tests on `capabilities.py` or `lifecycle.py`. The S0 review (PR #102) had thorough endpoint tests — this PR should match that standard.
*   **Resolution:** Created `tests/transport/test_capability_routes.py` with **24 integration tests** across 5 test classes:
    -   `TestCapabilityList` (6 tests): no-auth, query filter, pagination, invalid cursor/limit (422), Agent JWT with grant_status
    -   `TestCapabilityDescribe` (3 tests): found, not found (404), missing name (422)
    -   `TestCapabilityExecute` (6 tests): success, no grant (403), constraint violation (403 with violations), no auth (401), invalid JSON (400), invalid body with Pydantic detail (400)
    -   `TestAgentReactivate` (7 tests): success with capability decay, revoked (403), absolute lifetime exceeded (403), wrong host (403), no auth (401), unknown agent (404), invalid body with detail (400)
    -   `TestRegisterWithCapabilities` (2 tests): known caps granted active, unknown cap denied with reason

### Fix #2: Swallowed Exceptions in Request Body Parsing — ✅ RESOLVED

*   **Location:** `src/asap/transport/capability_routes.py:221-222` and `src/asap/transport/capability_routes.py:271-274`
*   **Problem:** Both `_handle_capability_execute` and `_handle_agent_reactivate` use bare `except Exception` when parsing request bodies.
*   **Resolution:** Replaced bare `except Exception` with specific handlers in all 3 locations:
    -   `capability_routes.py` — `_handle_capability_execute`: split into `ValueError` (bad JSON) + `ValidationError` (Pydantic detail via `e.errors()`)
    -   `capability_routes.py` — `_handle_agent_reactivate`: same pattern
    -   `agent_routes.py` — `_handle_agent_register` body parsing: narrowed to `(ValueError, UnicodeDecodeError)`
    -   Added `from pydantic import ValidationError` import and used `model_validate()` instead of `**raw_body`
    -   Verified with `test_execute_invalid_body_returns_400_with_detail` and `test_reactivate_invalid_body_returns_400_with_detail`

### Fix #3: Unvalidated `int()` Cast on Query Parameters — ✅ RESOLVED

*   **Location:** `src/asap/transport/capability_routes.py:148-149`
*   **Problem:** `cursor = int(request.query_params.get("cursor", "0"))` will raise unhandled `ValueError` on `?cursor=abc`, producing a raw 500.
*   **Resolution:** Moved query parameter validation to FastAPI's `Query()` annotations on the router function:
    -   `query: Annotated[str, Query()] = ""`
    -   `cursor: Annotated[int, Query(ge=0)] = 0`
    -   `limit: Annotated[int, Query(ge=1, le=1000)] = 100`
    -   Updated `_handle_capability_list` to accept these as keyword arguments
    -   Verified with `test_list_invalid_cursor_returns_422` and `test_list_invalid_limit_returns_422`

### Fix #4: Duplicated `_bearer_token_from_request` Helper — ✅ RESOLVED

*   **Location:** `src/asap/transport/capability_routes.py:56-60` and `src/asap/transport/agent_routes.py:65-70`
*   **Problem:** Identical function defined in two modules.
*   **Resolution:** Created `src/asap/transport/_auth_helpers.py` with `bearer_token_from_request()`. Removed local definitions from both `capability_routes.py` and `agent_routes.py`, replaced with import from shared module. mypy confirms clean.

---

## 3. Tech-Specific Bug Hunt (Deep Dive)

### A. Concurrency & Reliability

*   [x] **`CapabilityRegistry` has no concurrency protection** — ✅ RESOLVED (documentation approach)
    -   The registry uses plain `dict` for `_definitions` and `_grants`. Under concurrent FastAPI requests, reads and writes are interleaved.
    -   **Resolution:** Added `.. note::` docstring to `CapabilityRegistry` documenting it is intended for single-process deployments and relies on CPython GIL. Multi-worker/multi-instance deployments should use a persistent store. Opted for documentation over `asyncio.Lock` to keep the interface synchronous — the registry is a reference implementation.

*   [x] **Grant lookup in `/capability/list` is O(n) per capability per page** — `capability_routes.py:182-184`
    -   For each capability in the page, `registry.get_grants(agent_id)` returns **all** grants for the agent, then a list comprehension filters to find the matching one. If an agent has 100 grants and the page has 100 capabilities, this is 10,000 iterations. Not a problem today, but worth noting.
    -   **Recommendation (P3):** Add a `get_grant(agent_id, capability)` method to `CapabilityRegistry` for O(1) lookup. Low priority — the current scale won't hit this.

### B. Security & Identity

*   [x] **Lifecycle check integrated correctly** — `agent_jwt.py:314-324`. The `check_agent_expiry` → `extend_session` → `agent_store.save` chain is correct. The `agent_store_writable` flag correctly gates the write, preventing unintended writes during read-only contexts like `/capability/list`.

*   [x] **Reactivation host ownership check** — `capability_routes.py:291-294`. Correctly verifies `host.host_id != agent.host_id` before allowing reactivation. A host cannot reactivate another host's agents.

*   [x] **Grant expiry uses deferred import** — ✅ RESOLVED. Moved `timezone` to the top-level import (`from datetime import datetime, timezone`) and removed the inline `from datetime import timezone` inside `check_grant()`.

*   [x] **`/capability/list` re-verifies Agent JWT without replay cache** — `capability_routes.py:167-173`. The `verify_agent_jwt` call here uses `agent_store_writable=False` (good) but does **not** pass the `jti_replay_cache`. This means the same Agent JWT can be used on `/capability/list` even after being flagged as replayed on another endpoint. This is acceptable for a read-only listing endpoint, but should be documented as intentional.

### C. Tests, Quality & Observability

*   [x] **Unit test coverage is excellent** — ✅ RESOLVED. Added `test_unknown_operator_ignored` and `test_unknown_operator_only_treated_as_exact` to cover the unknown-operator branch in `validate_constraints`.

*   [x] **`agent_routes.py:248` also has bare `except Exception`** — ✅ RESOLVED. Narrowed to `(ValueError, UnicodeDecodeError)` as part of Fix #2.

*   [x] **Logging is appropriate** — `logger.info` on reactivation and registration events includes `agent_id` and `host_id`. No sensitive data (keys, tokens) is logged.

---

## 4. Improvements & Refactoring (Highly Recommended)

*   [ ] **Extract `_verify_host_bearer` and `_verify_agent_bearer` to shared module** — Both `capability_routes.py` and `agent_routes.py` have similar host JWT verification helpers (with slightly different signatures). As Sprint S2 (Approval Flows) and S3 (Streaming) will add more route modules, this duplication will compound. Consider a `src/asap/transport/_jwt_deps.py` with FastAPI dependency injection using `Depends()`.

*   [ ] **`map_scopes_to_capabilities` keyword matching is fragile** — `capabilities.py:329-338`. The scope-to-capability mapping uses substring matching (`"read" in name.lower()`). A capability named `"readonly_config"` would match `asap:read`, which may not be intended. Consider a structured annotation on `CapabilityDefinition` (e.g., `access_level: Literal["read", "write", "admin"] | None`) for explicit classification. Low priority — the current naming convention works, but fragility grows with more capabilities.

*   [ ] **`/asap/capability/list` tries Agent JWT verification on every authenticated request even for Host JWT callers** — `capability_routes.py:167-174`. When a Host JWT is presented, the Agent JWT verification will always fail (wrong `typ`), adding unnecessary latency. Consider peeking at the `typ` header claim first to dispatch to the correct verification flow.

*   [ ] **Capability decay on reactivation iterates twice** — `capability_routes.py:309-317`. First loop denies all existing grants, second loop grants defaults. This is clear and correct but could be a single pass if performance matters later. Fine for now.

---

## 5. Verification Results

All fixes verified on 2026-03-23. Commands and outcomes:

```
# S1 unit + integration tests: 101 passed
uv run pytest tests/auth/test_capabilities.py tests/auth/test_lifecycle.py tests/transport/test_capability_routes.py
→ 101 passed in 0.34s

# mypy on all changed files: clean
uv run mypy src/asap/auth/capabilities.py src/asap/auth/lifecycle.py \
  src/asap/auth/agent_jwt.py src/asap/transport/capability_routes.py \
  src/asap/transport/agent_routes.py src/asap/transport/_auth_helpers.py
→ Success: no issues found in 6 source files

# Full auth regression: clean
uv run pytest tests/auth/ → 227 passed in 3.99s

# Full transport regression: clean
uv run pytest tests/transport/test_server.py → 66 passed in 0.45s
```

### Fix-specific verification
- **Fix #1**: 24 new endpoint tests all pass (test_capability_routes.py)
- **Fix #2**: `test_execute_invalid_body_returns_400_with_detail` confirms Pydantic errors are returned (not swallowed)
- **Fix #3**: `test_list_invalid_cursor_returns_422` + `test_list_invalid_limit_returns_422` confirm 422 (not 500)
- **Fix #4**: Both `capability_routes.py` and `agent_routes.py` import from `_auth_helpers.py`, no local copies remain

---

## 6. PRD Requirement Traceability

| PRD Requirement | Status | Notes |
| :--- | :--- | :--- |
| CAP-001: `CapabilityDefinition` model | ✅ | `capabilities.py:24-39` |
| CAP-002: `CapabilityGrant` model | ✅ | `capabilities.py:42-59` |
| CAP-003: Constraint operators | ✅ | `max`, `min`, `in`, `not_in`, exact — all implemented and tested |
| CAP-004: Constraint enforcement with violations array | ✅ | `validate_constraints` + `GrantCheckResult` |
| CAP-005: `GET /capability/list` | ✅ | Three auth modes (no-auth, Host JWT, Agent JWT) |
| CAP-006: `GET /capability/describe` | ✅ | 404 on unknown capability |
| CAP-007: `POST /capability/execute` | ✅ | Agent JWT + grant check + constraint enforcement |
| CAP-008: OAuth scope backward compat | ✅ | `map_scopes_to_capabilities` |
| CAP-009: Partial approval | ✅ | Registration with unknown caps returns `denied` |
| LIFE-001: Session TTL | ✅ | Clock 1 in `check_agent_expiry` |
| LIFE-002: Max lifetime | ✅ | Clock 2 in `check_agent_expiry` |
| LIFE-003: Absolute lifetime | ✅ | Clock 3, returns `revoked` (permanent) |
| LIFE-004: Reactivation endpoint | ✅ | `/asap/agent/reactivate` with capability decay |
| LIFE-005: Session extension on auth | ✅ | `extend_session` called in `verify_agent_jwt` |
