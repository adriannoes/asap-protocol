# Tasks: ASAP v1.0.0 Developer Experience (P5-P6) - Detailed

> **Sprints**: P5-P6 - Improve developer experience
> **Goal**: Real-world examples, testing utilities, debugging tools

---

## Relevant Files

### Sprint P5: Examples & Testing Utilities
- `src/asap/examples/orchestration.py` - Multi-agent example (Task 5.1.1)
- `src/asap/examples/long_running.py` - NEW: Checkpoints example
- `src/asap/examples/error_recovery.py` - NEW: Retry patterns
- `src/asap/examples/mcp_integration.py` - NEW: MCP tools
- `src/asap/examples/auth_patterns.py` - NEW: Auth examples
- (5+ more examples)
- `src/asap/testing/__init__.py` - Testing utilities package (Task 5.2.1)
- `src/asap/testing/mocks.py` - MockAgent: pre-set/default responses, request recording, delay, failure (Task 5.2.2)
- `tests/testing/__init__.py` - Tests for asap.testing
- `tests/testing/test_mocks.py` - Unit tests for MockAgent
- `src/asap/testing/assertions.py` - assert_envelope_valid, assert_task_completed, assert_response_correlates (Task 5.2.4)
- `tests/testing/test_assertions.py` - Unit tests for assertions
- `docs/testing.md` - Section "ASAP Testing Utilities" (Task 5.2.5)
- Refactored: tests/examples/test_echo_agent.py, test_coordinator.py, test_examples_dx.py; tests/transport/test_handlers.py, test_client.py; tests/e2e/test_two_agents.py; tests/transport/e2e/test_full_agent_flow.py (Task 5.2.6)
- `src/asap/testing/fixtures.py` - mock_agent, mock_client, mock_snapshot_store, test_agent(), test_client() (Task 5.2.3)
- `tests/conftest.py` - pytest_plugins for asap.testing.fixtures
- `tests/testing/test_fixtures.py` - Tests for fixtures and context managers
- `tests/examples/` - Example tests

### Sprint P6: Debugging Tools
- `src/asap/cli.py` - Trace command, repl command (extend)
- `src/asap/observability/trace_ui.py` - NEW: Optional web UI
- `src/asap/observability/logging.py` - ASAP_DEBUG_LOG, is_debug_log_mode() (Task 6.2.2)
- `src/asap/transport/server.py` - Hot reload, debug logging mode (extend)

### Task 5.3: PRD Review Checkpoint
- `.cursor/dev-planning/prd/prd-v1-roadmap.md` - DD-010 (auth scheme), Q4 resolved, Q6 resolved (defer plugin)
- `.cursor/dev-planning/prd/prd-review-schedule.md` - Q4/Q6 status updated

### Task 6.1: Trace Visualization
- `src/asap/observability/trace_parser.py` - Parse JSON logs, filter by trace_id, extract_trace_ids, build hops, format ASCII, trace_to_json_export
- `src/asap/observability/trace_ui.py` - FastAPI Web UI: browse traces, list IDs, visualize (GET /, POST /api/traces/list, /api/traces/visualize)
- `src/asap/cli.py` - `asap trace <trace-id> [--log-file PATH] [--format ascii|json]` command
- `tests/observability/test_trace_parser.py` - Unit tests for trace parser (incl. extract_trace_ids)
- `tests/observability/test_trace_ui.py` - Tests for trace UI endpoints
- `tests/test_cli.py` - TestCliTrace tests for trace command (incl. --format json)

### Task 6.3: PRD Review Checkpoint
- `.cursor/dev-planning/prd/prd-v1-roadmap.md` - DD-011 (trace JSON export), Q5 resolved
- `.cursor/dev-planning/prd/prd-review-schedule.md` - Q5 status updated

### Task 6.4: Mark Sprints P5-P6 Complete
- `.cursor/dev-planning/tasks/v1.0.0/tasks-v1.0.0-roadmap.md` - P5/P6 tasks and DoD marked complete, progress 100%
- `.cursor/dev-planning/tasks/v1.0.0/tasks-v1.0.0-dx-detailed.md` - 6.4.1-6.4.3 and P5-P6 Definition of Done marked complete

### Task 6.2.1: Hot Reload
- `pyproject.toml` - Added watchfiles>=0.21.0
- `src/asap/transport/server.py` - RegistryHolder, _run_handler_watcher, create_app(hot_reload), ASAPRequestHandler(registry_holder)
- `tests/transport/test_server.py` - RegistryHolder in handler fixture, test_create_app_with_hot_reload_returns_app

