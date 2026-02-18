# v1.4.0 Roadmap: Resilience & Scale

> **Focus**: Addressing technical debt and scalability bottlenecks identified in v1.3.0.
> **Status**: PLANNING
> **Timeline**: Post-v1.3.0

## Goals

1.  **Type Safety**: Harden the data model by replacing loose `dict[str, Any]` with `TypedDict` or `pydantic.Json`.
2.  **Scalability**: Implement pagination in storage layers to handle large datasets (SLA history, Usage metering).

## Sprints

### Sprint S1: Type Safety Hardening
- **Objective**: Improve code reliability and reduce runtime errors.
- **Key Tasks**:
    - Audit and replace `dict[str, Any]` in `payloads.py`, `entities.py`, etc.
    - Introduce `TypedDict` for known schemas.
- **Reference**: `sprint-S1-type-safety.md`

### Sprint S2: Storage Pagination
- **Objective**: Prevent OOM errors and improve query performance.
- **Key Tasks**:
    - Add `LIMIT`/`OFFSET` to `SLAStorage` and `MeteringStorage` protocols.
    - Implement pagination in `SQLite` backends.
    - Update `sla_api` and `usage_api` to use storage-level pagination.
- **Reference**: `sprint-S2-pagination.md`
