# Tasks: ASAP v1.0.0 Developer Experience (P5-P6) - Detailed

> **Sprints**: P5-P6 - Improve developer experience
> **Duration**: Flexible (10-13 days)
> **Goal**: Real-world examples, testing utilities, debugging tools

---

## Relevant Files

### Sprint P5: Examples & Testing Utilities
- `src/asap/examples/orchestration.py` - NEW: Multi-agent example
- `src/asap/examples/long_running.py` - NEW: Checkpoints example
- `src/asap/examples/error_recovery.py` - NEW: Retry patterns
- `src/asap/examples/mcp_integration.py` - NEW: MCP tools
- `src/asap/examples/auth_patterns.py` - NEW: Auth examples
- (5+ more examples)
- `src/asap/testing/__init__.py` - NEW: Testing utilities
- `src/asap/testing/fixtures.py` - NEW: Pytest fixtures
- `src/asap/testing/mocks.py` - NEW: Mock agents
- `tests/examples/` - Example tests

### Sprint P6: Debugging Tools
- `src/asap/cli.py` - Trace command (extend)
- `src/asap/observability/trace_ui.py` - NEW: Optional web UI
- `src/asap/transport/server.py` - Hot reload, debug mode (extend)

---

## Sprint P5: Examples & Testing Utilities

### Task 5.1: Create Real-World Examples

- [ ] 5.1.1 Multi-agent orchestration (3+ agents)
  - File: `src/asap/examples/orchestration.py`
  - Scenario: Main agent delegates to 2 sub-agents
  - Show: Task coordination, state tracking

- [ ] 5.1.2 Long-running task with checkpoints
  - File: `src/asap/examples/long_running.py`
  - Scenario: Task saves snapshots, resumes after crash
  - Show: StateSnapshot usage

- [ ] 5.1.3 Error recovery patterns
  - File: `src/asap/examples/error_recovery.py`
  - Show: Retry with backoff, circuit breaker, fallback

- [ ] 5.1.4 MCP tool integration
  - File: `src/asap/examples/mcp_integration.py`
  - Show: Calling MCP tools via ASAP envelopes

- [ ] 5.1.5 State migration
  - File: `src/asap/examples/state_migration.py`
  - Show: Moving task state between agents

- [ ] 5.1.6 Authentication patterns
  - File: `src/asap/examples/auth_patterns.py`
  - Show: Bearer, custom validators, OAuth2 concept

- [ ] 5.1.7 Rate limiting strategies
  - File: `src/asap/examples/rate_limiting.py`
  - Show: Per-sender, per-endpoint patterns

- [ ] 5.1.8 WebSocket concept (not implemented)
  - File: `src/asap/examples/websocket_concept.py`
  - Show: How WebSocket would work (comments/pseudocode)

- [ ] 5.1.9 Add 2+ more creative examples
  - Ideas: Streaming responses, multi-step workflows, etc.

- [ ] 5.1.10 Add README for examples
  - File: Update `src/asap/examples/README.md`
  - List all examples with descriptions
  - Usage instructions for each

- [ ] 5.1.11 Add tests for examples
  - Directory: `tests/examples/`
  - Test each example runs successfully
  - Verify output correctness

- [ ] 5.1.12 Update main README
  - Section: Expand "Advanced Examples"
  - Link to all 10+ examples

- [ ] 5.1.13 Commit
  - Command: `git commit -m "docs(examples): add 10+ real-world usage examples"`

**Acceptance**: 10+ examples, all tested, README updated

---

### Task 5.2: Create Testing Utilities

- [ ] 5.2.1 Create asap.testing module
  - Directory: `src/asap/testing/`
  - Files: __init__.py, fixtures.py, mocks.py, assertions.py

- [ ] 5.2.2 Implement MockAgent
  - File: `src/asap/testing/mocks.py`
  - Class: Configurable mock agent
  - Features: Pre-set responses, request recording

- [ ] 5.2.3 Implement pytest fixtures
  - File: `src/asap/testing/fixtures.py`
  - Fixtures: mock_agent, mock_client, mock_snapshot_store
  - Context managers: test_agent(), test_client()

- [ ] 5.2.4 Implement custom assertions
  - File: `src/asap/testing/assertions.py`
  - Functions: assert_envelope_valid(), assert_task_completed()