### Task 6.2.2: Debug Logging Mode
- `src/asap/observability/logging.py` - ENV_DEBUG_LOG, is_debug_log_mode()
- `src/asap/observability/__init__.py` - Export is_debug_log_mode
- `src/asap/transport/server.py` - _log_request_debug, _log_response_debug; log full request/response when ASAP_DEBUG_LOG=true (structured JSON)
- `tests/observability/test_logging.py` - TestIsDebugLogMode (is_debug_log_mode true/false)
- `tests/transport/test_server.py` - TestDebugLogMode (debug_request and debug_response logged when ASAP_DEBUG_LOG=true)

### Task 6.2.3: Built-in REPL
- `src/asap/cli.py` - repl command, _repl_namespace(), REPL_BANNER; code.interact with Envelope, TaskRequest, Manifest, generate_id, sample_envelope()
- `tests/test_cli.py` - TestCliRepl (help shows repl, repl --help, repl starts and exits with exit())

### Task 6.2.4: Swagger UI in debug mode
- `src/asap/transport/server.py` - docs_url, redoc_url, openapi_url set from is_debug_mode(); /docs and /openapi.json only when ASAP_DEBUG=true
- `tests/transport/test_server.py` - TestSwaggerUiDebugMode (docs disabled when not debug, enabled when ASAP_DEBUG=true)

---

## Sprint P5: Examples & Testing Utilities

### Task 5.1: Create Real-World Examples

- [x] 5.1.1 Multi-agent orchestration (3+ agents)
  - File: `src/asap/examples/orchestration.py`
  - Scenario: Main agent delegates to 2 sub-agents
  - Show: Task coordination, state tracking

- [x] 5.1.2 Long-running task with checkpoints
  - File: `src/asap/examples/long_running.py`
  - Scenario: Task saves snapshots, resumes after crash
  - Show: StateSnapshot usage

- [x] 5.1.3 Error recovery patterns
  - File: `src/asap/examples/error_recovery.py`
  - Show: Retry with backoff, circuit breaker, fallback

- [x] 5.1.4 MCP tool integration
  - File: `src/asap/examples/mcp_integration.py`
  - Show: Calling MCP tools via ASAP envelopes

- [x] 5.1.5 State migration
  - File: `src/asap/examples/state_migration.py`
  - Show: Moving task state between agents

- [x] 5.1.6 Authentication patterns
  - File: `src/asap/examples/auth_patterns.py`
  - Show: Bearer, custom validators, OAuth2 concept

- [x] 5.1.7 Rate limiting strategies
  - File: `src/asap/examples/rate_limiting.py`
  - Show: Per-sender, per-endpoint patterns

- [x] 5.1.8 WebSocket concept (not implemented)
  - File: `src/asap/examples/websocket_concept.py`
  - Show: How WebSocket would work (comments/pseudocode)

- [x] 5.1.9 Add 2+ more creative examples
  - Ideas: Streaming responses, multi-step workflows, etc.
  - Files: `streaming_response.py`, `multi_step_workflow.py`

- [x] 5.1.10 Add README for examples
  - File: Update `src/asap/examples/README.md`
  - List all examples with descriptions
  - Usage instructions for each

- [x] 5.1.11 Add tests for examples
  - Directory: `tests/examples/`
  - Test each example runs successfully
  - Verify output correctness
  - File: `tests/examples/test_examples_dx.py` (28 tests)

- [x] 5.1.12 Update main README
  - Section: Expand "Advanced Examples"
  - Link to all 10+ examples

- [x] 5.1.13 Commit
  - Command: `git commit -m "docs(examples): add 10+ real-world usage examples"`

**Acceptance**: 10+ examples, all tested, README updated

---

### Task 5.2: Create Testing Utilities

- [x] 5.2.1 Create asap.testing module
  - Directory: `src/asap/testing/`
  - Files: __init__.py, fixtures.py, mocks.py, assertions.py

- [x] 5.2.2 Implement MockAgent
  - File: `src/asap/testing/mocks.py`
  - Class: Configurable mock agent
  - Features: Pre-set responses, request recording, set_default_response, set_delay, set_failure, requests_for_skill

- [x] 5.2.3 Implement pytest fixtures
  - File: `src/asap/testing/fixtures.py`
  - Fixtures: mock_agent, mock_client, mock_snapshot_store
  - Context managers: test_agent(), test_client()

- [x] 5.2.4 Implement custom assertions
  - File: `src/asap/testing/assertions.py`
  - Functions: assert_envelope_valid(), assert_task_completed(), assert_response_correlates()

- [x] 5.2.5 Document testing utilities
  - File: Update `docs/testing.md`
  - Show: How to use each utility
  - Examples: Reducing test boilerplate

- [x] 5.2.6 Refactor existing tests to use utilities
  - Refactored 8 tests across 6 files (examples, transport, e2e)
  - Replaced ~20 manual assert lines with assert_envelope_valid, assert_task_completed, assert_response_correlates
  - Files: test_echo_agent, test_coordinator, test_examples_dx, test_handlers, test_client, test_two_agents, test_full_agent_flow

