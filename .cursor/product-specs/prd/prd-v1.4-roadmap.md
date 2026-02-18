# PRD: ASAP Protocol v1.4.0 — Resilience & Scale

> **Product Requirements Document**
>
> **Version**: 1.4.0
> **Status**: DRAFT
> **Created**: 2026-02-18
> **Last Updated**: 2026-02-18

---

## 1. Executive Summary

### 1.1 Purpose

v1.4.0 is a **consolidation and hardening release** focused on technical debt and scalability bottlenecks identified during the v1.3.0 cycle. It prepares the codebase for the v2.0 Marketplace launch by ensuring:

- **Reliability**: Eliminating runtime type errors via stricter Pydantic models.
- **Scalability**: Preventing memory exhaustion in storage layers via pagination.

### 1.2 Strategic Context

While v1.3.0 delivered new features (SLA, Metering), v1.4.0 acts as a "stability checkpoint" before the major v2.0 release. It ensures the core protocol implementation is robust enough to handle the increased load and scrutiny of a public marketplace.

**Prerequisite**: v1.3.0 (Observability) released.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| **Zero Runtime Type Errors** | Pass `mypy` strict mode without `Any` in core models | P1 |
| **Stable Memory Usage** | API memory usage constant O(1) regardless of record count | P1 |
| **Query Performance** | Storage queries <50ms for large datasets | P2 |

---

## 3. Improvements & Requirements

### 3.1 Type Safety Hardening (S1)

**Problem**: Extensive use of `dict[str, Any]` in `payloads.py` and `entities.py` bypasses Pydantic validation, leading to potential "field missing" errors at runtime and security risks (injection).

**Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| TS-001 | Replace `dict[str, Any]` with `TypedDict` or `pydantic.Json` in core models | MUST |
| TS-002 | Define explicit schemas for `metadata`, `progress`, and `metrics` fields | MUST |
| TS-003 | Enforce strict typing in all new Pydantic models | MUST |

### 3.2 Storage Pagination (S2)

**Problem**: `GET /sla/history` and `GET /usage` endpoints fetch **all** records into memory before slicing, causing O(N) memory usage. This is a vulnerability (DoS) and a scalability bottleneck.

**Requirements**:

| ID | Requirement | Priority |
|----|-------------|----------|
| PAG-001 | Add `limit` and `offset` to `Storage` protocols (SLA, Metering) | MUST |
| PAG-002 | Implement SQL-level `LIMIT/OFFSET` in SQLite backends | MUST |
| PAG-003 | Update API endpoints to pass pagination params to storage | MUST |
| PAG-004 | Return total record count for UI pagination | MUST |

---

## 4. Technical Implementation

### 4.1 Sprints

- **Sprint S1 (Type Safety)**: Refactor `asap.models`.
- **Sprint S2 (Pagination)**: Refactor `asap.state.stores` and `asap.transport`.

### 4.2 Breaking Changes

- **API**: None (Pagination params are optional or backward compatible).
- **Internal**: `Storage` protocol signatures will change (adding `limit`/`offset`).

---

## 5. Success Metrics

- [ ] All usages of `dict[str, Any]` in core models audited/removed.
- [ ] `GET /sla/history` with 1M records returns in <50ms with minimal RAM increase.

---

## 6. Related Documents

- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)
- **v1.4 Roadmap**: [tasks-v1.4.0-roadmap.md](../../dev-planning/tasks/v1.4.0/tasks-v1.4.0-roadmap.md)
