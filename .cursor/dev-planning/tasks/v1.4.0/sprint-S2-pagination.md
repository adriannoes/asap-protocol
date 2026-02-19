# Sprint S2: Pagination in Storage Layer (v1.4.0)

> **Source**: [PRD v1.4.0](../../../product-specs/prd/prd-v1.4-roadmap.md)
> **Phase**: v1.4.0 Sprint S2
> **Priority**: Medium — acceptable for v1.3.0 scale, address when usage grows

## Relevant Files

- `src/asap/economics/sla_storage.py` - `SLAStorage` protocol and `SQLiteSLAStorage` class.
- `src/asap/transport/sla_api.py` - API endpoints consuming `SLAStorage`.
- `src/asap/state/stores/metering.py` - `MeteringStore` protocol and implementations.
- `src/asap/transport/usage_api.py` - API endpoints consuming `MeteringStore`.
- `tests/economics/test_sla_storage.py` - Storage logic tests.

### Notes

- Pagination should include a `limit` and `offset` parameter in API queries.
- The default limit should be reasonable (e.g. 50 or 100), and max limit enforced (e.g. 1000).
- Responses should include `total` count metadata so clients can calculate pages.

## Tasks

- [x] 1.0 SLA Storage Update (`sla_storage.py`)
  - [x] 1.1 Update `SLAStorage` Protocol
    - **File**: `src/asap/economics/sla_storage.py`
    - **What**: Add `limit: int | None`, `offset: int = 0` to `query_metrics`.
    - **Why**: Protocol definition must support pagination before implementations can use it.
  - [x] 1.2 Update `SQLiteSLAStorage` Implementation
    - **File**: `src/asap/economics/sla_storage.py`
    - **What**: Add `LIMIT ? OFFSET ?` to the SQL query string in `query_metrics`. Handle `None` limit (no LIMIT clause or large number).
    - **Why**: Push filtering to the database engine for performance.
  - [x] 1.3 `InMemorySLAStorage` Update
    - **File**: `src/asap/economics/sla_storage.py` (if present) or `tests/economics/conftest.py`
    - **What**: Update in-memory implementation to support slicing `[offset : offset + limit]`.
    - **Why**: Fix tests that use the fake storage so they don't break with new signature.

- [x] 2.0 SLA API Update (`sla_api.py`)
  - [x] 2.1 Pass Filter Params
    - **File**: `src/asap/transport/sla_api.py`
    - **What**: Update `get_sla_history` to extract `limit`/`offset` query params and pass them to `storage.query_metrics`.
    - **Why**: Enable clients to request specific pages.
  - [x] 2.2 Total Count Handling
    - **File**: `src/asap/transport/sla_api.py`
    - **What**: Ensure the `total` count returned is the total *matching* records (before pagination), not just the page size. Might require a separate `count_metrics` method in storage or window function.
    - **Verify**: `pytest tests/transport/test_sla_api.py`.

- [x] 3.0 Metering Storage Update (`metering.py`)
  - [x] 3.1 Update `MeteringStore` Protocol & Implementation
    - **File**: `src/asap/state/stores/metering.py`
    - **What**: Add `limit`/`offset` to `query()` method. Update SQLite implementation with SQL LIMIT.
    - **Why**: Consistency with SLA storage and performance.

- [x] 4.0 Usage API Update (`usage_api.py`)
  - [x] 4.1 Pass Pagination Params
    - **File**: `src/asap/transport/usage_api.py`
    - **What**: Update `get_usage` endpoint to use storage-level pagination.
    - **Verify**: Manual test via `curl` or new unit test.

- [x] 5.0 Verification and Testing
  - [x] 5.1 Unit Tests for Pagination
    - **File**: `tests/economics/test_sla_storage.py`
    - **What**: Add test cases: get page 1, get page 2, verify overlap/missing items, verify total count.
  - [x] 5.2 API Tests
    - **File**: `tests/transport/test_sla_api.py`
    - **What**: Verify `limit` and `offset` query params work as expected end-to-end.