- [x] 5.2.7 Commit
  - Command: `git commit -m "feat(testing): add testing utilities for easier test authoring"`

**Acceptance**: Testing module created, 50% boilerplate reduction

---

### Task 5.3: PRD Review Checkpoint

- [x] 5.3.1 Review Q4 (auth scheme for examples)
  - Options: Bearer (simple), OAuth2 (realistic), both
  - Decide based on example complexity
  - Document as DD-010 (DD-009 already used for connection pool)

- [x] 5.3.2 Review Q6 (pytest-asap plugin)
  - Assess testing utilities usage
  - Decide: Create plugin now or defer to v1.1.0

- [x] 5.3.3 Update PRD
  - Add DD-010 for auth scheme decision
  - Update Q6 status (defer pytest-asap to v1.1.0)

**Acceptance**: Q4 answered (DD-010), Q6 decided

---

## Sprint P6: Debugging Tools

### Task 6.1: Implement Trace Visualization

- [x] 6.1.1 Add trace command to cli.py
  - Command: `asap trace <trace-id> [--log-file PATH]`
  - Logic: Search logs for trace_id (JSON lines from ASAP_LOG_FORMAT=json)
  - Output: ASCII diagram of request flow

- [x] 6.1.2 Add timing information
  - Show: Latency for each hop (from asap.request.processed duration_ms)
  - Format: Agent A -> Agent B (15ms) -> Agent C (23ms)

- [x] 6.1.3 Optional: Web UI for traces
  - File: `src/asap/observability/trace_ui.py`
  - Framework: FastAPI + simple HTML
  - Features: Browse traces (list trace IDs), search, visualize (POST /api/traces/list, /api/traces/visualize)

- [x] 6.1.4 Commit
  - Done: `git commit -m "feat(cli): add trace visualization command and optional Web UI"`

**Acceptance**: Trace command works, shows flow and timing

---

### Task 6.2: Development Server Improvements

- [x] 6.2.1 Add hot reload for handlers
  - Use: watchfiles library
  - Monitor: src/asap/transport/handlers.py changes
  - Reload: Handler registry on file change (RegistryHolder + ASAP_HOT_RELOAD env)

- [x] 6.2.2 Add debug logging mode
  - Environment: ASAP_DEBUG_LOG=true
  - Behavior: Log all requests/responses
  - Format: Structured JSON logs

- [x] 6.2.3 Add built-in REPL
  - Command: `asap repl`
  - Features: Test payloads interactively
  - Use: Python's code module

- [x] 6.2.4 Enable Swagger UI in debug mode
  - FastAPI: Enable /docs endpoint
  - Condition: Only if ASAP_DEBUG=true

- [x] 6.2.5 Commit
  - Command: `git commit -m "feat(dev): add hot reload, debug logging, and REPL"`
  - Decision on slowapi and upstream PR #246: documented in `tasks/v1.0.0/upstream-slowapi-deprecation.md`

**Acceptance**: Hot reload works, debug mode detailed, REPL functional

---

### Task 6.3: PRD Review Checkpoint

- [x] 6.3.1 Review Q5 (trace JSON export)
  - Assess trace command usage from implementation
  - Decide: Add JSON export or defer
  - If valuable: Implement quickly
  - If not: Defer to v1.1.0
  - **Decision**: Valuable — implemented `--format json` (DD-011)

- [x] 6.3.2 Update PRD
  - Document decision
  - Update Q5 status
  - DD-011 added; Q5 resolved in prd-v1-roadmap.md and prd-review-schedule.md

**Acceptance**: Q5 answered, decision documented

---

## Task 6.4: Mark Sprints P5-P6 Complete

- [x] 6.4.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P5 tasks (5.1-5.3) as complete `[x]`
  - Mark: P6 tasks (6.1-6.3) as complete `[x]`
  - Update: P5 and P6 progress to 100%
  - **Completed**: 2026-01-31

- [x] 6.4.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion dates
  - **Completed**: 2026-01-31

- [x] 6.4.3 Verify DX improvements
  - Confirm: 10+ examples working (14 examples in src/asap/examples)
  - Confirm: Testing utilities reduce boilerplate (fixtures, mocks, assertions)
  - Confirm: PRD Q4, Q5, Q6 answered (DD-010, DD-011, Q6 deferred)
  - **Completed**: 2026-01-31

**Acceptance**: Both files complete, DX goals met

---

**P5-P6 Definition of Done**:
- [x] All tasks 5.1-6.4 completed
- [x] 10+ production examples
- [x] Testing utilities created
- [x] 50% boilerplate reduction
- [x] Trace command working
- [x] Hot reload functional
- [x] Debug mode comprehensive
- [x] PRD Q4, Q5, Q6 answered (DD-010, DD-011, Q6 deferred)
- [x] Progress tracked in both files

**Total Sub-tasks**: ~80
**P5-P6 completed**: 2026-01-31
