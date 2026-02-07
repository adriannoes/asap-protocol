# Tasks: ASAP v1.3.0 Metering & Delegation (E1-E2) - Detailed

> **Sprints**: E1-E2 - Usage Metering and Delegation Tokens
> **Goal**: Economic primitives for billing and trust hierarchies
> **Prerequisites**: v1.2.0 completed (PKI, Registry, Compliance)
> **Estimated Duration**: 2 weeks

---

## Relevant Files

### Sprint E1: Usage Metering
- `src/asap/economics/__init__.py` - Economics module init
- `src/asap/economics/metering.py` - Metering implementation
- `src/asap/economics/storage.py` - Time-series storage
- `tests/economics/test_metering.py` - Metering tests

### Sprint E2: Delegation Tokens
- `src/asap/economics/delegation.py` - Delegation implementation
- `tests/economics/test_delegation.py` - Delegation tests

---

## Sprint E1: Usage Metering

**Context**: Metering enables billing for agent-to-agent interactions. It tracks tokens, API calls, and duration. This is the foundation for the Agent Marketplace's pay-per-use model.

### Task 1.1: Metering Data Model

**Goal**: Define metrics schema for tracking usage

- [ ] 1.1.1 Create economics module structure
  - Directory: `src/asap/economics/`
  - Files: `__init__.py`, `metering.py`

- [ ] 1.1.2 Define UsageMetrics model
  ```python
  class UsageMetrics(BaseModel):
      task_id: str
      agent: str
      consumer: str
      tokens_in: int
      tokens_out: int
      duration_ms: int
      api_calls: int
      timestamp: datetime
  ```

- [ ] 1.1.3 Define aggregation models
  - By agent, by consumer, by time period
  - Totals and averages

- [ ] 1.1.4 Write tests
  - Model validation
  - Aggregation correctness

- [ ] 1.1.5 Commit
  - Command: `git commit -m "feat(economics): add metering data model"`

---

### Task 1.2: Metering Hooks

**Goal**: Capture metrics during task execution

- [ ] 1.2.1 Create metering middleware
  - Intercept task start/end
  - Track timing automatically

- [ ] 1.2.2 Implement token counting hook
  - Hook into LLM calls (if applicable)
  - Or accept reported metrics from agent

- [ ] 1.2.3 Implement API call counting
  - Count external API calls
  - Track per-task

- [ ] 1.2.4 Integrate with task lifecycle
  - Emit usage event on task complete
  - Include all metrics

- [ ] 1.2.5 Write tests
  - Middleware captures correctly
  - No double-counting

- [ ] 1.2.6 Commit
  - Command: `git commit -m "feat(economics): add metering hooks"`

---

### Task 1.3: Metering Storage

**Goal**: Store and query usage data

- [ ] 1.3.1 Define storage interface
  ```python
  class MeteringStorage(ABC):
      async def record(self, metrics: UsageMetrics) -> None
      async def query(self, filters: MeteringQuery) -> List[UsageMetrics]
      async def aggregate(self, group_by: str) -> List[UsageAggregate]
  ```

- [ ] 1.3.2 Implement in-memory storage
  - For development/testing

- [ ] 1.3.3 Implement SQLite storage
  - Time-series optimized schema
  - Indexed by agent, consumer, timestamp

- [ ] 1.3.4 Add retention policy
  - Configurable TTL
  - Auto-cleanup old data

- [ ] 1.3.5 Write tests
  - Storage operations
  - Query filtering
  - Aggregation

- [ ] 1.3.6 Commit
  - Command: `git commit -m "feat(economics): add metering storage"`

---

### Task 1.4: Metering API

**Goal**: REST API for querying usage

- [ ] 1.4.1 Implement GET /usage
  - Query params: agent, consumer, start, end
  - Pagination support

- [ ] 1.4.2 Implement GET /usage/aggregate
  - Group by: agent, consumer, day, week
  - Return totals

- [ ] 1.4.3 Implement POST /usage (for agents)
  - Agents report their own metrics
  - Validate signature

- [ ] 1.4.4 Add export endpoints
  - GET /usage/export?format=csv
  - GET /usage/export?format=json

- [ ] 1.4.5 Write integration tests

- [ ] 1.4.6 Commit
  - Command: `git commit -m "feat(economics): add metering API"`

---

## Sprint E2: Delegation Tokens

### Task 2.1: Delegation Token Model

**Goal**: Token with scopes, constraints, signature

- [ ] 2.1.1 Create delegation module
  - File: `src/asap/economics/delegation.py`

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
  - Command: `git commit -m "feat(economics): add delegation token model"`

---

### Task 2.2: Token Creation and Signing

**Goal**: Create tokens signed by delegator

- [ ] 2.2.1 Implement token creation
  - Use delegator's Ed25519 key (from v1.2)
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
  - Command: `git commit -m "feat(economics): add delegation token creation"`

---

### Task 2.3: Token Validation

**Goal**: Verify chain, constraints, expiration

- [ ] 2.3.1 Implement validation function
  ```python
  def validate_delegation(token: str, action: str) -> ValidationResult:
      # Check signature
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
  - Command: `git commit -m "feat(economics): add delegation validation"`

---

### Task 2.4: Token Revocation

**Goal**: Revoke tokens with immediate effect

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
  - Command: `git commit -m "feat(economics): add delegation revocation"`

---

**E1-E2 Definition of Done**:
- [ ] Metering captures all task metrics
- [ ] Usage queryable via API
- [ ] Delegation tokens work with constraints
- [ ] Revocation immediate
- [ ] Test coverage >95%

**Total Sub-tasks**: ~45
