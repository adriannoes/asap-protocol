# Sprint S1: Type Safety Hardening (v1.4.0)

> **Source**: [PRD v1.4.0](../../../product-specs/prd/prd-v1.4-roadmap.md)
> **Phase**: v1.4.0 Sprint S1
> **Priority**: Medium — Improves reliability and security posture

## Relevant Files

- `sprint-S1-type-safety.md` - Task list and audit baseline (updated).
- `src/asap/models/payloads.py` - Core message payload definitions; added `TaskRequestConfig`, `TaskMetrics`.
- `tests/models/test_payloads.py` - Updated for typed config/metrics access.
- `src/asap/models/entities.py` - Added `CommonMetadata`; Conversation.metadata typed.
- `tests/models/test_entities.py` - Updated for CommonMetadata attribute access.
- `src/asap/models/envelope.py` - Typed payload; `payload_dict`; validator by payload_type.
- Multiple tests/examples - Use `payload_dict` for dict access.
- `src/asap/models/entities.py` - Domain entities (metadata, progress fields).
- `src/asap/models/envelope.py` - Protocol envelope (payload polymorphism).
- `src/asap/models/parts.py` - Content parts.
- `tests/models/test_payloads.py` - Verification tests.

### Notes

- Avoid `dict[str, Any]` where possible. Use `TypedDict` for fixed dictionaries or `pydantic.Json` where raw JSON storage is needed but structure is unknown/variable.
- Use `Union` for polymorphic fields where the set of types is known.

### Audit Baseline (Task 1.1 — 2025-02-18)

- **Mypy**: `uv run mypy src/asap` → Success (0 errors, 105 files).
- **Scope of `dict[str, Any]`** (primary targets per sprint):
  - **payloads.py**: `TaskRequest.input`, `TaskRequest.config`; `TaskResponse.result`, `TaskResponse.final_state`, `TaskResponse.metrics`; `TaskUpdate.progress`, `TaskUpdate.input_request`; `McpToolCall.arguments`, `McpToolCall.mcp_context`; `McpToolResult.result`; `McpResourceData.content`.
  - **entities.py**: `Skill.input_schema`, `Skill.output_schema`; `AuthScheme.oauth2`; `Conversation.metadata`; `Task.progress`; `StateSnapshot.data`.
  - **envelope.py**: `Envelope.payload`, `Envelope.extensions`.
  - **parts.py**: `StructuredPart.data`, `PromptTemplate.variables`.
- **Secondary** (transport, auth, errors, mcp, etc.): ~50+ additional usages; address after primary targets.

## Tasks

- [x] 1.0 Audit and Baseline
  - [x] 1.1 Run typing audit
    - **Command**: `uv run mypy src/asap` (check baseline errors)
    - **Why**: Establish scope of `Any` usage and existing type errors.
    - **Result**: Mypy passes (0 errors in 105 files). Baseline: no type errors; focus is on replacing `dict[str, Any]` for stronger type safety.

- [x] 2.0 Refactor Payloads (`payloads.py`)
  - [x] 2.1 Typed `TaskRequest` attributes
    - **File**: `src/asap/models/payloads.py`
    - **What**: Define specific `TypedDict` or Pydantic models for `TaskRequest.input` and `TaskRequest.config`.
    - **Why**: Prevent injection or misconfiguration. `config` often has known schema (model, temperature, etc).
    - **Result**: Added `TaskRequestConfig` model (timeout_seconds, priority, idempotency_key, streaming, persist_state, model, temperature). `input` kept as `dict[str, Any]` (skill-specific).
  - [x] 2.2 Typed `TaskResponse` metrics
    - **File**: `src/asap/models/payloads.py`
    - **What**: Replace `dict[str, Any]` for `metrics` with a proper `TaskMetrics` model.
    - **Why**: Metrics are critical for v1.3 Observability and must be consistent.
    - **Result**: Added `TaskMetrics` model (duration_ms, tokens_in, tokens_out, tokens_used, api_calls). Compatible with economics/hooks.py.

- [x] 3.0 Refactor Entities (`entities.py`)
  - [x] 3.1 Metadata Schema
    - **File**: `src/asap/models/entities.py`
    - **What**: Create a `CommonMetadata` TypedDict. Replace `metadata: dict[str, Any]` locally where applicable.
    - **Why**: Standardize metadata keys (e.g., source, timestamp).
    - **Result**: Added `CommonMetadata` Pydantic model (purpose, ttl_hours, source, timestamp, tags) with extra="allow". Conversation.metadata now typed.

- [x] 4.0 Refactor Envelope Polymorphism (`envelope.py`)
  - [x] 4.1 Discriminated Unions for Envelope Payload
    - **File**: `src/asap/models/envelope.py`
    - **What**: Change `payload: dict[str, Any]` to `payload: Union[TaskRequest, TaskResponse, Error, ...]` with a discriminator field.
    - **Why**: Allows Pydantic to parse the correct subclass automatically, ensuring type safety on deserialization.
    - **Result**: Payload typed as `PayloadType | dict[str, Any]`. Validator parses dict→PayloadType by payload_type. `payload_dict` property for backward compat. Fallback for unknown types and validation failures.

- [x] 5.0 Verification and Cleanup
  - [x] 5.1 Run Type Checker
    - **Command**: `uv run mypy src/asap`
    - **What**: Verify zero errors in touched files.
    - **Result**: Success: no issues found in 105 source files.
  - [x] 5.2 Test Suite
    - **Command**: `uv run pytest`
    - **What**: Full regression test.
    - **Result**: 2335 passed, 5 skipped, 35 warnings (pre-existing).
