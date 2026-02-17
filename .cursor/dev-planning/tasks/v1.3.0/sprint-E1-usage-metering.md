# Sprint E1: Usage Metering

> **Goal**: Track and store usage metrics for visibility and transparency (No Payments)
> **Prerequisites**: v1.2.0 completed (PKI, Registry, Compliance)
> **Parent Roadmap**: [tasks-v1.3.0-roadmap.md](./tasks-v1.3.0-roadmap.md)

---

## Relevant Files

- `src/asap/economics/__init__.py` - Economics module init
- `src/asap/economics/metering.py` - Metering models (UsageMetrics, UsageSummary, BatchUsageRequest, StorageStats, aggregation)
- `src/asap/economics/hooks.py` - Metering hooks (record_task_usage, wrap_handler_with_metering)
- `src/asap/economics/storage.py` - MeteringStorage interface, InMemory/SQLite implementations
- `src/asap/transport/handlers.py` - HandlerRegistry + metering_store integration
- `src/asap/transport/server.py` - create_app + metering_store + metering_storage
- `src/asap/transport/usage_api.py` - Usage REST API routes
- `tests/economics/__init__.py` - Economics test package
- `tests/economics/test_metering.py` - Metering model tests
- `tests/economics/test_metering_hooks.py` - Metering hooks + integration tests
- `tests/economics/test_storage.py` - MeteringStorage + retention policy tests
- `tests/economics/test_usage_api.py` - Usage API integration tests

---

## Context

Metering enables visibility for agent-to-agent interactions. It tracks tokens, API calls and duration. This provides transparency for the "Lean Marketplace" (v2.0) so users can monitor consumption, even though the service is free. Financial billing is deferred to v3.0.

---

## Task 1.1: Metering Data Model

**Goal**: Define metrics schema for tracking usage

### Sub-tasks

- [x] 1.1.1 Create economics module structure
  - **Directory**: `src/asap/economics/`
  - **Files**: `__init__.py`, `metering.py`

- [x] 1.1.2 Define UsageMetrics model
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

- [x] 1.1.3 Define aggregation models
  - By agent, by consumer, by time period
  - Totals and averages

- [x] 1.1.4 Write tests
  - Model validation
  - Aggregation correctness

- [ ] 1.1.5 Commit 
  - **Command**: `git commit -m "feat(economics): add metering data model"`

**Acceptance Criteria**:
- [x] Data models defined and tested

---

## Task 1.2: Metering Hooks

**Goal**: Capture metrics during task execution

### Sub-tasks

- [x] 1.2.1 Create metering middleware
  - Intercept task start/end
  - Track timing automatically

- [x] 1.2.2 Implement token counting hook
  - Hook into LLM calls (if applicable)
  - Or accept reported metrics from agent

- [x] 1.2.3 Implement API call counting
  - Count external API calls
  - Track per-task

- [x] 1.2.4 Integrate with task lifecycle
  - Emit usage event on task complete
  - Include all metrics

- [x] 1.2.5 Write tests
  - Middleware captures correctly
  - No double-counting

- [ ] 1.2.6 Commit
  - **Command**: `git commit -m "feat(economics): add metering hooks"`

**Acceptance Criteria**:
- [x] Metrics captured automatically

---

## Task 1.3: Metering Storage

**Goal**: Store and query usage data

### Sub-tasks

- [x] 1.3.1 Define storage interface
  ```python
  class MeteringStorage(ABC):
      async def record(self, metrics: UsageMetrics) -> None
      async def query(self, filters: MeteringQuery) -> List[UsageMetrics]
      async def aggregate(self, group_by: str) -> List[UsageAggregate]
  ```

- [x] 1.3.2 Implement in-memory storage
  - For development/testing

- [x] 1.3.3 Implement SQLite storage
  - Time-series optimized schema
  - Indexed by agent, consumer, timestamp

- [x] 1.3.4 Add retention policy
  - Configurable TTL
  - Auto-cleanup old data

- [x] 1.3.5 Write tests
  - Storage operations
  - Query filtering
  - Aggregation

- [ ] 1.3.6 Commit
  - **Command**: `git commit -m "feat(economics): add metering storage"`

**Acceptance Criteria**:
- [x] Storage operations work correctly

---

## Task 1.4: Metering API

**Goal**: REST API for querying usage

### Sub-tasks

- [x] 1.4.1 Implement GET /usage
  - Query params: agent, consumer, start, end
  - Pagination support

- [x] 1.4.2 Implement GET /usage/aggregate
  - Group by: agent, consumer, day, week
  - Return totals

- [x] 1.4.3 Implement POST /usage (for agents)
  - Agents report their own metrics
  - **Security**: Ed25519 signature validation deferred to Strict Mode

- [x] 1.4.4 Add export endpoints
  - GET /usage/export?format=csv
  - GET /usage/export?format=json

- [x] 1.4.5 Write integration tests

- [x] 1.4.6 Extend GET /usage/aggregate with start/end
  - Optional query params: start, end (time range for aggregation)
  - Enables "last 7 days", "February 2026", etc.

- [x] 1.4.7 Implement GET /usage/summary
  - Returns total_tasks, total_tokens, total_duration_ms, unique_agents, unique_consumers
  - Optional start/end for period
  - Dashboard "at a glance" view

- [x] 1.4.8 Implement POST /usage/batch
  - Accept `{"events": [UsageMetrics, ...]}`
  - Bulk upload for agents with accumulated metrics
  - Foundation for v2.0 "report to marketplace"

- [x] 1.4.9 Add task_id filter to GET /usage
  - Query param: task_id (or path GET /usage/{task_id})
  - Lookup usage for specific task (debug, tracing)

- [x] 1.4.10 Implement GET /usage/agents
  - List distinct agent_id with usage
  - For dropdowns, filters in UI

- [x] 1.4.11 Implement GET /usage/consumers
  - List distinct consumer_id with usage
  - Same use case as agents

- [x] 1.4.12 Implement GET /usage/stats
  - Storage stats: total events, oldest record, retention status
  - Ops monitoring

- [x] 1.4.13 Implement POST /usage/purge
  - Trigger purge_expired() manually
  - For scheduled jobs or admin
  - **Security**: Consider auth (admin-only)

- [x] 1.4.14 Implement POST /usage/validate
  - Validate UsageMetrics payload without persisting
  - Returns validation result (debug, pre-flight)

- [x] 1.4.15 Write integration tests for new endpoints

- [ ] 1.4.16 Commit
  - **Command**: `git commit -m "feat(economics): add metering API"`

**Acceptance Criteria**:
- [x] Usage queryable via API
- [x] Export works
- [x] Summary, batch, task lookup, agents/consumers lists, stats, purge, validate

---

## Sprint E1 Definition of Done

- [x] Metering data models defined
- [x] Hooks capture metrics automatically
- [x] Storage and query working
- [x] API endpoints functional
- [ ] Test coverage >95%

**Total Sub-tasks**: ~31

## Documentation Updates
- [x] **Update Roadmap**: Mark completed items in [v1.3.0 Roadmap](./tasks-v1.3.0-roadmap.md)
- [x] **v2.0 Foundation**: [v2.0-marketplace-usage-foundation.md](../v2.0.0/v2.0-marketplace-usage-foundation.md) — Storage location, control model, evolution path to marketplace
