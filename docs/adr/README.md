# Architecture Decision Records

> Architecture Decision Records (ADRs) document key design decisions for the ASAP protocol.

---

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [ADR-001](ADR-001-ulid-for-id-generation.md) | ULID for ID Generation | Accepted |
| [ADR-002](ADR-002-async-first-api-design.md) | Async-First API Design | Accepted |
| [ADR-003](ADR-003-jsonrpc20-binding.md) | JSON-RPC 2.0 Binding | Accepted |
| [ADR-004](ADR-004-pydantic-for-models.md) | Pydantic for Models | Accepted |
| [ADR-005](ADR-005-state-machine-design.md) | State Machine Design for Task Lifecycle | Accepted |
| [ADR-006](ADR-006-security-defaults.md) | Security Defaults | Accepted |
| [ADR-007](ADR-007-fastapi-for-server.md) | FastAPI for Server | Accepted |
| [ADR-008](ADR-008-httpx-for-client.md) | httpx for Client | Accepted |
| [ADR-009](ADR-009-snapshot-vs-event-sourced.md) | Snapshot vs Event-Sourced State Persistence | Accepted |
| [ADR-010](ADR-010-python-313-requirement.md) | Python 3.13+ Requirement | Accepted |
| [ADR-011](ADR-011-per-sender-rate-limiting.md) | Per-Sender Rate Limiting | Accepted |
| [ADR-012](ADR-012-error-taxonomy.md) | Error Taxonomy | Accepted |
| [ADR-013](ADR-013-mcp-integration-approach.md) | MCP Integration Approach | Accepted |
| [ADR-014](ADR-014-testing-strategy.md) | Testing Strategy (TDD, Property-Based) | Accepted |
| [ADR-015](ADR-015-observability-design.md) | Observability Design (trace_id, correlation_id) | Accepted |
| [ADR-016](ADR-016-versioning-policy.md) | Versioning Policy (SemVer, Contract Tests) | Accepted |
| [ADR-017](ADR-017-failure-injection-strategy.md) | Failure Injection Strategy (Chaos Testing) | Accepted |

---

## Template

To create a new ADR, copy [template.md](template.md) and fill in the sections. Use MADR format.

---

## Status Legend

- **Accepted**: Decision implemented and in use
- **Superseded**: Replaced by another ADR
- **Deprecated**: No longer applicable
- **Proposed**: Under discussion
