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
- `src/asap/observability/dashboards/` - NEW: Grafana dashboards
- `src/asap/mcp/server.py` - NEW: Complete MCP server
- `src/asap/mcp/client.py` - NEW: Enhanced MCP client
- `docs/mcp-integration.md` - NEW: MCP documentation

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

- [ ] 12.1.1 Create RED metrics dashboard
  - File: `src/asap/observability/dashboards/asap-red.json`
  - Panels: Request rate, error rate, duration

- [ ] 12.1.2 Create topology dashboard
  - File: `asap-topology.json`
  - Visualization: Agent graph

- [ ] 12.1.3 Create state machine dashboard
  - File: `asap-state-machine.json`
  - Visualization: Transition heatmap

- [ ] 12.1.4 Test dashboards
  - Import to Grafana
  - Connect to Prometheus
  - Verify visualizations work

- [ ] 12.1.5 Commit
  - Command: `git commit -m "feat(observability): add Grafana dashboards"`

**Acceptance**: 3 dashboards, tested with Grafana

---

### Task 12.2: Complete MCP Implementation

- [ ] 12.2.1 Implement MCP server
  - Directory: `src/asap/mcp/`
  - Files: server.py, client.py, protocol.py
  - Features: Tool execution, resource fetching, streaming

- [ ] 12.2.2 Enhance MCP client
  - Features: Tool discovery, schema validation
  - Support: Result streaming for large responses

- [ ] 12.2.3 Test MCP interoperability
  - Test: With real MCP servers
  - Verify: 100% spec compliance

- [ ] 12.2.4 Document MCP integration
  - File: `docs/mcp-integration.md`
  - Content: Usage, examples, API reference

- [ ] 12.2.5 Commit
  - Command: `git commit -m "feat(mcp): add complete MCP server and client"`

**Acceptance**: MCP 100% spec compliant, documented

---

## Task 12.3: Mark Sprints P11-P12 Complete

- [ ] 12.3.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P11 tasks (11.1-11.3) as complete `[x]`
  - Mark: P12 tasks (12.1-12.2) as complete `[x]`
  - Update: P11 and P12 progress to 100%

- [ ] 12.3.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion dates

- [ ] 12.3.3 Verify observability working
  - Confirm: Tracing works with Jaeger
  - Confirm: Dashboards work in Grafana
  - Confirm: MCP spec compliance tested

**Acceptance**: Both files complete, observability production-ready

---

**P11-P12 Definition of Done**:
- [ ] All tasks 11.1-12.3 completed
- [ ] OpenTelemetry tracing working
- [ ] 20+ metrics instrumented
- [ ] 3 Grafana dashboards
- [ ] MCP 100% compliant
- [ ] Documentation complete
- [ ] Progress tracked in both files

**Total Sub-tasks**: ~65
