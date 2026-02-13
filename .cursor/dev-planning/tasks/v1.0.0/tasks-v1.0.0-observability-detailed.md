# Tasks: ASAP v1.0.0 Observability (P11-P12) - Detailed

> **Sprints**: P11-P12 - OpenTelemetry integration and MCP completion
> **Goal**: Distributed tracing, metrics, dashboards, MCP feature parity

---

## Relevant Files

### Sprint P11: OpenTelemetry Integration
- `src/asap/observability/tracing.py` - OTel tracing (configure_tracing, spans, W3C propagation)
- `src/asap/observability/metrics.py` - 20+ metrics (counters, histograms), Prometheus/OpenMetrics export
- `pyproject.toml` - OTel dependencies
- `docs/observability.md` - OpenTelemetry section, env vars, Jaeger
- `src/asap/transport/server.py` - tracing + error counters
- `src/asap/transport/handlers.py` - handler spans + handler metrics
- `src/asap/transport/client.py` - transport send/error/retry metrics
- `src/asap/state/machine.py` - state transition spans + metrics

### Sprint P12: Dashboards & MCP
- `src/asap/observability/dashboards/` - Grafana dashboards (asap-red.json, asap-detailed.json, README.md)
- `src/asap/observability/dashboards/asap-red.json` - RED metrics dashboard (request rate, error rate, latency p95/p99)
- `src/asap/observability/dashboards/asap-detailed.json` - Topology, state transitions, circuit breaker panels
- `scripts/observability-stack/` - Optional docker-compose (Prometheus + Grafana) and provisioning
- `tests/observability/test_grafana_dashboards.py` - Dashboard JSON validation tests
- `docs/observability.md` - Metrics and Grafana section
- `src/asap/mcp/` - MCP 2025-11-25: protocol.py, server.py, client.py, server_runner.py
- `docs/mcp-integration.md` - MCP integration guide
- `examples/mcp_demo.py` - MCP client demo (list tools, call echo)
- `tests/mcp/` - Unit and integration tests for MCP

---

## Sprint P11: OpenTelemetry Integration

### Task 11.1: Add OpenTelemetry Dependencies

- [x] 11.1.1 Add OTel packages
  - Command: `uv add "opentelemetry-api>=1.20"`
  - Command: `uv add "opentelemetry-sdk>=1.20"`
  - Command: `uv add "opentelemetry-instrumentation-fastapi>=0.41"`
  - Command: `uv add "opentelemetry-instrumentation-httpx>=0.41"`

- [x] 11.1.2 Verify imports
  - Test: Import all OTel packages
  - Check: No conflicts with existing dependencies

**Acceptance**: OTel packages installed, imports work

---

### Task 11.2: Implement Tracing Integration

- [x] 11.2.1 Create tracing.py module
  - File: `src/asap/observability/tracing.py`
  - Function: configure_tracing() setup
  - Auto-instrument: FastAPI and httpx

- [x] 11.2.2 Add custom spans
  - Span: Handler execution
  - Span: State transitions
  - Attributes: agent URN, payload type

- [x] 11.2.3 Add context propagation
  - Inject: trace_id/span_id into envelope.extensions
  - Standard: W3C Trace Context

- [x] 11.2.4 Test with Jaeger
  - Run: Jaeger in Docker (jaegertracing/all-in-one:1.53)
  - Send: Test requests (integration test)
  - Verify: Traces appear in Jaeger API (tests/observability/test_jaeger_tracing.py)

- [x] 11.2.5 Document zero-config setup
  - File: Update `docs/observability.md`
  - Show: Environment variables for auto-config

- [x] 11.2.6 Commit
  - Command: `git commit -m "feat(observability): add OpenTelemetry tracing integration"` (at end of sprint)

**Acceptance**: Tracing works, Jaeger tested, zero-config for dev

---

### Task 11.3: Implement Structured Metrics

- [x] 11.3.1 Add OTel metrics to metrics.py
  - Metrics: 20+ counters, histograms, gauges
  - Instrument: Transport, handlers, state machine

- [x] 11.3.2 Enhance Prometheus export
  - Update: Existing /asap/metrics endpoint
  - Support: Prometheus + OpenMetrics format

- [x] 11.3.3 Test metrics
  - Send: Requests and verify metrics increment
  - Check: Prometheus scrape works

- [x] 11.3.4 Commit
  - Command: `git commit -m "feat(observability): add OpenTelemetry metrics"` (at end of sprint)

**Acceptance**: 20+ metrics, Prometheus export works

---

## Sprint P12: Dashboards & MCP

### Task 12.1: Create Grafana Dashboards

