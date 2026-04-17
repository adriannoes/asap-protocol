# Tasks: v2.2.0 Protocol Hardening — Sprint Index

**Status: ✅ COMPLETE** — v2.2.0 released; all sprints S0–S6 delivered.

Based on [PRD v2.2 Protocol Hardening](../../product-specs/prd/prd-v2.2-protocol-hardening.md). Each sprint was delivered as a PR sequence.

## Prerequisites
- [x] v2.1.1 Tech Debt & Security Cleared — See [tasks-v2.2.0-tech-debt.md](./tasks-v2.2.0-tech-debt.md)
- [x] A2H Integration completed — See [tasks-a2h-integration.md](./tasks-a2h-integration.md)

## Sprint Plan

Each sprint maps to a PR. Execute in order — each sprint depends on the previous.

| Sprint | Focus | PRD Sections | Priority | Status |
|--------|-------|-------------|----------|--------|
| **S0** | [Per-Runtime-Agent Identity](./sprint-S0-agent-identity.md) | §4.1 | P0 | ✅ |
| **S1** | [Capabilities & Lifecycle](./sprint-S1-capabilities-lifecycle.md) | §4.2, §4.3 | P0 | ✅ |
| **S2** | [Approval Flows & Self-Auth Prevention](./sprint-S2-approval-flows.md) | §4.4, §4.5 | P1 | ✅ |
| **S3** | [Error Taxonomy & Streaming/SSE](./sprint-S3-errors-streaming.md) | §4.6, §4.7 | P1 | ✅ |
| **S4** | [Versioning & Async Protocol](./sprint-S4-versioning-async.md) | §4.8, §4.9 | P1 | ✅ |
| **S5** | [Batch, Audit & Compliance](./sprint-S5-batch-audit-compliance.md) | §4.10, §4.11, §4.12, §4.13 | P2 | ✅ |
| **S6** | [Release v2.2.0](./sprint-S6-release.md) | — | — | ✅ |

## Dependency Graph

```
S0 (Identity) ──► S1 (Capabilities + Lifecycle) ──► S2 (Approval Flows)
                                                          │
S3 (Errors + Streaming) ◄────────────────────────────────┘
     │
     ▼
S4 (Versioning + Async) ──► S5 (Batch + Audit + Compliance) ──► S6 (Release)
```

## Definition of Done (v2.2.0)

- [x] All P0 features (Identity, Capabilities, Lifecycle) implemented and tested
- [x] All P1 features (Approval, Streaming, Errors, Versioning, Async) implemented and tested
- [x] All P2 features (Batch, Compliance, Audit) implemented and tested
- [x] Test coverage >= 90% for new code
- [x] `uv run mypy src/` passes with zero errors
- [x] `uv run ruff check .` passes
- [x] E2E tests passing for identity, streaming, and batch
- [x] CHANGELOG.md updated
- [x] v2.2.0 published to PyPI
