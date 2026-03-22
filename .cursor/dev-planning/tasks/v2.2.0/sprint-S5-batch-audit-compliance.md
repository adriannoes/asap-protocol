# Sprint S5: Batch, Audit & Compliance

**PRD**: §4.10 A2H Completion (P1, ✅ done), §4.11 Batch Operations (P2), §4.12 Compliance Harness v2 (P2), §4.13 Audit Logging (P2)
**Branch**: `feat/batch-audit-compliance`
**PR Scope**: JSON-RPC batch, audit logging with hash chain, compliance harness v2
**Depends on**: Sprint S4 (Versioning & Async)

## Relevant Files

### New Files
- `src/asap/economics/audit.py` — AuditEntry, AuditStore Protocol, InMemory/SQLite implementations
- `tests/economics/test_audit.py` — Audit tests
- `src/asap/testing/compliance.py` — Compliance Harness v2

### Modified Files
- `src/asap/transport/server.py` — Batch request handling, audit hooks, batch size limit
- `src/asap/transport/jsonrpc.py` — JSON array detection for batch
- `src/asap/transport/http_client.py` — `ASAPClient.batch()` method

---

## Tasks

### 1.0 Batch Operations

- [ ] 1.1 Server-side batch request handling
  - **File**: `src/asap/transport/server.py` (modify), `src/asap/transport/jsonrpc.py` (modify)
  - **What**: Detect JSON array (vs object). Process each request, collect responses. Return JSON array. Rate limiting counts as N requests.
  - **Verify**: Valid batch, mixed success/error, empty batch (error), oversized batch (error)

- [ ] 1.2 Batch size limit configuration
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `max_batch_size: int = 50`. Return error if exceeded.
  - **Verify**: Batch of 51 returns error

- [ ] 1.3 Client-side batch method
  - **File**: `src/asap/transport/http_client.py` (modify)
  - **What**: `async def batch(requests: list[Envelope]) -> list[Envelope]`. Serializes as JSON array.
  - **Verify**: `uv run pytest tests/transport/test_http_client.py -k "batch"`

### 2.0 Audit Logging

- [ ] 2.1 Define AuditStore Protocol and models
  - **File**: `src/asap/economics/audit.py` (create)
  - **What**: `AuditEntry` (id, timestamp, operation, agent_urn, details, prev_hash, hash). `AuditStore` Protocol with `append(entry)`, `query(urn, start, end)`, `verify_chain()`.
  - **Verify**: Model validation, protocol conformance

- [ ] 2.2 In-memory and SQLite AuditStore implementations
  - **File**: `src/asap/economics/audit.py` (extend)
  - **What**: Hash chain: each entry hashes (prev_hash + timestamp + operation + details). Tamper detection: modify an entry → chain validation fails.
  - **Verify**: Hash chain integrity test

- [ ] 2.3 Audit logging hooks in transport
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: Optional `audit_store` parameter. Log all write operations via middleware.
  - **Verify**: Task creation and state transitions logged

- [ ] 2.4 Audit query API
  - **File**: `src/asap/transport/server.py` (modify)
  - **What**: `GET /audit` with `urn`, `start`, `end` query params. Paginated.
  - **Verify**: `uv run pytest tests/transport/test_server.py -k "audit"`

### 3.0 Compliance Harness v2

- [ ] 3.1 Identity & capability compliance checks
  - **File**: `src/asap/testing/compliance.py` (create/modify)
  - **What**: Checks for agent registration, JWT verification, capability enforcement, lifecycle clocks.
  - **Verify**: Passes against test agent with identity features

- [ ] 3.2 Streaming compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: SSE endpoint responds, event format valid, stream terminates with final event.
  - **Verify**: Passes against streaming test agent

- [ ] 3.3 Error handling compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: Errors include RecoverableError/FatalError, recovery hints present, codes in range.
  - **Verify**: Passes against test agent with error taxonomy

- [ ] 3.4 Version negotiation compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: ASAP-Version header present, negotiation works, backward compat.
  - **Verify**: Passes against test agent with versioning

- [ ] 3.5 Batch & audit compliance checks
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: Batch accepted, array response, size limit. Audit log queryable.
  - **Verify**: Passes against test agent with batch/audit

- [ ] 3.6 Compliance report export
  - **File**: `src/asap/testing/compliance.py` (extend)
  - **What**: JSON report with score, check results, summary.
  - **Verify**: Report is valid JSON

---

## Definition of Done

- [ ] JSON-RPC batch endpoint handles N requests in single POST
- [ ] Batch size limit enforced
- [ ] `ASAPClient.batch()` method working
- [ ] Tamper-evident audit log with hash chain
- [ ] All write operations logged
- [ ] Audit query API working
- [ ] Compliance Harness v2 covers: identity, capabilities, streaming, errors, versioning, batch, audit
- [ ] Compliance report exportable as JSON
- [ ] Test coverage >= 90% for new code