- [x] 12.1.1 Create RED metrics dashboard
  - File: `src/asap/observability/dashboards/asap-red.json`
  - Panels:
    - **Request Rate**: `sum(rate(asap_requests_total[1m])) by (payload_type)`
    - **Error Rate**: `sum(rate(asap_requests_error_total[1m])) / (sum(rate(asap_requests_total[1m])) + 1e-9)`
    - **Latency (p95)**: `histogram_quantile(0.95, sum(rate(asap_request_duration_seconds_bucket[1m])) by (le))`
    - **Latency (p99)**: `histogram_quantile(0.99, sum(rate(asap_request_duration_seconds_bucket[1m])) by (le))`

- [x] 12.1.2 Create topology and state dashboards
  - File: `src/asap/observability/dashboards/asap-detailed.json`
  - Panels:
    - **Handler executions**: `sum(rate(asap_handler_executions_total[1m])) by (payload_type)`
    - **State Transitions**: `sum(rate(asap_state_transitions_total[1m])) by (from_status, to_status)` (timeseries + table)
    - **Circuit Breaker Status**: Stat panel for `asap_circuit_breaker_open` (when metric is exposed)

- [x] 12.1.3 Test dashboards
  - Setup: `scripts/observability-stack/docker-compose.yml` (Prometheus + Grafana)
  - Configure: Grafana provisioning loads from `src/asap/observability/dashboards/`
  - Verify: `tests/observability/test_grafana_dashboards.py` validates JSON and panel structure

- [x] 12.1.4 Commit
  - Command: `git commit -m "feat(observability): add Grafana dashboards"` (at end of sprint)

**Acceptance**: 2 dashboards (RED + Detailed), working with Prometheus data

---

### Task 12.2: Complete MCP Implementation

**Spec**: Use **MCP 2025-11-25** (current). Reference: [mcp-specs.md](../../references/mcp-specs.md).

- [x] 12.2.1 Implement MCP Protocol Models
  - File: `src/asap/mcp/protocol.py`
  - Define: JSON-RPC 2.0 types (`JSONRPCRequest`, `JSONRPCResponse`, `JSONRPCError`)
  - Define: MCP 2025-11-25 types (`Tool`, `CallToolRequestParams`, `CallToolResult`, `TextContent`, `InitializeRequestParams`, `InitializeResult`; protocol version `2025-11-25`)
  - Validation: Pydantic models with extra="ignore" for forward compatibility

- [x] 12.2.2 Implement MCP Server
  - File: `src/asap/mcp/server.py`
  - Class: `MCPServer`
  - Features:
    - `register_tool(name, func, schema, description=..., title=...)`
    - `run_stdio()`: Async stdin/stdout (newline-delimited JSON)
    - `_handle_initialize()`, `_handle_tools_list()`, `_handle_tools_call()`; ping supported

- [x] 12.2.3 Implement MCP Client and Verification
  - File: `src/asap/mcp/client.py`
  - Class: `MCPClient` (stdio subprocess transport)
  - Runner: `src/asap/mcp/server_runner.py` (echo tool)
  - Verification: `examples/mcp_demo.py` and `tests/mcp/test_server_client.py`

- [x] 12.2.4 Document MCP integration
  - File: `docs/mcp-integration.md`
  - Sections: "How to Expose ASAP Agents as MCP Servers", "Connecting Claude/Gemini to ASAP", Demo, Protocol version

- [x] 12.2.5 Commit
  - Command: `git commit -m "feat(mcp): add complete MCP server and client"`

**Acceptance**: MCP 100% spec compliant, documented, verified with demo script

---

## Task 12.3: Mark Sprints P11-P12 Complete

- [x] 12.3.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P11 tasks (11.1-11.3) as complete `[x]`
  - Mark: P12 tasks (12.1-12.2) as complete `[x]`
  - Update: P11 and P12 progress to 100%

- [x] 12.3.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Completion: 2026-02-02

- [x] 12.3.3 Verify observability working
  - Tracing: Jaeger integration tested (tests/observability/test_jaeger_tracing.py)
  - Dashboards: Grafana JSON validated (tests/observability/test_grafana_dashboards.py)
  - MCP: Spec 2025-11-25 compliance tested (tests/mcp/)

**Acceptance**: Both files complete, observability production-ready

---

**P11-P12 Definition of Done**:
- [x] All tasks 11.1-12.3 completed
- [x] OpenTelemetry tracing working
- [x] 20+ metrics instrumented
- [x] Grafana dashboards (RED + Detailed)
- [x] MCP 2025-11-25 compliant
- [x] Documentation complete
- [x] Progress tracked in both files

**Total Sub-tasks**: ~65
