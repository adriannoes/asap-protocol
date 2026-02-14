# Sprint E1: Usage Metering

> **Goal**: Track and store usage metrics for billing
> **Prerequisites**: v1.2.0 completed (PKI, Registry, Compliance)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/__init__.py` - Economics module init
- `src/asap/economics/metering.py` - Metering implementation
- `src/asap/economics/storage.py` - Time-series storage
- `tests/economics/__init__.py` - Economics test package
- `tests/economics/test_metering.py` - Metering tests

---

## Context

Metering enables billing for agent-to-agent interactions. It tracks tokens, API calls, and duration. This is the foundation for the Agent Marketplace's pay-per-use model.

---

## Task 1.1: Metering Data Model

**Goal**: Define metrics schema for tracking usage

### Sub-tasks

- [ ] 1.1.1 Create economics module structure
  - **Directory**: `src/asap/economics/`
  - **Files**: `__init__.py`, `metering.py`

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
  - **Command**: `git commit -m "feat(economics): add metering data model"`

**Acceptance Criteria**:
- [ ] Data models defined and tested

---

## Task 1.2: Metering Hooks

**Goal**: Capture metrics during task execution

### Sub-tasks

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
  - **Command**: `git commit -m "feat(economics): add metering hooks"`

**Acceptance Criteria**:
- [ ] Metrics captured automatically

---

## Task 1.3: Metering Storage

**Goal**: Store and query usage data

### Sub-tasks

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
  - **Command**: `git commit -m "feat(economics): add metering storage"`

**Acceptance Criteria**:
- [ ] Storage operations work correctly

---

## Task 1.4: Metering API

**Goal**: REST API for querying usage

### Sub-tasks

- [ ] 1.4.1 Implement GET /usage
  - Query params: agent, consumer, start, end
  - Pagination support

- [ ] 1.4.2 Implement GET /usage/aggregate
  - Group by: agent, consumer, day, week
  - Return totals

- [ ] 1.4.3 Implement POST /usage (for agents)
  - Agents report their own metrics
  - **Security**: Validate Ed25519 signature (Strict Mode)
  - **Security**: Verify `agent_id` matches signer

- [ ] 1.4.4 Add export endpoints
  - GET /usage/export?format=csv
  - GET /usage/export?format=json

- [ ] 1.4.5 Write integration tests

- [ ] 1.4.6 Commit
  - **Command**: `git commit -m "feat(economics): add metering API"`

**Acceptance Criteria**:
- [ ] Usage queryable via API
- [ ] Export works

---

## Sprint E1 Definition of Done

- [ ] Metering data models defined
- [ ] Hooks capture metrics automatically
- [ ] Storage and query working
- [ ] API endpoints functional
- [ ] Test coverage >95%

**Total Sub-tasks**: ~22

## Documentation Updates
- [ ] **Update Roadmap**: Mark completed items in [v1.3.0 Roadmap](./tasks-v1.3.0-roadmap.md)
