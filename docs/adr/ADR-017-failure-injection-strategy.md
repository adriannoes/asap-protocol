# ADR-017: Failure Injection Strategy (Chaos Testing)

## Context and Problem Statement

ASAP agents must handle failures gracefully (server crashes, message loss, network partition). We need a strategy to validate resilience through controlled failure injection.

## Decision Drivers

* Validate retry, circuit breaker, timeout behavior
* Simulate real-world failures (crashes, drops, partitions)
* Reproducible tests in CI
* Document expected behavior under failure

## Considered Options

* No chaos testing
* Manual chaos (external tools)
* In-process chaos (mocked transport, controlled failures)
* Dedicated chaos test suite with simulated failures

## Decision Outcome

Chosen option: "In-process chaos tests with mocked transport", because tests in tests/chaos/ use httpx.MockTransport to simulate server crash, message loss, 503, network partition, clock skew. Validates ASAPClient retry, circuit breaker, timeout. No external chaos tools required for CI.

### Consequences

* Good, because reproducible; runs in CI
* Good, because covers message loss, crashes, circuit open
* Good, because documents expected client behavior
* Bad, because mocked; may miss real network behavior

### Confirmation

tests/chaos/: test_crashes.py, test_message_reliability.py, test_network_partition.py, test_clock_skew.py. See [Building Resilient Agents](../tutorials/resilience.md).

## Pros and Cons of the Options

### No chaos testing

* Good, because no extra tests
* Bad, because no resilience validation

### In-process chaos with mocks

* Good, because CI-friendly; deterministic
* Good, because covers key scenarios
* Bad, because mocks may not reflect real failures

### External chaos (Chaos Monkey, etc.)

* Good, because real failures
* Bad, because complex; not suitable for unit CI

## More Information

* tests/chaos/
* [Building Resilient Agents](../tutorials/resilience.md)
* ASAPClient retry, circuit breaker, timeout behavior
