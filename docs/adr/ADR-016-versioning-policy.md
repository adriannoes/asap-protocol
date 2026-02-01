# ADR-016: Versioning Policy (SemVer, Contract Tests)

## Context and Problem Statement

ASAP protocol and library will evolve. We need a versioning strategy that signals breaking changes and allows clients to upgrade safely.

## Decision Drivers

* Clear semantic versioning (MAJOR.MINOR.PATCH)
* Backward compatibility guarantees
* Contract tests for compatibility
* Protocol version (asap_version) vs library version

## Considered Options

* No formal versioning
* SemVer for library only
* SemVer + protocol version + contract tests
* CalVer

## Decision Outcome

Chosen option: "SemVer for library + asap_version in envelope + contract tests", because library follows SemVer; envelope has asap_version (e.g., "0.1") for protocol evolution. Contract tests (tests/contract/, tests/compatibility/) validate backward compatibility (v0.1.0, v0.5.0, v1.0.0).

### Consequences

* Good, because SemVer signals breaking (MAJOR), additive (MINOR), patch (PATCH)
* Good, because contract tests catch accidental breaks
* Good, because asap_version allows protocol evolution
* Bad, because contract test maintenance across versions

### Confirmation

pyproject.toml version. Contract tests in tests/contract/, tests/compatibility/. Envelope.asap_version.

## Pros and Cons of the Options

### SemVer only

* Good, because standard
* Bad, because no automated compatibility checks

### SemVer + contract tests

* Good, because automated compatibility verification
* Bad, because test matrix growth

## More Information

* [Migration Guide](../migration.md)
* tests/compatibility/test_v0_1_0_compatibility.py, test_v0_3_0_compatibility.py
* Envelope.asap_version field
