# Sprint S1: Type Safety Hardening (v1.4.0)

> **Source**: [PRD v1.4.0](../../../product-specs/prd/prd-v1.4-roadmap.md)
> **Phase**: v1.4.0 Sprint S1
> **Priority**: Medium — Improves reliability and security posture

## Relevant Files

- `src/asap/models/payloads.py` - Core message payload definitions (primary target).
- `src/asap/models/entities.py` - Domain entities (metadata, progress fields).
- `src/asap/models/envelope.py` - Protocol envelope (payload polymorphism).
- `src/asap/models/parts.py` - Content parts.
- `tests/models/test_payloads.py` - Verification tests.

### Notes

- Avoid `dict[str, Any]` where possible. Use `TypedDict` for fixed dictionaries or `pydantic.Json` where raw JSON storage is needed but structure is unknown/variable.
- Use `Union` for polymorphic fields where the set of types is known.

## Tasks

- [ ] 1.0 Audit and Baseline
  - [ ] 1.1 Run typing audit
    - **Command**: `uv run mypy src/asap` (check baseline errors)
    - **Why**: Establish scope of `Any` usage and existing type errors.

- [ ] 2.0 Refactor Payloads (`payloads.py`)
  - [ ] 2.1 Typed `TaskRequest` attributes
    - **File**: `src/asap/models/payloads.py`
    - **What**: Define specific `TypedDict` or Pydantic models for `TaskRequest.input` and `TaskRequest.config`.
    - **Why**: Prevent injection or misconfiguration. `config` often has known schema (model, temperature, etc).
  - [ ] 2.2 Typed `TaskResponse` metrics
    - **File**: `src/asap/models/payloads.py`
    - **What**: Replace `dict[str, Any]` for `metrics` with a proper `TaskMetrics` model.
    - **Why**: Metrics are critical for v1.3 Observability and must be consistent.

- [ ] 3.0 Refactor Entities (`entities.py`)
  - [ ] 3.1 Metadata Schema
    - **File**: `src/asap/models/entities.py`
    - **What**: Create a `CommonMetadata` TypedDict. Replace `metadata: dict[str, Any]` locally where applicable.
    - **Why**: Standardize metadata keys (e.g., source, timestamp).

- [ ] 4.0 Refactor Envelope Polymorphism (`envelope.py`)
  - [ ] 4.1 Discriminated Unions for Envelope Payload
    - **File**: `src/asap/models/envelope.py`
    - **What**: Change `payload: dict[str, Any]` to `payload: Union[TaskRequest, TaskResponse, Error, ...]` with a discriminator field.
    - **Why**: Allows Pydantic to parse the correct subclass automatically, ensuring type safety on deserialization.

- [ ] 5.0 Verification and Cleanup
  - [ ] 5.1 Run Type Checker
    - **Command**: `uv run mypy src/asap`
    - **What**: Verify zero errors in touched files.
  - [ ] 5.2 Test Suite
    - **Command**: `uv run pytest`
    - **What**: Full regression test.
