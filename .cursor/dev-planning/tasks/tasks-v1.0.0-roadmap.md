# Tasks: ASAP Protocol v1.0.0 Roadmap

> Task list for v1.0.0 milestone (Production-Ready Release)
>
> **Parent PRD**: [prd-v1-roadmap.md](../prd/prd-v1-roadmap.md)
> **Prerequisite**: v0.5.0 released
> **Target Version**: v1.0.0
> **Focus**: Complete security + performance + DX + production tooling

---

## Sprint P1: Sensitive Data Protection & Input Validation

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Complete MEDIUM priority security tasks

### 1.1 Log Sanitization

- [ ] 1.1.1 Implement sanitization function
  - **Task Reference**: [Task 7.1](./tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02)
  - **Issue**: [#12](https://github.com/adriannoes/asap-protocol/issues/12)
  - **File**: `src/asap/observability/logging.py`
  - **Function**: `sanitize_for_logging(data: dict[str, Any]) -> dict[str, Any]`
  - **Logic**:
    - Define sensitive patterns: `password`, `token`, `secret`, `key`, `authorization`
    - Recursively sanitize nested dicts
    - Replace with `***REDACTED***`

- [ ] 1.1.2 Apply sanitization to logs
  - **Task Reference**: [Task 7.2](./tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02)
  - **Files**: `src/asap/transport/server.py`, `src/asap/transport/client.py`
  - **Action**: Sanitize envelopes, requests, responses before logging

- [ ] 1.1.3 Add debug mode configuration
  - **Task Reference**: [Task 7.3](./tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02)
  - **Environment Variable**: `ASAP_DEBUG=true`
  - **Behavior**: Show full error details when debug=True

- [ ] 1.1.4 Update error responses
  - **Task Reference**: [Task 7.4](./tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02)
  - **File**: `src/asap/transport/server.py`
  - **Logic**:
    - Production: Generic error messages
    - Debug: Full stack traces
    - Always log full errors server-side

- [ ] 1.1.5 Add sanitization tests
  - **Task Reference**: [Task 7.5](./tasks-security-review-report.md#70-medium-priority---sensitive-data-protection-med-01-med-02)
  - **File**: `tests/observability/test_logging.py`
  - **Tests**:
    - Sensitive keys redacted
    - Nested objects sanitized
    - Non-sensitive data preserved
    - Debug mode exposes full errors
    - Production mode hides details

### 1.2 Handler Security Documentation

- [ ] 1.2.1 Add handler security section
  - **Task Reference**: [Task 8.1](./tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04)
  - **File**: `docs/security.md`
  - **Content**:
    - Input validation requirements
    - Handler security checklist
    - Examples of secure handlers

- [ ] 1.2.2 Add FilePart URI validation
  - **Task Reference**: [Task 8.2](./tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04)
  - **File**: `src/asap/models/parts.py`
  - **Validator**: `validate_uri()` field validator
  - **Checks**:
    - Path traversal detection (../ patterns)
    - Reject file:// URIs with suspicious paths
    - Validate URI format

- [ ] 1.2.3 Add handler validation helpers
  - **Task Reference**: [Task 8.3](./tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04)
  - **File**: `src/asap/transport/handlers.py`
  - **Function**: `validate_handler(handler: Callable) -> None`
  - **Checks**: Handler signature, dangerous modules

- [ ] 1.2.4 Add validation tests
  - **Task Reference**: [Task 8.4](./tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04)
  - **File**: `tests/models/test_parts.py`
  - **Tests**:
    - Path traversal detected
    - Malicious file:// URIs rejected
    - Valid URIs accepted

- [ ] 1.2.5 Update handler examples
  - **Task Reference**: [Task 8.5](./tasks-security-review-report.md#80-medium-priority---input-validation-hardening-med-03-med-04)
  - **File**: `src/asap/examples/secure_handler.py`
  - **Content**: Security-focused handler example

### 1.3 PRD Review Checkpoint

- [ ] 1.3.1 Review PRD Open Questions
  - **PRD Reference**: [Section 11](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Action**: Review security open questions after completing MED priority
  - **Questions to Answer**:
    - Q3: HMAC signing decision (if deferred from v0.5.0)
    - Document as DD-008 or defer to v1.1.0
  - **Deliverable**: Update PRD Section 10

**Definition of Done**:
- [ ] Tokens/secrets redacted from logs
- [ ] Debug mode working (full errors in dev)
- [ ] Path traversal detection working
- [ ] Test coverage >95% maintained
- [ ] Security documentation complete
- [ ] PRD updated with security decisions

---

## Sprint P2: Code Quality & LOW Priority Security

**Duration**: Flexible (estimated 3-4 days)
**Goal**: Complete LOW priority security and code quality improvements

### 2.1 Code Improvements

- [ ] 2.1.1 Improve HandlerRegistry thread safety
  - **Task Reference**: [Task 9.1](./tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03)
  - **File**: `src/asap/transport/handlers.py`
  - **Action**: Copy handler reference before execution
  - **Test**: Concurrent handler registration

- [ ] 2.1.2 Enhance URN validation
  - **Task Reference**: [Task 9.2](./tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03)
  - **File**: `src/asap/models/entities.py`
  - **Validation**:
    - Max length: 256 characters
    - Stricter special character restrictions

- [ ] 2.1.3 Add task depth validation
  - **Task Reference**: [Task 9.3](./tasks-security-review-report.md#90-low-priority---code-improvements-low-01-low-02-low-03)
  - **File**: `src/asap/models/entities.py`
  - **Logic**: Check depth when creating subtasks
  - **Limit**: `MAX_TASK_DEPTH` from constants

### 2.2 Code Quality Audit

- [ ] 2.2.1 Run full code quality audit
  - **Commands**:
    - `uv run ruff check --preview src/ tests/`
    - `uv run mypy --strict src/`
  - **Action**: Address any remaining warnings

**Definition of Done**:
- [ ] All security tasks (CRIT+HIGH+MED+LOW) completed
- [ ] Test coverage >95% maintained
- [ ] mypy --strict passes with zero errors
- [ ] ruff checks pass with zero warnings

---

## Sprint P3: Performance - Connection & Caching

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Implement connection pooling and caching

### 3.1 Connection Pooling

- [ ] 3.1.1 Implement connection pool in ASAPClient
  - **PRD Reference**: Req 12
  - **File**: `src/asap/transport/client.py`
  - **Implementation**: Use httpx connection pools
  - **Config**:
    - `pool_connections: int = 100`
    - `pool_maxsize: int = 100`
    - `pool_timeout: float = 5.0`

- [ ] 3.1.2 Add pool configuration
  - **Parameters**: Add to `ASAPClient.__init__()`
  - **Environment Variables**:
    - `ASAP_POOL_CONNECTIONS`
    - `ASAP_POOL_MAXSIZE`

- [ ] 3.1.3 Benchmark connection pooling
  - **File**: `benchmarks/benchmark_transport.py`
  - **Test**: 1000+ concurrent connections
  - **Target**: <10ms overhead vs raw httpx

### 3.2 Manifest Caching

- [ ] 3.2.1 Implement manifest cache
  - **PRD Reference**: Req 14
  - **File**: `src/asap/transport/cache.py`
  - **Class**: `ManifestCache`
  - **Features**:
    - TTL-based expiration (default: 5 minutes)
    - Automatic invalidation on errors
    - Optional persistent backend

- [ ] 3.2.2 Integrate cache in client
  - **File**: `src/asap/transport/client.py`
  - **Method**: `get_manifest(url: str) -> Manifest`
  - **Logic**: Check cache before HTTP request

- [ ] 3.2.3 Benchmark cache hit rate
  - **Target**: 90% cache hit rate for stable topologies
  - **Measure**: Cache hits / total manifest requests

### 3.3 PRD Review Checkpoint

- [ ] 3.3.1 Review performance open questions
  - **PRD Reference**: [Section 11, Q1](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Action**: Document optimal connection pool size based on benchmarks
  - **Deliverable**: Add DD-008 to PRD Section 10 with recommendations

**Definition of Done**:
- [ ] Connection pooling supports 1000+ concurrent connections
- [ ] Manifest cache achieves 90% hit rate
- [ ] Benchmark results documented
- [ ] No performance regression vs v0.5.0
- [ ] PRD updated with pool size decision (DD-008)

---

## Sprint P4: Performance - Async Batch & Compression

**Duration**: Flexible (estimated 4-6 days)
**Goal**: Implement batch operations and compression

### 4.1 Async Batch Operations

- [ ] 4.1.1 Implement send_batch method
  - **PRD Reference**: Req 13
  - **File**: `src/asap/transport/client.py`
  - **Method**: `async def send_batch(envelopes: list[Envelope]) -> list[Envelope]`
  - **Implementation**: Use `asyncio.gather` for parallel requests

- [ ] 4.1.2 Add batch request pipelining
  - **Action**: Pipeline HTTP requests to reduce latency
  - **Logic**: Use httpx HTTP/2 multiplexing

- [ ] 4.1.3 Benchmark batch operations
  - **File**: `benchmarks/benchmark_transport.py`
  - **Target**: 10x throughput improvement vs sequential

### 4.2 Compression Support

- [ ] 4.2.1 Implement compression
  - **PRD Reference**: Req 15
  - **File**: `src/asap/transport/client.py`
  - **Formats**: gzip, brotli
  - **Threshold**: Default 1KB (configurable)

- [ ] 4.2.2 Add content negotiation
  - **Headers**: `Accept-Encoding`, `Content-Encoding`
  - **Logic**: Automatic compression/decompression

- [ ] 4.2.3 Benchmark compression
  - **Target**: 70% bandwidth reduction for JSON
  - **Measure**: Compressed size / original size

**Definition of Done**:
- [ ] Batch operations achieve 10x throughput improvement
- [ ] Compression reduces bandwidth by 70% for JSON
- [ ] API backward compatible
- [ ] Test coverage >95% maintained

---

## Sprint P5: Developer Experience - Examples & Testing

**Duration**: Flexible (estimated 6-8 days)
**Goal**: Create real-world examples and testing utilities

### 5.1 Real-World Examples

- [ ] 5.1.1 Multi-agent orchestration example
  - **PRD Reference**: Req 16
  - **File**: `src/asap/examples/orchestration.py`
  - **Scenario**: 3+ agents collaborating on a task

- [ ] 5.1.2 Long-running task with checkpoints
  - **File**: `src/asap/examples/long_running.py`
  - **Features**: State snapshots, resume after crash

- [ ] 5.1.3 Error recovery patterns example
  - **File**: `src/asap/examples/error_recovery.py`
  - **Patterns**: Retry, circuit breaker, fallback

- [ ] 5.1.4 MCP tool integration example
  - **File**: `src/asap/examples/mcp_integration.py`
  - **Scenario**: Agent calling MCP tools

- [ ] 5.1.5 State migration example
  - **File**: `src/asap/examples/state_migration.py`
  - **Scenario**: Moving task state between agents

- [ ] 5.1.6 Authentication patterns example
  - **File**: `src/asap/examples/auth_patterns.py`
  - **Patterns**: Bearer, OAuth2, custom validators

- [ ] 5.1.7 Rate limiting strategies example
  - **File**: `src/asap/examples/rate_limiting.py`
  - **Strategies**: Per-sender, per-endpoint

- [ ] 5.1.8 WebSocket notifications concept
  - **File**: `src/asap/examples/websocket_concept.py`
  - **Note**: Conceptual (WebSocket transport not in v1.0)

- [ ] 5.1.9 Add example tests
  - **Files**: `tests/examples/test_*.py`
  - **Action**: Test each example runs successfully

- [ ] 5.1.10 Update README with examples
  - **File**: `README.md`
  - **Section**: Expand "Advanced Examples"

### 5.2 Testing Utilities

- [ ] 5.2.1 Create asap.testing module
  - **PRD Reference**: Req 17
  - **Files**:
    - `src/asap/testing/__init__.py`
    - `src/asap/testing/fixtures.py`
    - `src/asap/testing/mocks.py`
    - `src/asap/testing/assertions.py`

- [ ] 5.2.2 Implement mock agent factory
  - **File**: `src/asap/testing/mocks.py`
  - **Class**: `MockAgent`
  - **Features**: Configurable responses, request recording

- [ ] 5.2.3 Implement snapshot fixtures
  - **File**: `src/asap/testing/fixtures.py`
  - **Fixtures**: `mock_snapshot`, `mock_snapshot_store`

- [ ] 5.2.4 Implement async test context managers
  - **File**: `src/asap/testing/fixtures.py`
  - **Context Managers**: `async with test_agent()`, `async with test_client()`

- [ ] 5.2.5 Add custom assertions
  - **File**: `src/asap/testing/assertions.py`
  - **Functions**: `assert_envelope_valid()`, `assert_task_completed()`

- [ ] 5.2.6 Document testing utilities
  - **File**: `docs/testing.md`
  - **Content**: Usage examples, API reference

### 5.3 PRD Review Checkpoint

- [ ] 5.3.1 Review DX open questions
  - **PRD Reference**: [Section 11, Q4, Q6](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Questions to Answer**:
    - Q4: Default auth scheme for examples (Bearer, OAuth2, or both?)
    - Q6: Should we create pytest-asap plugin? (assess utilities usage)
  - **Deliverable**: Add DD-009 to PRD for auth scheme decision

**Definition of Done**:
- [ ] 10+ production-ready examples
- [ ] Testing utilities reduce boilerplate by 50%
- [ ] All examples have passing tests
- [ ] README showcases example variety
- [ ] PRD updated with DX decisions (DD-009)

---

## Sprint P6: Developer Experience - Debugging Tools

**Duration**: Flexible (estimated 4-5 days)
**Goal**: Build debugging and development tools

### 6.1 Trace Visualization

- [ ] 6.1.1 Implement trace command
  - **PRD Reference**: Req 18
  - **File**: `src/asap/cli.py`
  - **Command**: `asap trace [trace-id]`
  - **Output**: ASCII diagram showing request flow

- [ ] 6.1.2 Add timing information
  - **Action**: Display latency for each hop
  - **Format**: `Agent A -> Agent B (15ms) -> Agent C (23ms)`

- [ ] 6.1.3 Optional web UI
  - **File**: `src/asap/observability/trace_ui.py`
  - **Framework**: FastAPI + htmx (lightweight)
  - **Features**: Interactive trace exploration

### 6.2 Development Server Improvements

- [ ] 6.2.1 Implement hot reload for handlers
  - **PRD Reference**: Req 19
  - **File**: `src/asap/transport/server.py`
  - **Library**: Use watchfiles for file monitoring

- [ ] 6.2.2 Add debug logging mode
  - **Environment Variable**: `ASAP_DEBUG_LOG=true`
  - **Behavior**: Detailed request/response logging

- [ ] 6.2.3 Add built-in REPL
  - **Command**: `asap repl`
  - **Features**: Test payloads interactively

- [ ] 6.2.4 Add Swagger UI
  - **File**: `src/asap/transport/server.py`
  - **Endpoint**: `/docs` (FastAPI built-in)
  - **Action**: Enable in debug mode

### 6.3 PRD Review Checkpoint

- [ ] 6.3.1 Review debugging tool questions
  - **PRD Reference**: [Section 11, Q5](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Question to Answer**:
    - Q5: Should trace CLI support JSON export?
    - Gather feedback from implementation experience
  - **Deliverable**: Decide and implement if valuable, or defer to v1.1.0

**Definition of Done**:
- [ ] Trace command visualizes request flow
- [ ] Hot reload works for handler changes
- [ ] Debug mode provides detailed logging
- [ ] Documentation includes debugging guide
- [ ] PRD updated with trace export decision

---

## Sprint P7: Testing Enhancements - Property & Load Tests

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Expand test coverage with advanced techniques

### 7.1 Property-Based Testing

- [ ] 7.1.1 Add Hypothesis dependency
  - **PRD Reference**: Req 20
  - **Action**: `uv add --dev hypothesis>=6.92`

- [ ] 7.1.2 Implement property tests for models
  - **File**: `tests/models/test_properties.py`
  - **Tests**:
    - Serialization roundtrip (model -> JSON -> model)
    - Envelope validation properties
    - State machine invariants

- [ ] 7.1.3 Implement fuzz testing
  - **File**: `tests/fuzz/test_envelope_fuzz.py`
  - **Tests**: Fuzz envelope validation with random data

- [ ] 7.1.4 Target: 100+ property tests
  - **Goal**: Cover all Pydantic models

### 7.2 Load & Stress Testing

- [ ] 7.2.1 Add Locust dependency
  - **PRD Reference**: Req 21
  - **Action**: `uv add --dev locust>=2.20`

- [ ] 7.2.2 Implement load tests
  - **File**: `benchmarks/load_test.py`
  - **Scenario**: 1000 req/sec sustained
  - **Metrics**: Latency, throughput, error rate

- [ ] 7.2.3 Implement stress tests
  - **File**: `benchmarks/stress_test.py`
  - **Goal**: Find breaking point
  - **Action**: Gradually increase load until failure

- [ ] 7.2.4 Document latency percentiles
  - **Metrics**: p50, p95, p99, p99.9
  - **Target**: <5ms p95 latency for localhost

- [ ] 7.2.5 Add memory leak detection
  - **Tool**: memory_profiler
  - **Test**: Run long-duration test, monitor memory

### 7.3 Edge Case Coverage

- [ ] 7.3.1 Address Issue #11
  - **Issue**: [#11](https://github.com/adriannoes/asap-protocol/issues/11)
  - **Action**: Identify and test missing edge cases
  - **Examples**:
    - Empty payloads
    - Maximum size payloads
    - Invalid UTF-8 in strings
    - Clock skew scenarios

### 7.4 PRD Review Checkpoint

- [ ] 7.4.1 Review performance open questions
  - **PRD Reference**: [Section 11, Q2](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Question to Answer**:
    - Q2: Adaptive rate limiting based on load?
    - Assess based on load testing experience
  - **Deliverable**: Decide for v1.0.0 or defer to v1.1.0

**Definition of Done**:
- [ ] 100+ property-based tests passing
- [ ] Load tests show <5ms p95 latency
- [ ] Stress tests identify breaking point
- [ ] No memory leaks detected
- [ ] Issue #11 resolved
- [ ] PRD updated with adaptive rate limiting decision

---

## Sprint P8: Testing Enhancements - Chaos & Contract

**Duration**: Flexible (estimated 4-5 days)
**Goal**: Chaos engineering and contract testing

### 8.1 Chaos Engineering

- [ ] 8.1.1 Implement network partition simulation
  - **PRD Reference**: Req 22
  - **File**: `tests/chaos/test_network_partition.py`
  - **Tool**: toxiproxy or custom middleware

- [ ] 8.1.2 Implement random server crashes
  - **File**: `tests/chaos/test_crashes.py`
  - **Logic**: Randomly kill server during test

- [ ] 8.1.3 Implement message loss/duplication
  - **File**: `tests/chaos/test_message_reliability.py`
  - **Logic**: Drop or duplicate random messages

- [ ] 8.1.4 Implement clock skew testing
  - **File**: `tests/chaos/test_clock_skew.py`
  - **Logic**: Simulate servers with different clocks

- [ ] 8.1.5 Document resilience patterns
  - **File**: `docs/testing.md`
  - **Content**: How to run chaos tests

### 8.2 Contract Testing

- [ ] 8.2.1 Implement v0.1.0 → v1.0.0 compatibility
  - **PRD Reference**: Req 23
  - **File**: `tests/contract/test_v0_1_to_v1_0.py`
  - **Test**: v0.1.0 client can talk to v1.0.0 server

- [ ] 8.2.2 Implement v1.0.0 → v0.1.0 compatibility
  - **File**: `tests/contract/test_v1_0_to_v0_1.py`
  - **Test**: v1.0.0 client can talk to v0.1.0 server

- [ ] 8.2.3 Implement schema evolution validation
  - **File**: `tests/contract/test_schema_evolution.py`
  - **Test**: Old schemas validate against new code

**Definition of Done**:
- [ ] Chaos tests verify graceful degradation
- [ ] Contract tests guarantee backward compatibility
- [ ] Test suite >800 tests total
- [ ] Documentation covers resilience

---

## Sprint P9: Documentation - Tutorials & ADRs

**Duration**: Flexible (estimated 5-6 days)
**Goal**: Create comprehensive tutorials and ADRs

### 9.1 Step-by-Step Tutorials

- [ ] 9.1.1 "Building Your First Agent" tutorial
  - **PRD Reference**: Req 24
  - **File**: `docs/tutorials/first-agent.md`
  - **Duration**: 15-minute quickstart
  - **Content**: Echo agent from scratch

- [ ] 9.1.2 "Stateful Workflows with Snapshots" tutorial
  - **File**: `docs/tutorials/stateful-workflows.md`
  - **Level**: Intermediate
  - **Content**: Long-running task with checkpoints

- [ ] 9.1.3 "Multi-Agent Orchestration" tutorial
  - **File**: `docs/tutorials/multi-agent.md`
  - **Level**: Advanced
  - **Content**: 3+ agents collaborating

- [ ] 9.1.4 "Production Deployment Checklist" guide
  - **File**: `docs/tutorials/production-checklist.md`
  - **Audience**: DevOps engineers
  - **Content**: Security, monitoring, scaling

### 9.2 Architecture Decision Records

- [ ] 9.2.1 Write ADRs for key decisions
  - **PRD Reference**: Req 25
  - **Location**: `docs/adr/`
  - **Format**: [MADR](https://adr.github.io/madr/)

- [ ] 9.2.2 ADR topics (15+ total):
  - [ ] ADR-001: ULID for ID generation
  - [ ] ADR-002: Async-first API design
  - [ ] ADR-003: JSON-RPC 2.0 binding
  - [ ] ADR-004: Pydantic for models
  - [ ] ADR-005: State machine design
  - [ ] ADR-006: Security defaults (HTTPS, auth)
  - [ ] ADR-007: FastAPI for server
  - [ ] ADR-008: httpx for client
  - [ ] ADR-009: Snapshot vs event-sourced persistence
  - [ ] ADR-010: Python 3.13+ requirement
  - [ ] ADR-011: Rate limiting strategy
  - [ ] ADR-012: Error taxonomy
  - [ ] ADR-013: MCP integration approach
  - [ ] ADR-014: Testing strategy
  - [ ] ADR-015: Observability design

- [ ] 9.2.3 Update docs navigation
  - **File**: `mkdocs.yml`
  - **Action**: Add tutorials and ADRs to nav

### 9.3 PRD Review Checkpoint

- [ ] 9.3.1 Review documentation open questions
  - **PRD Reference**: [Section 11, Q7, Q8](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Questions to Answer**:
    - Q8: i18n documentation languages (check PyPI stats)
    - Assess download geography since v0.5.0
  - **Deliverable**: Decide i18n scope (English-only, +PT-BR, or more)

**Definition of Done**:
- [ ] 4+ tutorials covering beginner→advanced
- [ ] 15+ ADRs documenting key decisions
- [ ] Docs site well-organized
- [ ] All content reviewed for accuracy
- [ ] PRD updated with i18n decision (DD-010)

---

## Sprint P10: Documentation - Deployment & Troubleshooting

**Duration**: Flexible (estimated 4-5 days)
**Goal**: Deployment guides and troubleshooting

### 10.1 Cloud-Native Deployment

- [ ] 10.1.1 Create Docker images
  - **PRD Reference**: Req 26
  - **File**: `Dockerfile`
  - **Base**: `python:3.13-slim`
  - **Best Practices**: Multi-stage build, non-root user

- [ ] 10.1.2 Write Kubernetes manifests
  - **Files**:
    - `k8s/deployment.yaml`
    - `k8s/service.yaml`
    - `k8s/ingress.yaml`
  - **Features**: Readiness/liveness probes, resource limits

- [ ] 10.1.3 Create Helm chart
  - **Directory**: `helm/asap-agent/`
  - **Files**: `Chart.yaml`, `values.yaml`, `templates/`
  - **Features**: Configurable via values

- [ ] 10.1.4 Add health check endpoints
  - **File**: `src/asap/transport/server.py`
  - **Endpoints**:
    - `/health` - Always returns 200 OK
    - `/ready` - Returns 200 when ready to serve

- [ ] 10.1.5 Test K8s deployment
  - **Target**: Deploy to K8s in <10 minutes
  - **Action**: Test with minikube or kind

- [ ] 10.1.6 Publish Docker images
  - **Registry**: GitHub Container Registry (ghcr.io)
  - **Tags**: `latest`, `v1.0.0`, `v1.0`

### 10.2 Troubleshooting Guide

- [ ] 10.2.1 Write troubleshooting guide
  - **PRD Reference**: Req 27
  - **File**: `docs/troubleshooting.md`
  - **Sections**:
    - Common errors
    - Debugging checklist
    - Performance tuning
    - FAQ

- [ ] 10.2.2 Common errors section
  - **Content**: Top 20 errors with solutions
  - **Format**: Error message → Cause → Solution

- [ ] 10.2.3 Debugging checklist
  - **Content**: Step-by-step debugging workflow
  - **Tools**: Logs, traces, metrics

- [ ] 10.2.4 Performance tuning tips
  - **Content**: Connection pools, caching, compression
  - **Benchmarks**: Before/after measurements

- [ ] 10.2.5 FAQ section
  - **Content**: 30+ frequently asked questions
  - **Topics**: Setup, configuration, errors, best practices

**Definition of Done**:
- [ ] Docker images published to registry
- [ ] K8s deployment works in <10 minutes
- [ ] Troubleshooting guide covers 80% of issues
- [ ] Health checks working

---

## Sprint P11: Observability - OpenTelemetry Integration

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Distributed tracing and metrics

### 11.1 OpenTelemetry Tracing

- [ ] 11.1.1 Add OpenTelemetry dependencies
  - **PRD Reference**: Req 28
  - **Packages**:
    - `opentelemetry-api>=1.20`
    - `opentelemetry-sdk>=1.20`
    - `opentelemetry-instrumentation-fastapi>=0.41`
    - `opentelemetry-instrumentation-httpx>=0.41`

- [ ] 11.1.2 Implement tracing integration
  - **File**: `src/asap/observability/tracing.py`
  - **Features**:
    - Auto-instrument FastAPI and httpx
    - Custom spans for handler execution
    - Span attributes (agent URN, payload type)

- [ ] 11.1.3 Add context propagation
  - **Action**: Inject trace_id/span_id into envelope extensions
  - **Standard**: W3C Trace Context

- [ ] 11.1.4 Test with Jaeger/Zipkin
  - **Action**: Run local Jaeger, verify traces appear
  - **Command**: `docker run -p 16686:16686 jaegertracing/all-in-one`

### 11.2 Structured Metrics

- [ ] 11.2.1 Implement OpenTelemetry metrics
  - **PRD Reference**: Req 29
  - **File**: `src/asap/observability/metrics.py`
  - **Metrics** (20+ total):
    - `asap.requests.total` (counter)
    - `asap.requests.duration` (histogram)
    - `asap.requests.active` (gauge)
    - `asap.errors.total` (counter)
    - `asap.state_transitions.total` (counter)
    - (others as needed)

- [ ] 11.2.2 Enhance Prometheus export
  - **Action**: Update existing `/asap/metrics` endpoint
  - **Format**: Prometheus + OpenMetrics

- [ ] 11.2.3 Document zero-config setup
  - **File**: `docs/observability.md`
  - **Content**: Environment variables for auto-config

**Definition of Done**:
- [ ] OpenTelemetry tracing working
- [ ] 20+ metrics instrumented
- [ ] Zero-config for development
- [ ] Production export tested
- [ ] Documentation complete

---

## Sprint P12: Observability - Dashboards & MCP

**Duration**: Flexible (estimated 4-5 days)
**Goal**: Grafana dashboards and MCP feature parity

### 12.1 Grafana Dashboards

- [ ] 12.1.1 Create RED metrics dashboard
  - **PRD Reference**: Req 30
  - **File**: `src/asap/observability/dashboards/asap-red.json`
  - **Metrics**: Rate, Errors, Duration

- [ ] 12.1.2 Create topology dashboard
  - **File**: `src/asap/observability/dashboards/asap-topology.json`
  - **Visualization**: Agent graph with request flow

- [ ] 12.1.3 Create state machine dashboard
  - **File**: `src/asap/observability/dashboards/asap-state-machine.json`
  - **Visualization**: Heatmap of state transitions

- [ ] 12.1.4 Test dashboards
  - **Action**: Import to Grafana, verify visualizations
  - **Data Source**: Prometheus

### 12.2 MCP Feature Parity

- [ ] 12.2.1 Implement complete MCP server
  - **PRD Reference**: Req 31
  - **File**: `src/asap/mcp/server.py`
  - **Features**:
    - Tool execution protocol
    - Resource fetching with streaming
    - Prompt templates

- [ ] 12.2.2 Enhance MCP client
  - **PRD Reference**: Req 32
  - **File**: `src/asap/mcp/client.py`
  - **Features**:
    - Discover MCP tools
    - Schema validation for inputs
    - Result streaming

- [ ] 12.2.3 Test MCP interoperability
  - **Action**: Test with real MCP servers
  - **Target**: 100% spec compliance

- [ ] 12.2.4 Document MCP integration
  - **File**: `docs/mcp-integration.md`
  - **Content**: Usage examples, API reference

**Definition of Done**:
- [ ] Grafana dashboards working
- [ ] MCP server 100% spec compliant
- [ ] MCP client supports all features
- [ ] Documentation complete

---

## Sprint P13: v1.0.0 Release Preparation

**Duration**: Flexible (estimated 5-7 days)
**Goal**: Final testing, polish, and release

### 13.1 Comprehensive Testing

- [ ] 13.1.1 Run full test suite
  - **Command**: `uv run pytest`
  - **Target**: 800+ tests passing
  - **Coverage**: ≥95%

- [ ] 13.1.2 Run full benchmark suite
  - **Commands**:
    - `uv run pytest benchmarks/`
    - `uv run locust -f benchmarks/load_test.py`
  - **Target**: All performance targets met

- [ ] 13.1.3 Run full security audit
  - **Commands**:
    - `uv run pip-audit`
    - `uv run bandit -r src/`
  - **Target**: Zero critical vulnerabilities

### 13.2 Documentation Review

- [ ] 13.2.1 Review all documentation
  - **Files**: README, docs/, CHANGELOG, CONTRIBUTING
  - **Action**: Verify accuracy, fix broken links

- [ ] 13.2.2 Test all examples
  - **Files**: `src/asap/examples/*.py`
  - **Action**: Run each example, verify they work

- [ ] 13.2.3 Test upgrade paths
  - **Paths**:
    - v0.1.0 → v1.0.0
    - v0.5.0 → v1.0.0
  - **Action**: Verify smooth upgrades

### 13.3 Release Preparation

- [ ] 13.3.1 Update CHANGELOG.md
  - **Section**: `## [1.0.0] - YYYY-MM-DD`
  - **Content**: All changes since v0.5.0
  - **Format**: Follow Keep a Changelog

- [ ] 13.3.2 Create comprehensive release notes
  - **File**: `.github/release-notes-v1.0.0.md`
  - **Sections**:
    - Major features
    - Performance improvements
    - Breaking changes
    - Migration guide
    - Contributors

- [ ] 13.3.3 Review and merge open PRs
  - **Action**: Merge ready PRs or defer to v1.1.0

### 13.4 Release

- [ ] 13.4.1 Tag and publish
  - **Tag**: `git tag v1.0.0 && git push origin v1.0.0`
  - **Build**: `uv build`
  - **Publish**: `uv publish`
  - **Verify**: Check PyPI package page

- [ ] 13.4.2 Create GitHub release
  - **Action**: Use release notes from 13.3.2
  - **Assets**: Attach wheel and sdist
  - **Label**: Mark as "Release" (remove pre-release)

- [ ] 13.4.3 Publish Docker images
  - **Tags**: `latest`, `v1.0.0`, `v1.0`, `v1`
  - **Registry**: ghcr.io

### 13.5 Communication

- [ ] 13.5.1 Announce release
  - **Channels**:
    - GitHub Discussions
    - README update
    - Social media
    - Blog post (optional)

- [ ] 13.5.2 Notify community
  - **Action**: Comment on resolved issues
  - **Action**: Thank contributors

- [ ] 13.5.3 Update project status
  - **README**: Change "Alpha" → "Stable"
  - **Classifiers**: Update to `Development Status :: 5 - Production/Stable`

### 13.6 Final PRD Review & Retrospective

- [ ] 13.6.1 Complete PRD review before release
  - **PRD Reference**: [Section 11](../prd/prd-v1-roadmap.md#11-open-questions)
  - **Action**: Review all remaining open questions
  - **Questions to Address**:
    - Any unanswered questions from Q1-Q12
    - Document decisions or defer to v1.1.0
  - **Deliverable**: Updated PRD with all decisions documented

- [ ] 13.6.2 Create v1.0.0 retrospective document
  - **File**: `.cursor/dev-planning/retrospectives/v1.0.0-retro.md`
  - **Content**:
    - What went well
    - What could be improved
    - Lessons learned
    - Metrics achieved vs targets
    - Recommendations for v1.1.0 planning

- [ ] 13.6.3 Schedule post-release PRD review
  - **Timeline**: 2 weeks after v1.0.0 release
  - **Action**: Create calendar reminder
  - **Focus**: Community feedback on remaining open questions (Q7, Q9, Q10)

**Definition of Done**:
- [ ] All success metrics met (PRD Section 8)
- [ ] Zero critical bugs
- [ ] Documentation 100% complete
- [ ] v1.0.0 published to PyPI
- [ ] Release announcement live
- [ ] Community notified
- [ ] PRD fully reviewed and updated
- [ ] Retrospective document created
- [ ] Post-release review scheduled

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| P1 | 10 | Security (MED) + **PRD Review** | 5-7 |
| P2 | 4 | Code quality (LOW) | 3-4 |
| P3 | 8 | Performance (connection & cache) + **PRD Review** | 5-7 |
| P4 | 6 | Performance (batch & compression) | 4-6 |
| P5 | 16 | DX (examples & testing) + **PRD Review** | 6-8 |
| P6 | 9 | DX (debugging) + **PRD Review** | 4-5 |
| P7 | 9 | Testing (property & load) + **PRD Review** | 5-7 |
| P8 | 8 | Testing (chaos & contract) | 4-5 |
| P9 | 21 | Docs (tutorials & ADRs) + **PRD Review** | 5-6 |
| P10 | 11 | Docs (deployment & troubleshooting) | 4-5 |
| P11 | 8 | Observability (tracing & metrics) | 5-7 |
| P12 | 8 | Observability (dashboards & MCP) | 4-5 |
| P13 | 17 | Release prep + **Final PRD Review** | 5-7 |

**Total**: 135 tasks across 13 sprints (60-80 days)

**PRD Review Checkpoints**: 7 (P1, P3, P5, P6, P7, P9, P13)

---

## Progress Tracking

**Overall Progress**: 0/135 tasks completed (0%)

**Sprint Status**:
- ⏳ P1: 0/10 tasks (0%) - **Includes PRD review**
- ⏳ P2: 0/4 tasks (0%)
- ⏳ P3: 0/8 tasks (0%) - **Includes PRD review**
- ⏳ P4: 0/6 tasks (0%)
- ⏳ P5: 0/16 tasks (0%) - **Includes PRD review**
- ⏳ P6: 0/9 tasks (0%) - **Includes PRD review**
- ⏳ P7: 0/9 tasks (0%) - **Includes PRD review**
- ⏳ P8: 0/8 tasks (0%)
- ⏳ P9: 0/21 tasks (0%) - **Includes PRD review**
- ⏳ P10: 0/11 tasks (0%)
- ⏳ P11: 0/8 tasks (0%)
- ⏳ P12: 0/8 tasks (0%)
- ⏳ P13: 0/17 tasks (0%) - **Includes final PRD review**

**PRD Maintenance Schedule**:
- P1: Review security decisions (HMAC signing)
- P3: Document connection pool size (DD-008)
- P5: Decide auth scheme for examples (DD-009)
- P6: Decide trace JSON export
- P7: Decide adaptive rate limiting
- P9: Decide i18n scope (DD-010)
- P13: Final review + retrospective + post-release planning

**Last Updated**: 2026-01-24

---

**Prerequisites**: v0.5.0 must be released before starting Sprint P1