- [ ] 5.2.5 Document testing utilities
  - File: Update `docs/testing.md`
  - Show: How to use each utility
  - Examples: Reducing test boilerplate

- [ ] 5.2.6 Refactor existing tests to use utilities
  - Pick: 5-10 tests to refactor as examples
  - Measure: Boilerplate reduction
  - Target: 50% less code

- [ ] 5.2.7 Commit
  - Command: `git commit -m "feat(testing): add testing utilities for easier test authoring"`

**Acceptance**: Testing module created, 50% boilerplate reduction

---

### Task 5.3: PRD Review Checkpoint

- [ ] 5.3.1 Review Q4 (auth scheme for examples)
  - Options: Bearer (simple), OAuth2 (realistic), both
  - Decide based on example complexity
  - Document as DD-009

- [ ] 5.3.2 Review Q6 (pytest-asap plugin)
  - Assess testing utilities usage
  - Decide: Create plugin now or defer to v1.1.0

- [ ] 5.3.3 Update PRD
  - Add DD-009 for auth scheme decision
  - Update Q6 status

**Acceptance**: Q4 answered (DD-009), Q6 decided

---

## Sprint P6: Debugging Tools

### Task 6.1: Implement Trace Visualization

- [ ] 6.1.1 Add trace command to cli.py
  - Command: `asap trace [trace-id]`
  - Logic: Search logs for trace_id
  - Output: ASCII diagram of request flow

- [ ] 6.1.2 Add timing information
  - Show: Latency for each hop
  - Format: Agent A -> Agent B (15ms) -> Agent C (23ms)

- [ ] 6.1.3 Optional: Web UI for traces
  - File: `src/asap/observability/trace_ui.py`
  - Framework: FastAPI + simple HTML
  - Features: Browse traces, search, visualize

- [ ] 6.1.4 Commit
  - Command: `git commit -m "feat(cli): add trace visualization command"`

**Acceptance**: Trace command works, shows flow and timing

---

### Task 6.2: Development Server Improvements

- [ ] 6.2.1 Add hot reload for handlers
  - Use: watchfiles library
  - Monitor: src/asap/transport/handlers.py changes
  - Reload: Handler registry on file change

- [ ] 6.2.2 Add debug logging mode
  - Environment: ASAP_DEBUG_LOG=true
  - Behavior: Log all requests/responses
  - Format: Structured JSON logs

- [ ] 6.2.3 Add built-in REPL
  - Command: `asap repl`
  - Features: Test payloads interactively
  - Use: Python's code module

- [ ] 6.2.4 Enable Swagger UI in debug mode
  - FastAPI: Enable /docs endpoint
  - Condition: Only if ASAP_DEBUG=true

- [ ] 6.2.5 Commit
  - Command: `git commit -m "feat(dev): add hot reload, debug logging, and REPL"`

**Acceptance**: Hot reload works, debug mode detailed, REPL functional

---

### Task 6.3: PRD Review Checkpoint

- [ ] 6.3.1 Review Q5 (trace JSON export)
  - Assess trace command usage from implementation
  - Decide: Add JSON export or defer
  - If valuable: Implement quickly
  - If not: Defer to v1.1.0

- [ ] 6.3.2 Update PRD
  - Document decision
  - Update Q5 status

**Acceptance**: Q5 answered, decision documented

---

## Task 6.4: Mark Sprints P5-P6 Complete

- [ ] 6.4.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P5 tasks (5.1-5.3) as complete `[x]`
  - Mark: P6 tasks (6.1-6.3) as complete `[x]`
  - Update: P5 and P6 progress to 100%

- [ ] 6.4.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion dates

- [ ] 6.4.3 Verify DX improvements
  - Confirm: 10+ examples working
  - Confirm: Testing utilities reduce boilerplate
  - Confirm: PRD Q4, Q5, Q6 answered

**Acceptance**: Both files complete, DX goals met

---

**P5-P6 Definition of Done**:
- [ ] All tasks 5.1-6.4 completed
- [ ] 10+ production examples
- [ ] Testing utilities created
- [ ] 50% boilerplate reduction
- [ ] Trace command working
- [ ] Hot reload functional
- [ ] Debug mode comprehensive
- [ ] PRD Q4, Q5, Q6 answered (DD-009)
- [ ] Progress tracked in both files

**Total Sub-tasks**: ~80
