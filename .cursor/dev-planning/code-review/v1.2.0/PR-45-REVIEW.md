# Code Review: Sprint T3 - ASAP Compliance Harness

## 1. Executive Summary
| Metric | Assessment |
| :--- | :--- |
| **Architecture** | ✅ Aligned / Fixed |
| **Test Coverage** | ✅ Solid (53 Tests Passed) |
| **Blocking Issues** | 0 (All resolved) |

## 2. Architecture & Stack Violations (Critical)
*Strict enforcement of `tech-stack-decisions.md`.*

### [Invalid State Machine Compliance Strategy]
* **File:** `asap-compliance/asap_compliance/validators/state.py`
* **Rule Broken:** "Protocol Compliance (Shell)" - The harness must test the **remote agent's** compliance.
* **Status:** ✅ **RESOLVED**.
* **Fix Verification:** The validator now performs black-box testing by sending `TaskRequest` to the agent and observing the `TaskResponse` status. It no longer imports `asap.state.machine`.

### [Implicit Protocol Dependnecy]
* **File:** `asap-compliance/asap_compliance/validators/sla.py`
* **Rule Broken:** Compliance Harness must be agent-agnostic.
* **Status:** ✅ **RESOLVED**.
* **Fix Verification:** `skill_id` is now configurable via `ComplianceConfig.sla_skill_id` (default: "echo").

## 3. Red Team Findings (Bugs & Logic)
Race conditions, error swallowing, and edge cases.

### [Unsafe Sync Wrapper]
- **Location:** `asap-compliance/asap_compliance/validators/handshake.py`
- **Status:** ✅ **RESOLVED**.
- **Fix Verification:** Sync wrappers now raise `RuntimeError` if called from within a running event loop.

### [Unsafe URL Construction]
- **Location:** `asap-compliance/asap_compliance/validators/handshake.py`
- **Status:** ✅ **RESOLVED**.
- **Fix Verification:** Using `urllib.parse.urljoin` for safe path concatenation.

## 4. QA & Test Health
**Coverage Gaps:**
- `asap-compliance/tests/test_state.py`: Tests the *validator*, which tests the *library*. It does not test the validator against a *bad agent* because the validator never talks to the agent.
- **Missing:** Tests where the agent sends *invalid* state transitions (e.g. mocking a bad agent that goes `COMPLETED` -> `WORKING`). Currently impossible because `state.py` doesn't look at the agent.

**Fixture Issues:**
- `asap-compliance/tests/conftest.py` is minimal.
- `asap-compliance/tests/test_handshake.py` defines its own `good_agent_app`. Consider moving this to a shared fixture in `conftest.py` so other tests can reuse the "Reference Implementation Agent".

**Verification Command:** `uv run pytest asap-compliance`

## 5. Refactoring & Nitpicks
- **Type Safety**: `asap-compliance/asap_compliance/validators/schema.py:103` returns `type | None`. Callers check for None, but explicit `Optional[type]` is clearer.
- **Config**: `ComplianceConfig` should allow disabling specific checks (e.g. "Skip SLA check" if I know I'm slow).
