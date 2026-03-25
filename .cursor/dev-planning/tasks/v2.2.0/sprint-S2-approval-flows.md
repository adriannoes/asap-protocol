# Sprint S2: Approval Flows & Self-Authorization Prevention

**PRD**: §4.4 Approval Flows (P1), §4.5 Self-Authorization Prevention (P1)
**Branch**: `feat/approval-flows`
**PR Scope**: Device Authorization (RFC 8628), CIBA, approval polling, WebAuthn integration, fresh session enforcement
**Depends on**: Sprint S1 (Capabilities & Lifecycle)

## Relevant Files

### New Files
- `src/asap/auth/approval.py` — Approval object schema, Device Auth flow, CIBA flow, method selection
- `src/asap/auth/self_auth.py` — Fresh session policy, WebAuthn verifier protocol, register-time WebAuthn check helpers
- `tests/auth/test_approval.py` — Approval flow tests
- `tests/auth/test_self_auth.py` — Self-auth prevention tests (fresh session, WebAuthn, CIBA preference)
- `docs/security/self-authorization-prevention.md` — Threat model and configuration (PRD §4.5)

### Modified Files
- `src/asap/transport/server.py` — `identity_approval_store`, CIBA/A2H knobs, `identity_fresh_session_config`, `identity_webauthn_verifier` on `create_app`
- `src/asap/transport/agent_routes.py` — Approval-aware `/asap/agent/register` and `/asap/agent/status`; fresh session + WebAuthn on approval paths; `agent_controls_browser` → method selection
- `src/asap/auth/identity.py` — `AgentSession` includes `rejected` status
- `src/asap/auth/agent_jwt.py` — Reject Agent JWT when session is `pending` or `rejected`
- `tests/transport/test_server.py` — Expect `approval` on pending register; auto-approve coverage
- `tests/transport/test_capability_routes.py` — Approve + status sync in helpers; capability register cases
- `tests/auth/test_server_oauth2_integration.py` — Register response includes `approval`

---

## Tasks

### 1.0 Approval Object & Device Authorization

- [x] 1.1 Create `ApprovalObject` model
  - **File**: `src/asap/auth/approval.py` (create)
  - **What**: Pydantic model for the approval object returned in registration/reactivation/escalation responses:
    - `method: Literal["device_authorization", "ciba"]`
    - `verification_uri: str | None` (device_authorization)
    - `verification_uri_complete: str | None` (device_authorization)
    - `user_code: str | None` (device_authorization)
    - `binding_message: str | None` (ciba)
    - `expires_in: int`
    - `interval: int`
    - `ConfigDict(extra="forbid")`
  - **Verify**: Model validates for both device_auth and ciba methods

- [x] 1.2 Implement Device Authorization flow (RFC 8628)
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**:
    - `ApprovalStore` Protocol — `async def create(agent_id, method, ...)`, `async def get(agent_id)`, `async def approve(agent_id, user_id)`, `async def deny(agent_id, reason)`
    - `InMemoryApprovalStore` implementation
    - `create_device_authorization(agent_id, capabilities)` — Generates `user_code` (8 chars, uppercase alphanumeric), stores approval request, returns `ApprovalObject`
    - `check_approval_status(agent_id)` — Returns current status (pending/approved/denied/expired)
  - **Verify**: Create → poll → approve → status is active

- [x] 1.3 Implement CIBA flow (basic)
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**:
    - `create_ciba_approval(agent_id, capabilities, binding_message=None)` — Creates approval request with `method: "ciba"`. Returns `ApprovalObject` with `binding_message`.
    - Server-side approval: same `approve()`/`deny()` interface as Device Auth
    - CIBA doesn't have a `verification_uri` — the server pushes notification through its own channel
  - **Verify**: Create → approve → status is active

- [x] 1.4 Implement approval method selection
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**: `select_approval_method(host, agent, preferred_method=None)` — If host is linked (has `user_id`) and CIBA supported → CIBA. Otherwise → Device Authorization. `preferred_method` hint is considered but server decides.
  - **Verify**: Method selection logic with linked/unlinked hosts

