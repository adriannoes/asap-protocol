# ADR-014: Testing Strategy (TDD, Property-Based)

## Context and Problem Statement

ASAP must be reliable and maintainable. We need a testing strategy that catches regressions, edge cases, and contract violations across versions.

## Decision Drivers

* High confidence in correctness
* Edge case coverage (invalid inputs, boundary conditions)
* Backward compatibility (contract tests)
* Performance regression detection

## Considered Options

* Unit tests only
* Unit + integration tests
* Unit + integration + property-based tests
* Full TDD with property-based and contract tests

## Decision Outcome

Chosen option: "Unit + integration + property-based + contract tests", because unit tests cover logic, integration tests cover transport/server, property-based tests (Hypothesis) cover envelope/payload edge cases, and contract tests validate backward compatibility (v0.1.0, v0.5.0). Chaos tests verify resilience.

### Consequences

* Good, because property-based tests find edge cases automatically
* Good, because contract tests catch breaking changes
* Good, because chaos tests validate failure handling
* Bad, because more test code; longer CI

### Confirmation

Tests in `tests/`: unit, integration, properties, contract, chaos. Hypothesis in `tests/properties/` and `tests/fuzz/`. See [Testing](../testing.md).

## Pros and Cons of the Options

### Unit only

* Good, because fast
* Bad, because misses integration and edge cases

### Unit + property-based + contract

* Good, because broad coverage; edge cases; compatibility
* Bad, because maintenance cost

## More Information

* [Testing Guide](../testing.md)
* tests/properties/, tests/contract/, tests/chaos/
* Rate limiting and integration test patterns (see test conftest)
