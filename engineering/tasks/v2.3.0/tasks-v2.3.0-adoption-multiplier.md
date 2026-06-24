# Tasks: v2.3.0 Adoption Multiplier — Sprint Index

**Status: 🟢 SHIPPED (code & docs 2026-05-04)** — PyPI `asap-protocol==2.3.0`, npm `@asap-protocol/client@2.3.0` (**live 2026-05-13**; maintainer runbook [docs/maintainers/npm-publishing.md](../../../docs/maintainers/npm-publishing.md)), tag, Docker, and GitHub Release: see [release-checklist.md](./release-checklist.md) for remaining verify steps.

Based on [PRD v2.3 Adoption Multiplier](../../../product/prd/prd-v2.3-scale.md). Each sprint maps to a PR sequence.

## Prerequisites
- [x] v2.2.0 Protocol Hardening released (2026-04-15)
- [x] v2.2.1 carry-over patch released (2026-04-21) — See [tasks-v2.2.1-patch.md](../v2.2.1/tasks-v2.2.1-patch.md)
- [x] Capability model stable (v2.2)
- [x] Identity model stable (v2.2)
- [x] Streaming/SSE operational (v2.2)
- [x] Compliance Harness v2 operational (v2.2)

## Sprint Plan

| Sprint | Focus | PRD Sections | Priority | Status |
|--------|-------|--------------|----------|--------|
| **S1** | [OpenAPI Adapter (Python)](./sprint-S1-openapi-adapter.md) | §4.1 (OA-001..011) | P0 | 🟢 **Done (repo)** — PyPI with `2.3.0` via **S5** |
| **S2** | [TypeScript Client SDK](./sprint-S2-typescript-sdk.md) | §4.2 (TS-001..011) | P0 | 🟢 **Done (repo)** — npm `@asap-protocol/client@2.3.0` via **S5** |
| **S3** | [Auto-Registration](./sprint-S3-auto-registration.md) | §4.3 (AUTO-001..007) | P0 | 🟢 **Done (repo)** |
| **S4** | [Capability Escalation + ASAP Challenge](./sprint-S4-escalation-challenge.md) | §4.4 (ESC-001..004), §4.5 (CHAL-001..004) | P1/P2 | 🟢 **Done (repo)** |
| **S5** | Release v2.3.0 | — | — | 🟡 **In progress** — [release-checklist.md](./release-checklist.md): npm **shipped** + runbook linked (§4.3); Docker pull verify / PyPI venv verify / housekeeping |

## Dependency Graph

```
S1 (OpenAPI Adapter ─ Python) ──► S4 (Escalation + Challenge) ──► S5 (Release)
                                              ▲
S2 (TypeScript SDK) ──────────────────────────┤
                                              │
S3 (Auto-Registration) ───────────────────────┘
```

S1, S2, and S3 are independent and can run in parallel with three contributors. S4 depends on S1 (escalation flow used by OpenAPI-derived agents) and on S2 (escalation client method needed in TS SDK). S5 depends on S1–S4.

## Definition of Done (v2.3.0)

- [x] **OpenAPI Adapter (repo)**: `asap.adapters.openapi` implemented (`create_from_openapi`, PetStore example `examples/openapi_petstore/`, docs `docs/adapters/openapi.md`) — see [sprint-S1-openapi-adapter.md](./sprint-S1-openapi-adapter.md). *Acceptance: sprint checklist complete; release packaging tracked separately.*
- [ ] **OpenAPI Adapter (release)**: `asap-protocol==2.3.0` on **PyPI** includes the `[openapi]` extra and adapter surface (closes when S5 ships)
- [x] **TypeScript SDK**: `@asap-protocol/client@2.3.0` published to npm with Vercel AI / OpenAI / Anthropic adapters — [npm](https://www.npmjs.com/package/@asap-protocol/client) (2026-05-13)
- [x] **Auto-Registration (repo)**: `POST /registry/agents` + bot PR / merge workflows — see [sprint-S3-auto-registration.md](./sprint-S3-auto-registration.md). *Production registry-bot deployment is operator-specific.*
- [x] **Capability Escalation (repo)**: `POST /asap/agent/request-capability` + client helpers — see [sprint-S4-escalation-challenge.md](./sprint-S4-escalation-challenge.md).
- [x] **ASAP Challenge (repo)**: `WWW-Authenticate: ASAP` middleware + client recognition — see [sprint-S4-escalation-challenge.md](./sprint-S4-escalation-challenge.md).
- [ ] Test coverage ≥90% for new modules (Python and TS) — **OpenAPI adapter** (`src/asap/adapters/openapi/`) remains **~87%** per [sprint-S1-openapi-adapter.md](./sprint-S1-openapi-adapter.md); **narrow `--cov=asap.transport.escalation_routes`** still unsuitable for JWT-heavy suites (see S4 sprint note). Treat as **release debt** or raise coverage in a follow-up PR.
- [x] `uv run mypy src/ scripts/ tests/` — **2026-05-04** (396 files, exit 0).
- [x] `uv run ruff check .` — **2026-05-04** (exit 0).
- [x] TS SDK passes `pnpm test`, `pnpm lint`, `pnpm typecheck` (from repo root: `pnpm test` / `pnpm lint` / `pnpm typecheck` — **2026-05-04**).
- [x] E2E test: spec URL → onboarded agent → invocable capability — **covered in-repo** (OpenAPI PetStore + registry tests; see sprint S1/S3 files).
- [x] `apps/web` landing page, feature cards, and docs links updated for v2.3.0.
- [x] Public docs (`docs/index.md`, migration, adapter/TS guides) route users to OpenAPI, TypeScript SDK, and registry flows.
- [x] CHANGELOG.md updated under `## [2.3.0]`
- [ ] `asap-protocol==2.3.0` published to PyPI *(full package; confirms **OpenAPI Adapter (release)** above)*
- [x] `@asap-protocol/client@2.3.0` published to npm
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

The 500-agent trigger (original v2.3 Registry API gate) is treated as an **outcome metric**, not a prerequisite. The hypothesis: OpenAPI Adapter (zero-code) + TypeScript SDK (dominant AI ecosystem) + Auto-Registration (no PR friction) generates the agent volume. If the hypothesis holds within 90 days, the deferred Registry API Backend returns as a v2.5.x or v3.x patch release.

## Deferred (will return only when triggers fire)

- Registry API Backend (PostgreSQL) — gated by 500+ agents OR IssueOps becoming the bottleneck
- Intent-Based Directory Search — gated by Registry API Backend
- Orchestration Primitives — gated by 10+ users requesting multi-agent flows
- Delegated/Autonomous Mode formalization — gated by capability escalation usage data
- Capability-Aware Introspection (RFC 7662) — moved to v2.5.3 Formal Spec & Interop
- Privacy Considerations spec — moved to v2.5.3 Formal Spec & Interop
- DeepEval Intelligence Layer — gated by 3+ requests