- [x] 1.5 Write approval tests
  - **File**: `tests/auth/test_approval.py` (create)
  - **What**: Tests for Device Auth flow (create → poll → approve/deny), CIBA flow, method selection, expiry, idempotent re-registration (pending agent returns existing state), `user_code` format validation.
  - **Verify**: `uv run pytest tests/auth/test_approval.py`

### 2.0 Integrate Approval into Registration

- [x] 2.1 Update `/asap/agent/register` with approval flow
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: When agent registration requires approval (host not trusted or capabilities need consent), return `status: "pending"` with `approval` object. When host is trusted and capabilities are within defaults, return `status: "active"` directly (auto-approve).
  - **Verify**: Registration with trusted host (auto-approve), untrusted host (approval required)

- [x] 2.2 Update `/asap/agent/status` with approval polling
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: When agent is `pending`, status endpoint returns current approval state. When approved, status changes to `active` with full capability grants. When denied, status changes to `rejected`.
  - **Verify**: Polling sequence: pending → active (approved) or rejected (denied)

- [x] 2.3 Integrate A2H as approval channel
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**: `A2HApprovalChannel` — Uses existing `A2HApprovalProvider` from `asap.integrations.a2h` to send approval requests via A2H Gateway. Maps A2H `ApprovalResult` back to approval store status.
  - **Verify**: Integration test with mocked A2H gateway

### 3.0 Self-Authorization Prevention

- [x] 3.1 Implement fresh session enforcement
  - **File**: `src/asap/auth/self_auth.py` (create)
  - **What**:
    - `FreshSessionConfig` — `window_seconds: int = 300`, `require_webauthn_for: list[str] = []` (capability names requiring WebAuthn)
    - `check_fresh_session(session_timestamp, config)` — Returns True if session is within `window_seconds`. Stale sessions must re-authenticate.
    - Middleware/dependency for approval endpoints that rejects stale sessions
  - **Verify**: Fresh session accepted, stale session rejected

- [x] 3.2 Add WebAuthn verification hook
  - **File**: `src/asap/auth/self_auth.py` (extend)
  - **What**: `WebAuthnVerifier` Protocol — `async def verify(challenge, response) -> bool`. Placeholder implementation that always returns True (actual WebAuthn library integration is optional). Config: `require_webauthn_for` list of capability names that need proof-of-presence.
  - **Verify**: Protocol is runtime-checkable, placeholder works

- [x] 3.3 Document threat model
  - **File**: `docs/security/self-authorization-prevention.md` (create)
  - **What**: Document the self-authorization threat (agents controlling browser auto-approve), mitigations (fresh auth, WebAuthn, CIBA preference, hardware keys), and configuration guidance.
  - **Verify**: Document exists and covers all mitigations from PRD §4.5

- [x] 3.4 Write self-auth prevention tests
  - **File**: `tests/auth/test_self_auth.py` (create)
  - **What**: Tests for fresh session check (within window, outside window), WebAuthn verifier protocol conformance, CIBA preference for browser-controlling agents.
  - **Verify**: `uv run pytest tests/auth/test_self_auth.py`

---

## Definition of Done

- [x] Device Authorization flow (RFC 8628) operational: create → poll → approve/deny
- [x] CIBA flow operational: create → push notification → approve/deny
- [x] Approval method selection logic working
- [x] Registration returns approval object when consent required
- [x] Status polling reflects approval state changes
- [x] A2H integrated as approval channel (`A2HApprovalChannel` + optional `identity_approval_a2h_channel` background resolve)
- [x] Fresh session enforcement on approval endpoints
- [x] WebAuthn verifier protocol defined (placeholder impl)
- [x] Threat model documented
- [x] Test coverage >= 90% for new code (`asap.auth.self_auth` at 100% line/branch in dedicated run)
