# ADR-010: Python 3.13+ Requirement

## Context and Problem Statement

ASAP protocol must target a Python version that provides modern features (type hints, async, performance) while balancing adoption and ecosystem support.

## Decision Drivers

* Type system (PEP 484, ParamSpec, TypeAlias)
* Async/await maturity
* Performance (faster interpreter)
* Ecosystem support (dependencies)
* Long-term support horizon

## Considered Options

* Python 3.10
* Python 3.11
* Python 3.12
* Python 3.13

## Decision Outcome

Chosen option: "Python 3.13+", because it provides the latest performance improvements, type system features, and ensures ASAP targets a modern baseline. pyproject.toml specifies `requires-python = ">=3.13"`.

### Consequences

* Good, because access to latest language features
* Good, because better performance for high-throughput agents
* Bad, because narrower install base; some users on older Python
* Neutral, because uv/pip handle version checks

### Confirmation

pyproject.toml: `requires-python = ">=3.13"`. CI tests on 3.13.

## Pros and Cons of the Options

### Python 3.10

* Good, because wider adoption
* Bad, because misses 3.11+ performance and features

### Python 3.13

* Good, because latest performance and features
* Bad, because newer; some distros may not ship it yet

## More Information

* pyproject.toml: `requires-python = ">=3.13"`
* CI: .github/workflows/ci.yml
