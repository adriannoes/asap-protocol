# Sprint S2: Approval Flows & Self-Authorization Prevention

**PRD**: §4.4 Approval Flows (P1), §4.5 Self-Authorization Prevention (P1)
**Branch**: `feat/approval-flows`
**PR Scope**: Device Authorization (RFC 8628), CIBA, approval polling, WebAuthn integration, fresh session enforcement
**Depends on**: Sprint S1 (Capabilities & Lifecycle)

## Relevant Files

### New Files
- `src/asap/auth/approval.py` — Approval object schema, Device Auth flow, CIBA flow, method selection
- `src/asap/auth/self_auth.py` — Fresh session enforcement, WebAuthn integration, threat model docs
- `tests/auth/test_approval.py` — Approval flow tests
- `tests/auth/test_self_auth.py` — Self-auth prevention tests

### Modified Files
- `src/asap/transport/server.py` — Approval-aware registration, status polling with grants
- `src/asap/auth/identity.py` — `AgentSession` status transitions for approval (pending → active/rejected)

---

## Tasks

### 1.0 Approval Object & Device Authorization

- [ ] 1.1 Create `ApprovalObject` model
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

- [ ] 1.2 Implement Device Authorization flow (RFC 8628)
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**:
    - `ApprovalStore` Protocol — `async def create(agent_id, method, ...)`, `async def get(agent_id)`, `async def approve(agent_id, user_id)`, `async def deny(agent_id, reason)`
    - `InMemoryApprovalStore` implementation
    - `create_device_authorization(agent_id, capabilities)` — Generates `user_code` (8 chars, uppercase alphanumeric), stores approval request, returns `ApprovalObject`
    - `check_approval_status(agent_id)` — Returns current status (pending/approved/denied/expired)
  - **Verify**: Create → poll → approve → status is active

- [ ] 1.3 Implement CIBA flow (basic)
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**:
    - `create_ciba_approval(agent_id, capabilities, binding_message=None)` — Creates approval request with `method: "ciba"`. Returns `ApprovalObject` with `binding_message`.
    - Server-side approval: same `approve()`/`deny()` interface as Device Auth
    - CIBA doesn't have a `verification_uri` — the server pushes notification through its own channel
  - **Verify**: Create → approve → status is active

- [ ] 1.4 Implement approval method selection
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**: `select_approval_method(host, agent, preferred_method=None)` — If host is linked (has `user_id`) and CIBA supported → CIBA. Otherwise → Device Authorization. `preferred_method` hint is considered but server decides.
  - **Verify**: Method selection logic with linked/unlinked hosts

- [ ] 1.5 Write approval tests
  - **File**: `tests/auth/test_approval.py` (create)
  - **What**: Tests for Device Auth flow (create → poll → approve/deny), CIBA flow, method selection, expiry, idempotent re-registration (pending agent returns existing state), `user_code` format validation.
  - **Verify**: `uv run pytest tests/auth/test_approval.py`

### 2.0 Integrate Approval into Registration

- [ ] 2.1 Update `/asap/agent/register` with approval flow
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: When agent registration requires approval (host not trusted or capabilities need consent), return `status: "pending"` with `approval` object. When host is trusted and capabilities are within defaults, return `status: "active"` directly (auto-approve).
  - **Verify**: Registration with trusted host (auto-approve), untrusted host (approval required)

- [ ] 2.2 Update `/asap/agent/status` with approval polling
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: When agent is `pending`, status endpoint returns current approval state. When approved, status changes to `active` with full capability grants. When denied, status changes to `rejected`.
  - **Verify**: Polling sequence: pending → active (approved) or rejected (denied)

- [ ] 2.3 Integrate A2H as approval channel
  - **File**: `src/asap/auth/approval.py` (extend)
  - **What**: `A2HApprovalChannel` — Uses existing `A2HApprovalProvider` from `asap.integrations.a2h` to send approval requests via A2H Gateway. Maps A2H `ApprovalResult` back to approval store status.
  - **Verify**: Integration test with mocked A2H gateway

### 3.0 Self-Authorization Prevention

- [ ] 3.1 Implement fresh session enforcement
  - **File**: `src/asap/auth/self_auth.py` (create)
  - **What**:
    - `FreshSessionConfig` — `window_seconds: int = 300`, `require_webauthn_for: list[str] = []` (capability names requiring WebAuthn)
    - `check_fresh_session(session_timestamp, config)` — Returns True if session is within `window_seconds`. Stale sessions must re-authenticate.
    - Middleware/dependency for approval endpoints that rejects stale sessions
  - **Verify**: Fresh session accepted, stale session rejected

- [ ] 3.2 Add WebAuthn verification hook
  - **File**: `src/asap/auth/self_auth.py` (extend)
  - **What**: `WebAuthnVerifier` Protocol — `async def verify(challenge, response) -> bool`. Placeholder implementation that always returns True (actual WebAuthn library integration is optional). Config: `require_webauthn_for` list of capability names that need proof-of-presence.
  - **Verify**: Protocol is runtime-checkable, placeholder works

- [ ] 3.3 Document threat model
  - **File**: `docs/security/self-authorization-prevention.md` (create)
  - **What**: Document the self-authorization threat (agents controlling browser auto-approve), mitigations (fresh auth, WebAuthn, CIBA preference, hardware keys), and configuration guidance.
  - **Verify**: Document exists and covers all mitigations from PRD §4.5

- [ ] 3.4 Write self-auth prevention tests
  - **File**: `tests/auth/test_self_auth.py` (create)
  - **What**: Tests for fresh session check (within window, outside window), WebAuthn verifier protocol conformance, CIBA preference for browser-controlling agents.
  - **Verify**: `uv run pytest tests/auth/test_self_auth.py`

---

## Definition of Done

- [ ] Device Authorization flow (RFC 8628) operational: create → poll → approve/deny
- [ ] CIBA flow operational: create → push notification → approve/deny
- [ ] Approval method selection logic working
- [ ] Registration returns approval object when consent required
- [ ] Status polling reflects approval state changes
- [ ] A2H integrated as approval channel
- [ ] Fresh session enforcement on approval endpoints
- [ ] WebAuthn verifier protocol defined (placeholder impl)
- [ ] Threat model documented
- [ ] Test coverage >= 90% for new code
