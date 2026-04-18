# Tasks: v2.3.0 Adoption Multiplier — Sprint Index

**Status: 🟡 PLANNED** — Rescoped 2026-04-17 from "Scale & Registry" after v2.2.0 audit confirmed 120/500 agents (trigger unmet).

Based on [PRD v2.3 Adoption Multiplier](../../../product-specs/prd/prd-v2.3-scale.md). Each sprint maps to a PR sequence.

## Prerequisites
- [x] v2.2.0 Protocol Hardening released (2026-04-15)
- [ ] v2.2.1 carry-over patch released — See [tasks-v2.2.1-patch.md](../v2.2.1/tasks-v2.2.1-patch.md)
- [x] Capability model stable (v2.2)
- [x] Identity model stable (v2.2)
- [x] Streaming/SSE operational (v2.2)
- [x] Compliance Harness v2 operational (v2.2)

## Sprint Plan

| Sprint | Focus | PRD Sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S1** | [OpenAPI Adapter (Python)](./sprint-S1-openapi-adapter.md) | §4.1 (OA-001..011) | P0 | 🟡 |
| **S2** | [TypeScript Client SDK](./sprint-S2-typescript-sdk.md) | §4.2 (TS-001..011) | P0 | 🟡 |
| **S3** | [Auto-Registration](./sprint-S3-auto-registration.md) | §4.3 (AUTO-001..007) | P0 | 🟡 |
| **S4** | [Capability Escalation + ASAP Challenge](./sprint-S4-escalation-challenge.md) | §4.4 (ESC-001..004), §4.5 (CHAL-001..004) | P1/P2 | 🟡 |
| **S5** | Release v2.3.0 | — | — | 🟡 |

## Dependency Graph

```
S1 (OpenAPI Adapter ─ Python) ──► S4 (Escalation + Challenge) ──► S5 (Release)
                                              ▲
S2 (TypeScript SDK) ─────────────────────────┤
                                              │
S3 (Auto-Registration) ──────────────────────┘
```

S1, S2, and S3 are independent and can run in parallel with three contributors. S4 depends on S1 (escalation flow used by OpenAPI-derived agents) and on S2 (escalation client method needed in TS SDK). S5 depends on S1–S4.

## Definition of Done (v2.3.0)

- [ ] **OpenAPI Adapter**: Python package `asap.adapters.openapi` published; reference example onboards a public OpenAPI spec end-to-end
- [ ] **TypeScript SDK**: `@asap-protocol/client@2.3.0` published to npm with Vercel AI / OpenAI / Anthropic adapters
- [ ] **Auto-Registration**: `POST /registry/agents` endpoint live; bot-driven PR flow merging into `registry.json` automatically when Compliance Harness v2 passes
- [ ] **Capability Escalation**: `POST /asap/agent/request-capability` operational with approval flow integration
- [ ] **ASAP Challenge**: `WWW-Authenticate: ASAP discovery=...` middleware shipped; client recognizes scheme
- [ ] Test coverage ≥90% for new modules (Python and TS)
- [ ] `uv run mypy src/` and `uv run ruff check .` pass
- [ ] TS SDK passes `pnpm test`, `pnpm lint`, `pnpm typecheck`
- [ ] E2E test: spec URL → onboarded agent → invocable capability with constraints
- [ ] CHANGELOG.md updated under `[2.3.0]`
- [ ] `asap-protocol==2.3.0` published to PyPI
- [ ] `@asap-protocol/client@2.3.0` published to npm
- [ ] Tag `v2.3.0` on `main` + GitHub Release notes
- [ ] Docker `ghcr.io/adriannoes/asap-protocol:v2.3.0` and `:latest` rebuilt

## Estimated Effort

| Sprint | Effort |
|--------|--------|
| S1 OpenAPI Adapter | 2 weeks (1 contributor) |
| S2 TypeScript SDK | 3 weeks (1 contributor) |
| S3 Auto-Registration | 1.5 weeks (1 contributor) |
| S4 Escalation + Challenge | 1 week (1 contributor) |
| S5 Release | 0.5 week |

Total target: **6–8 weeks** end-to-end (parallelism reduces wall-clock to ~4 weeks).

## Strategic Bet

The 500-agent trigger (original v2.3 Registry API gate) is treated as an **outcome metric**, not a prerequisite. The hypothesis: OpenAPI Adapter (zero-code) + TypeScript SDK (dominant AI ecosystem) + Auto-Registration (no PR friction) generates the agent volume. If the hypothesis holds within 90 days, the deferred Registry API Backend returns as a v2.3.x or v2.4.x patch release.

## Deferred (will return only when triggers fire)

- Registry API Backend (PostgreSQL) — gated by 500+ agents OR IssueOps becoming the bottleneck
- Intent-Based Directory Search — gated by Registry API Backend
- Orchestration Primitives — gated by 10+ users requesting multi-agent flows
- Delegated/Autonomous Mode formalization — gated by capability escalation usage data
- Capability-Aware Introspection (RFC 7662) — moved to v2.4 Spec & Interop
- Privacy Considerations spec — moved to v2.4 Spec & Interop
- DeepEval Intelligence Layer — gated by 3+ requests
