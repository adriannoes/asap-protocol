# Sprint E2: Delegation Tokens

> **Goal**: Trust hierarchies with constrained permissions
> **Prerequisites**: Sprint E1 completed (Metering)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/delegation.py` - Delegation models, scopes, JWT creation (create_delegation_jwt)
- `src/asap/economics/delegation_storage.py` - DelegationStorage, IssuedSummary, list_issued_summaries, get_issued_at, get_revoked_at
- `src/asap/economics/__init__.py` - Exports (create_delegation_jwt, DelegationToken, DelegationStorage, etc.)
- `src/asap/cli.py` - `asap delegation create`, `asap delegation revoke` commands
- `src/asap/transport/delegation_api.py` - POST/GET/DELETE /asap/delegations (create_delegation_router)
- `src/asap/transport/server.py` - create_app(..., delegation_key_store=...), include delegation router
- `tests/economics/test_delegation.py` - Delegation tests (model, scopes, JWT creation and signature)
- `tests/economics/test_delegation_storage.py` - Revocation storage tests (InMemory, SQLite, persistence)
- `tests/transport/test_delegation_api.py` - Delegation API tests (POST /asap/delegations, auth)

---

## Context

Delegation tokens allow agents to grant limited permissions to other agents. This enables trust hierarchies where a principal agent can delegate specific capabilities with constraints.

**Key Changes from Feedback**:
- **Persistence**: Revocations are stored in SQLite (not just memory).
- **Format**: Using standard JWT (RFC 7519) with EdDSA signatures.
- **Integration**: Validation checks `MeteringStorage` for usage limits.
- **Visibility**: New endpoints to list/inspect issued delegations.

---

## Task 2.1: Delegation Token Model

**Goal**: Token with scopes, constraints, signature

### Sub-tasks

- [x] 2.1.1 Create delegation module
  - **File**: `src/asap/economics/delegation.py`

- [x] 2.1.2 Define DelegationToken model
  ```python
  class DelegationToken(BaseModel):
      id: str
      delegator: str  # URN
      delegate: str   # URN
      scopes: List[str]
      constraints: DelegationConstraints
      signature: str
      created_at: datetime

  class DelegationConstraints(BaseModel):
      max_cost_usd: Optional[float]  # Reserved for v3.0 (Payments)
      max_tasks: Optional[int]       # Primary limit for v2.0 (Free)
      expires_at: datetime
  ```

- [x] 2.1.3 Define scope vocabulary
  - `*` = all permissions
  - `task.execute`, `task.cancel`
  - `data.read`, `data.write`

- [x] 2.1.4 Write tests
  - Model validation
  - Scope parsing

- [x] 2.1.5 Commit
  - **Command**: `git commit -m "feat(economics): add delegation token model"`

**Acceptance Criteria**:
- [x] Token model defined and validated

---

## Task 2.2: Token Creation and Signing

**Goal**: Create tokens signed by delegator

### Sub-tasks

- [x] 2.2.1 Implement token creation
  - Use delegator's Ed25519 key (from v1.2)
  - **Security**: Serialize with JCS before signing
  - Sign token content

- [x] 2.2.2 Implement CLI command
  - `asap delegation create --delegate URN --scopes x,y`
  - Output: signed token

- [x] 2.2.3 Implement API endpoint
  - POST /delegations
  - Requires delegator auth

- [x] 2.2.4 Use Standard JWT format
  - **Standard**: RFC 7519 (JWT)
  - **Algorithm**: EdDSA (using `asap.auth` or `cryptography` lib)
  - **Claims**: `iss` (delegator), `aud` (delegate), `exp`, `jti` (id), `scp` (scopes), `x-constraints`

- [x] 2.2.5 Write tests
  - Token creation
  - Signature validity

- [x] 2.2.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation token creation"`

**Acceptance Criteria**:
- [x] Tokens can be created and signed

---

## Task 2.3: Token Validation

**Goal**: Verify chain, constraints, expiration

### Sub-tasks

- [x] 2.3.1 Implement validation function
  ```python
  def validate_delegation(token: str, action: str) -> ValidationResult:
      # Check Ed25519 signature (Strict Verification)
      # Check expiration
      # Check scope includes action
      # Check constraints (cost, tasks)
  ```

- [x] 2.3.2 Add middleware integration
  - Extract delegation from request header
  - Validate before handler execution

- [x] 2.3.3 Integrate validation with MeteringStorage
  - **Goal**: Enforce `max_tasks` limit
  - **Logic**: Query `MeteringStorage` for usage by this token/delegate
  - Reject if usage >= limit

- [x] 2.3.4 Implement chain validation
  - Delegator must have permission to delegate
  - No privilege escalation

- [x] 2.3.5 Write tests
  - Valid tokens pass
  - Expired rejected
  - Over-limit rejected
  - Escalation rejected

- [x] 2.3.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation validation"`

**Acceptance Criteria**:
- [x] Validation enforces all constraints

---

## Task 2.4: Token Revocation

**Goal**: Revoke tokens with immediate effect

### Sub-tasks

- [x] 2.4.1 Implement revocation storage
  - **Store**: SQLite table `revocations` (id, revoked_at, reason)
  - **Interface**: `DelegationStorage.is_revoked(token_id)`
  - **Persistence**: Survives restarts

- [x] 2.4.2 Implement revocation API
  - DELETE /delegations/{id}
  - Requires delegator auth

- [x] 2.4.3 Implement CLI command
  - `asap delegation revoke TOKEN_ID`

- [x] 2.4.4 Add propagation
  - Child delegations also revoked
  - Cascade through chain

- [x] 2.4.5 Write tests
  - Revoked tokens rejected
  - Cascade works

- [x] 2.4.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation revocation"`

**Acceptance Criteria**:
- [x] Revocation is immediate and persistent
- [x] Cascade works correctly

---

## Task 2.5: Observability for Delegations

**Goal**: Allow agents to see what they have delegated

### Sub-tasks

- [x] 2.5.1 Implement GET /delegations
  - **Goal**: List active delegations issued by the authenticated agent
  - **Filter**: `?active=true` (default)
  - **Response**: List of DelegationTokenSummary

- [x] 2.5.2 Implement GET /delegations/{id}
  - **Goal**: Inspect full details of a specific token
  - **Security**: Only issuer or holder can view

- [x] 2.5.3 Write tests
  - List returns correct tokens
  - Access control prevents unauthorized viewing

- [x] 2.5.4 Commit
  - **Command**: `git commit -m "feat(economics): add delegation list api"`

**Acceptance Criteria**:
- [x] Agents can list their issued tokens
- [x] Agents can inspect token details

---

## Sprint E2 Definition of Done

- [x] Delegation tokens work with constraints (JWT/EdDSA)
- [x] Validation enforces all rules (integrated with Metering)
- [x] Revocation immediate and PERSISTENT
- [x] Agents can list/inspect delegations
- [x] Test coverage >95%

**Total Sub-tasks**: ~23

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v1.3.0 Roadmap](./tasks-v1.3.0-roadmap.md)
