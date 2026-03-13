# ASAP Protocol: Unified ADR Index

> **Purpose**: Single reference for all Architecture Decision Records across both documentation locations.
>
> **Created**: 2026-03-13
> **Context**: The project has two ADR collections with overlapping numbering. This index provides a unified view.

---

## ADR Collections

### Collection 1: Implementation ADRs (`docs/adr/`)

Format: MADR (Markdown Any Decision Records). Focus: implementation-level technical decisions.

| ADR | Title | Status | File |
|-----|-------|--------|------|
| ADR-001 | ULID for ID Generation | Accepted | `docs/adr/ADR-001-ulid-for-id-generation.md` |
| ADR-002 | Async-First API Design | Accepted | `docs/adr/ADR-002-async-first-api-design.md` |
| ADR-003 | JSON-RPC 2.0 Binding | Accepted | `docs/adr/ADR-003-jsonrpc20-binding.md` |
| ADR-004 | Pydantic for Models | Accepted | `docs/adr/ADR-004-pydantic-for-models.md` |
| ADR-005 | State Machine Design | Accepted | `docs/adr/ADR-005-state-machine-design.md` |
| ADR-006 | Security Defaults | Accepted | `docs/adr/ADR-006-security-defaults.md` |
| ADR-007 | FastAPI for Server | Accepted | `docs/adr/ADR-007-fastapi-for-server.md` |
| ADR-008 | httpx for Client | Accepted | `docs/adr/ADR-008-httpx-for-client.md` |
| ADR-009 | Snapshot vs Event-Sourced | Accepted | `docs/adr/ADR-009-snapshot-vs-event-sourced.md` |
| ADR-010 | Python 3.13+ Requirement | Accepted | `docs/adr/ADR-010-python-313-requirement.md` |
| ADR-011 | Per-Sender Rate Limiting | Accepted | `docs/adr/ADR-011-per-sender-rate-limiting.md` |
| ADR-012 | Error Taxonomy | Accepted | `docs/adr/ADR-012-error-taxonomy.md` |
| ADR-013 | MCP Integration Approach | Accepted | `docs/adr/ADR-013-mcp-integration-approach.md` |
| ADR-014 | Testing Strategy | Accepted | `docs/adr/ADR-014-testing-strategy.md` |
| ADR-015 | Observability Design | Accepted | `docs/adr/ADR-015-observability-design.md` |
| ADR-016 | Versioning Policy | Accepted | `docs/adr/ADR-016-versioning-policy.md` |
| ADR-017 | Failure Injection Strategy | Accepted | `docs/adr/ADR-017-failure-injection-strategy.md` |
| ADR-018 | Streaming Transport (SSE) | Accepted | `docs/adr/ADR-018-streaming-transport.md` |
| ADR-019 | Unified Versioning | Accepted | `docs/adr/ADR-019-unified-versioning.md` |

### Collection 2: Strategic ADRs (`.cursor/product-specs/decision-records/`)

Format: Question-based (Q-number) organized by topic. Focus: architecture, protocol, security, technology, and product strategy decisions.

| Q# / ADR | Title | Status | File | Topic |
|-----------|-------|--------|------|-------|
| Q1 | Event-Sourced State for MVP? | Modified | `01-architecture.md` | Architecture |
| Q3 | P2P Default Practical? | Modified | `01-architecture.md` | Architecture |
| Q4 | Consistency Model | Added | `01-architecture.md` | Architecture |
| Q13 / ADR-13 | State Management Strategy | Active | `01-architecture.md` | Architecture |
| Q14 / ADR-14 | Agent Liveness Protocol | Active | `01-architecture.md` | Architecture |
| Q2 | JSON-RPC Over REST? | Kept | `02-protocol.md` | Protocol |
| Q5 | MCP Envelope Optimal? | Kept | `02-protocol.md` | Protocol |
| Q7 | Error Model Complete? | Added | `02-protocol.md` | Protocol |
| Q16 / ADR-16 | WebSocket Message Ack | Active | `02-protocol.md` | Protocol |
| Q8 | MVP Security Sufficient? | Kept | `03-security.md` | Security |
| Q17 / ADR-17 | Trust Model & Identity Binding | Active | `03-security.md` | Security |
| Q20 / ADR-20 | Ed25519 Security Hardening | Active | `03-security.md` | Security |
| Q9 | C/Rust for Performance? | Kept | `04-technology.md` | Technology |
| Q11 | Web Marketplace Stack | Kept | `04-technology.md` | Technology |
| Q12 / ADR-12 | OAuth Library (Authlib) | Active | `04-technology.md` | Technology |
| Q23 / ADR-23 | Mypy Strategy | Active | `04-technology.md` | Technology |
| Q25 / ADR-25 | SDK Cache Strategy | Active | `04-technology.md` | Technology |
| Q6 | CalVer for Protocol? | Rejected (ADR-019) | `05-product-strategy.md` | Product |
| Q10 | Build vs Buy Evals? | Hybrid | `05-product-strategy.md` | Product |
| Q15 / ADR-15 | Lite Registry | Active | `05-product-strategy.md` | Product |
| Q18 / ADR-18 | Agent Registration (IssueOps) | Active | `05-product-strategy.md` | Product |
| Q19 / ADR-19 | Design Strategy | Active | `05-product-strategy.md` | Product |
| Q21 / ADR-21 | Pricing at Launch | Active | `05-product-strategy.md` | Product |
| Q22 / ADR-22 | Register-Agent Template | Active | `05-product-strategy.md` | Product |
| Q24 / ADR-24 | asap-mcp-server Language | Active | `05-product-strategy.md` | Product |
| Q26 / ADR-26 | Cross-Platform Domain | Active | `05-product-strategy.md` | Product |

---

## Number Collisions

The following ADR numbers appear in BOTH collections with DIFFERENT topics:

| Number | Collection 1 (docs/adr/) | Collection 2 (decision-records/) |
|--------|-------------------------|----------------------------------|
| 12 | Error Taxonomy | OAuth Library (Authlib) |
| 13 | MCP Integration Approach | State Management Strategy |
| 15 | Observability Design | Lite Registry |
| 16 | Versioning Policy | WebSocket Message Ack |
| 17 | Failure Injection Strategy | Trust Model & Identity Binding |

### Resolution

**Going forward** (ADR-018+): All new ADRs use the `docs/adr/` numbering sequence (ADR-018, ADR-019, ...). Strategic decisions in `decision-records/` use Q-numbers (Q1, Q2, ...) without the "ADR-" prefix to avoid collisions. Historical collisions are documented here for reference but not renumbered to avoid breaking existing links.

---

## Change Log

| Date | Change |
|------|--------|
| 2026-03-13 | Initial unified index created during v2.2 strategic review |
