# Sprint E2: Delegation Tokens

> **Goal**: Trust hierarchies with constrained permissions
> **Prerequisites**: Sprint E1 completed (Metering)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/delegation.py` - Delegation implementation
- `tests/economics/test_delegation.py` - Delegation tests

---

## Context

Delegation tokens allow agents to grant limited permissions to other agents. This enables trust hierarchies where a principal agent can delegate specific capabilities with constraints.

---

## Task 2.1: Delegation Token Model

**Goal**: Token with scopes, constraints, signature

### Sub-tasks

- [ ] 2.1.1 Create delegation module
  - **File**: `src/asap/economics/delegation.py`

- [ ] 2.1.2 Define DelegationToken model
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
      max_cost_usd: Optional[float]
      max_tasks: Optional[int]
      expires_at: datetime
  ```

- [ ] 2.1.3 Define scope vocabulary
  - `*` = all permissions
  - `task.execute`, `task.cancel`
  - `data.read`, `data.write`

- [ ] 2.1.4 Write tests
  - Model validation
  - Scope parsing

- [ ] 2.1.5 Commit
  - **Command**: `git commit -m "feat(economics): add delegation token model"`

**Acceptance Criteria**:
- [ ] Token model defined and validated

---

## Task 2.2: Token Creation and Signing

**Goal**: Create tokens signed by delegator

### Sub-tasks

- [ ] 2.2.1 Implement token creation
  - Use delegator's Ed25519 key (from v1.2)
  - **Security**: Serialize with JCS before signing
  - Sign token content

- [ ] 2.2.2 Implement CLI command
  - `asap delegation create --delegate URN --scopes x,y`
  - Output: signed token

- [ ] 2.2.3 Implement API endpoint
  - POST /delegations
  - Requires delegator auth

- [ ] 2.2.4 Add token serialization
  - Base64 compact format
  - JWT-like structure (header.payload.signature)

- [ ] 2.2.5 Write tests
  - Token creation
  - Signature validity

- [ ] 2.2.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation token creation"`

**Acceptance Criteria**:
- [ ] Tokens can be created and signed

---

## Task 2.3: Token Validation

**Goal**: Verify chain, constraints, expiration

### Sub-tasks

- [ ] 2.3.1 Implement validation function
  ```python
  def validate_delegation(token: str, action: str) -> ValidationResult:
      # Check Ed25519 signature (Strict Verification)
      # Check expiration
      # Check scope includes action
      # Check constraints (cost, tasks)
  ```

- [ ] 2.3.2 Add middleware integration
  - Extract delegation from request header
  - Validate before handler execution

- [ ] 2.3.3 Implement constraint tracking
  - Track spent cost against max_cost
  - Track used tasks against max_tasks

- [ ] 2.3.4 Implement chain validation
  - Delegator must have permission to delegate
  - No privilege escalation

- [ ] 2.3.5 Write tests
  - Valid tokens pass
  - Expired rejected
  - Over-limit rejected
  - Escalation rejected

- [ ] 2.3.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation validation"`

**Acceptance Criteria**:
- [ ] Validation enforces all constraints

---

## Task 2.4: Token Revocation

**Goal**: Revoke tokens with immediate effect

### Sub-tasks

- [ ] 2.4.1 Implement revocation list
  - Store revoked token IDs
  - Check during validation

- [ ] 2.4.2 Implement revocation API
  - DELETE /delegations/{id}
  - Requires delegator auth

- [ ] 2.4.3 Implement CLI command
  - `asap delegation revoke TOKEN_ID`

- [ ] 2.4.4 Add propagation
  - Child delegations also revoked
  - Cascade through chain

- [ ] 2.4.5 Write tests
  - Revoked tokens rejected
  - Cascade works

- [ ] 2.4.6 Commit
  - **Command**: `git commit -m "feat(economics): add delegation revocation"`

**Acceptance Criteria**:
- [ ] Revocation is immediate
- [ ] Cascade works correctly

---

## Sprint E2 Definition of Done

- [ ] Delegation tokens work with constraints
- [ ] Validation enforces all rules
- [ ] Revocation immediate
- [ ] Test coverage >95%

**Total Sub-tasks**: ~23
