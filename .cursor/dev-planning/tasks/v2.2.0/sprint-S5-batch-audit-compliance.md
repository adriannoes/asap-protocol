# Sprint S5: Batch, Audit & Compliance

**PRD**: §4.10 A2H Completion (P1, ✅ done), §4.11 Batch Operations (P2), §4.12 Compliance Harness v2 (P2), §4.13 Audit Logging (P2)
**Branch**: `feat/batch-audit-compliance`
**PR Scope**: JSON-RPC batch, audit logging with hash chain, compliance harness v2
**Depends on**: Sprint S4 (Versioning & Async)

## Relevant Files

### New Files
- `src/asap/economics/audit.py` — AuditEntry, AuditStore Protocol, InMemory/SQLite implementations
- `tests/economics/test_audit.py` — Audit tests
- `src/asap/testing/compliance.py` — Compliance Harness v2 (`run_compliance_harness_v2`, JSON report)
- `tests/testing/test_compliance_v2.py` — Harness v2 tests (ASGI stack, JSON export, categories)

### Modified Files
- `src/asap/economics/__init__.py` — exports audit types and stores
- `src/asap/testing/__init__.py` — exports compliance harness v2 types and runner
- `src/asap/transport/server.py` — JSON-RPC batch on POST `/asap`, `max_batch_size`, rate limit `check_n` integration; optional `audit_store`, `GET /audit`, write-audit hooks
- `src/asap/transport/jsonrpc.py` — `DEFAULT_MAX_BATCH_SIZE` constant
- `src/asap/transport/rate_limit.py` — `ASAPRateLimiter.check_n()` for batch cost
- `src/asap/transport/client.py` — `ASAPClient.batch()` (JSON array body)
- `tests/transport/test_http_client.py` — batch client test
- `tests/transport/integration/test_server_core.py` — batch + updated primitive/array expectations
- `tests/transport/test_server.py` — stream/array parsing expectations, `handle_message` test fixture, `TestAuditLogging` for `/audit` and task.request audit

---

## Tasks

### 1.0 Batch Operations

- [x] 1.1 Server-side batch request handling
  - **File**: `src/asap/transport/server.py` (modify), `src/asap/transport/jsonrpc.py` (modify)
  - **What**: Detect JSON array (vs object). Process each request, collect responses. Return JSON array. Rate limiting counts as N requests.
  - **Verify**: Valid batch, mixed success/error, empty batch (error), oversized batch (error)

- [x] 1.2 Batch size limit configuration
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `max_batch_size: int = 50`. Return error if exceeded.
  - **Verify**: Batch of 51 returns error

- [x] 1.3 Client-side batch method
  - **File**: `src/asap/transport/client.py` (modify; PRD cited `http_client.py` — client lives under `transport/client.py`)
  - **What**: `async def batch(requests: list[Envelope]) -> list[Envelope]`. Serializes as JSON array.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "batch"`

### 2.0 Audit Logging

- [x] 2.1 Define AuditStore Protocol and models
  - **File**: `src/asap/economics/audit.py` (create)
  - **What**: `AuditEntry` (id, timestamp, operation, agent_urn, details, prev_hash, hash). `AuditStore` Protocol with `append(entry)`, `query(urn, start, end)`, `verify_chain()`.
  - **Verify**: Model validation, protocol conformance

- [x] 2.2 In-memory and SQLite AuditStore implementations
  - **File**: `src/asap/economics/audit.py` (extend)
  - **What**: Hash chain: each entry hashes (prev_hash + timestamp + operation + details). Tamper detection: modify an entry → chain validation fails.
  - **Verify**: Hash chain integrity test

- [x] 2.3 Audit logging hooks in transport
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Optional `audit_store` parameter. Log all write operations via middleware.
  - **Verify**: Task creation and state transitions logged

- [x] 2.4 Audit query API
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `GET /audit` with `urn`, `start`, `end` query params. Paginated.
  - **Verify**: `uv run pytest tests/transport/test_server.py -k "audit"`

### 3.0 Compliance Harness v2

- [x] 3.1 Identity & capability compliance checks
  - **File**: `src/asap/testing/compliance.py` (create/modify)
  - **What**: Checks for agent registration, JWT verification, capability enforcement, lifecycle clocks.
  - **Verify**: Passes against test agent with identity features

- [x] 3.2 Streaming compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: SSE endpoint responds, event format valid, stream terminates with final event.
  - **Verify**: Passes against streaming test agent

- [x] 3.3 Error handling compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: Errors include RecoverableError/FatalError, recovery hints present, codes in range.
  - **Verify**: Passes against test agent with error taxonomy

- [x] 3.4 Version negotiation compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: ASAP-Version header present, negotiation works, backward compat.
  - **Verify**: Passes against test agent with versioning

- [x] 3.5 Batch & audit compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: Batch accepted, array response, size limit. Audit log queryable.
  - **Verify**: Passes against test agent with batch/audit

- [x] 3.6 Compliance report export
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: JSON report with score, check results, summary.
  - **Verify**: Report is valid JSON

---

## Definition of Done

- [x] JSON-RPC batch endpoint handles N requests in single POST
- [x] Batch size limit enforced
- [x] `ASAPClient.batch()` method working
- [x] Tamper-evident audit log with hash chain
- [x] All write operations logged
- [x] Audit query API working
- [x] Compliance Harness v2 covers: identity, capabilities, streaming, errors, versioning, batch, audit
- [x] Compliance report exportable as JSON
- [x] Test coverage >= 90% for new code
