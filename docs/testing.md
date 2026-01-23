# Testing

This guide describes the testing strategy and how to run tests locally.

## Test Structure

- `tests/models/`: unit tests for core models
- `tests/state/`: state machine and snapshot store tests
- `tests/transport/`: JSON-RPC, server, handlers, and client tests
- `tests/e2e/`: end-to-end agent interaction tests

## Running Tests

Use `uv` to run tests with the project environment:

```bash
uv run pytest
```

Run a specific module:

```bash
uv run pytest tests/models/
```

Run with coverage:

```bash
uv run pytest --cov=src tests/
```

## Unit Tests

Unit tests validate isolated components such as models and utilities. Keep
fixtures minimal and prefer deterministic inputs.

## Integration Tests

Integration tests validate component interactions within the transport and
state layers (e.g., JSON-RPC serialization, handler dispatch, client/server).

## E2E Tests

End-to-end tests validate the full agent flow using the demo agents. These
tests live in `tests/e2e/` and should be reserved for cross-component behavior.

## Guidelines

- Use `pytest` for all tests.
- Keep tests deterministic and fast.
- Prefer explicit assertions over implicit behavior.
