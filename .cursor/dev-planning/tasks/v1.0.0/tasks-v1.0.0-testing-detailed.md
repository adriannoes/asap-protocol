# Tasks: ASAP v1.0.0 Testing (P7-P8) - Detailed

> **Sprints**: P7-P8 - Advanced testing techniques
> **Duration**: Flexible (9-12 days)
> **Goal**: Property-based, load, stress, chaos, and contract testing

---

## Relevant Files

### Sprint P7: Property & Load Tests
- `tests/properties/` - NEW: Property-based tests
- `benchmarks/load_test.py` - NEW: Load testing with Locust
- `benchmarks/stress_test.py` - NEW: Stress testing

### Sprint P8: Chaos & Contract Tests
- `tests/chaos/` - NEW: Chaos engineering tests
- `tests/contract/` - NEW: Cross-version compatibility

---

## Sprint P7: Property & Load Tests

### Task 7.1: Add Property-Based Testing

**Issue**: [#11](https://github.com/adriannoes/asap-protocol/issues/11) - Edge cases

- [ ] 7.1.1 Add Hypothesis dependency
  - Command: `uv add --dev "hypothesis>=6.92"`

- [ ] 7.1.2 Create property tests directory
  - Directory: `tests/properties/`
  - File: `test_model_properties.py`

- [ ] 7.1.3 Add serialization roundtrip tests
  - Strategy: Generate random valid models
  - Test: model -> JSON -> model preserves data
  - Models: All 24 Pydantic models

- [ ] 7.1.4 Add fuzz testing for envelope
  - File: `tests/fuzz/test_envelope_fuzz.py`
  - Strategy: Random invalid data
  - Test: Validation catches all malformed inputs

- [ ] 7.1.5 Add state machine property tests
  - Test: Invariants hold (terminal states never transition)
  - Test: All paths eventually reach terminal state

- [ ] 7.1.6 Run property tests
  - Command: `uv run pytest tests/properties/ -v`
  - Target: 100+ property tests

- [ ] 7.1.7 Commit
  - Command: `git commit -m "test: add property-based tests with Hypothesis"`
  - Close issue #11

**Acceptance**: 100+ property tests, issue #11 closed

---

### Task 7.2: Add Load & Stress Testing

- [ ] 7.2.1 Add Locust dependency
  - Command: `uv add --dev "locust>=2.20"`

- [ ] 7.2.2 Create load test file
  - File: `benchmarks/load_test.py`
  - Scenario: 1000 req/sec sustained for 60s
  - Measure: Latency (p50, p95, p99), errors

- [ ] 7.2.3 Create stress test file
  - File: `benchmarks/stress_test.py`
  - Scenario: Gradually increase load until failure
  - Find: Breaking point (max req/sec)

- [ ] 7.2.4 Add memory leak detection
  - Tool: memory_profiler
  - Test: Long-duration test (1 hour)
  - Monitor: Memory usage trend

- [ ] 7.2.5 Run load tests
  - Command: `uv run locust -f benchmarks/load_test.py --headless`
  - Target: <5ms p95 latency

- [ ] 7.2.6 Document results
  - File: `benchmarks/RESULTS.md`
  - Include: Latency percentiles, throughput, breaking point

- [ ] 7.2.7 Commit
  - Command: `git commit -m "test: add load and stress testing with Locust"`

**Acceptance**: <5ms p95 latency, breaking point identified, no leaks

---

### Task 7.3: PRD Review Checkpoint

- [ ] 7.3.1 Review Q2 (adaptive rate limiting)
  - Assess based on load testing experience
  - Decide: Implement in v1.0.0 or defer to v1.1.0
  - Complexity vs value tradeoff

- [ ] 7.3.2 Update PRD
  - Document decision
  - Update Q2 status

**Acceptance**: Q2 answered, PRD updated

---

## Sprint P8: Chaos & Contract Tests

### Task 8.1: Chaos Engineering

- [ ] 8.1.1 Create chaos tests directory
  - Directory: `tests/chaos/`

- [ ] 8.1.2 Implement network partition simulation
  - File: `test_network_partition.py`
  - Tool: toxiproxy or custom middleware
  - Test: Agent resilience to network issues

- [ ] 8.1.3 Implement random server crashes
  - File: `test_crashes.py`
  - Simulate: Kill server during request
  - Test: Client retry behavior

- [ ] 8.1.4 Implement message loss/duplication
  - File: `test_message_reliability.py`
  - Simulate: Drop or duplicate random messages
  - Test: Idempotency and error handling

- [ ] 8.1.5 Implement clock skew testing
  - File: `test_clock_skew.py`
  - Simulate: Servers with different clocks
  - Test: Timestamp validation edge cases

- [ ] 8.1.6 Document chaos tests
  - File: Update `docs/testing.md`
  - Section: "Chaos Engineering"
  - Instructions: How to run chaos tests

- [ ] 8.1.7 Commit
  - Command: `git commit -m "test: add chaos engineering tests for resilience"`

**Acceptance**: Chaos tests verify graceful degradation

---

### Task 8.2: Contract Testing

- [ ] 8.2.1 Test v0.1.0 client → v1.0.0 server
  - File: `tests/contract/test_v0_1_to_v1_0.py`
  - Setup: v0.1.0 client, v1.0.0 server
  - Test: Basic TaskRequest → TaskResponse flow

- [ ] 8.2.2 Test v1.0.0 client → v0.1.0 server
  - File: `tests/contract/test_v1_0_to_v0_1.py`
  - Test: New client works with old server

- [ ] 8.2.3 Test schema evolution
  - File: `tests/contract/test_schema_evolution.py`
  - Test: Old schemas validate new data
  - Test: New schemas validate old data (forward compat)

- [ ] 8.2.4 Run contract tests
  - Command: `uv run pytest tests/contract/ -v`
  - Expected: All compatibility tests pass

- [ ] 8.2.5 Commit
  - Command: `git commit -m "test: add contract tests for backward compatibility"`

**Acceptance**: Backward compatibility guaranteed

---

**P7-P8 Definition of Done**:
- [ ] 100+ property tests
- [ ] <5ms p95 latency
- [ ] Breaking point identified
- [ ] No memory leaks
- [ ] Chaos tests pass
- [ ] Contract tests guarantee compatibility
- [ ] 800+ total tests
- [ ] Issue #11 closed
- [ ] PRD Q2 answered

**Total Sub-tasks**: ~65
