# PRD: ASAP Protocol v2.5.4 — Distribution Loop

> **Product Requirements Document**
>
> **Version**: 2.5.4
> **Status**: ✅ **SHIPPED** (2026-07-18) — tag [`v2.5.4`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.4); PyPI `asap-protocol==2.5.4`; PR [#294](https://github.com/adriannoes/asap-protocol/pull/294)
> **Created**: 2026-04-28 (as v2.3.3); **renumbered**: 2026-06-22 → v2.5.2; **2026-07-08 → v2.5.4**
> **Last Updated**: 2026-07-18
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.3-adapter-lab-ii.md](./prd-v2.5.3-adapter-lab-ii.md)
> **Successor**: [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md)
> **Tasks**: [engineering/tasks/v2.5.4/](../../engineering/tasks/v2.5.4/tasks-v2.5.4-roadmap.md)
>
> **Migration note**: Formerly `product/prd/private/prd-v2.3.3-distribution-loop.md` (v2.3.3), then `prd-v2.5.2-distribution-loop.md`. v2.5.2 was reassigned to the security follow-up patch (2026-07-08).

---

## 1. Purpose

v2.5.4 turns adoption work from v2.3.0–v2.5.3 into a **repeatable distribution loop**: homepage, docs routing, thin starter templates, and lightweight metrics so developers discover ASAP through executable paths.

---

## 2. Scope

| Area | Requirement |
|------|-------------|
| Homepage | Hero, feature cards, "what's new", CTA for agent-first software |
| Docs routing | Every homepage CTA → GitHub docs, starters, or runnable examples |
| Templates | Thin starters: OpenAPI provider, TypeScript consumer, MCP Auth Bridge |
| Metrics | Site→docs clicks, npm/PyPI installs, registered agents, guide-view proxies |
| Narrative | Public "Build for agents" copy (no private GTM) |

---

## 3. Locked decisions (D1–D5)

| ID | Decision | Locked value |
|----|----------|--------------|
| **D1** | Homepage narrative hierarchy | **"Build for agents" is primary**; marketplace remains proof/distribution (secondary CTAs to browse/register) |
| **D2** | Canonical starters (exactly 3) | OpenAPI provider · TypeScript consumer · MCP Auth Bridge |
| **D3** | Starter shape | **Thin wrappers** under `examples/starters/` derived from existing examples/apps; not a new scaffold CLI |
| **D4** | Metrics DoD (DIST-004) | **Operationalize** existing `scripts/telemetry/` + maintainer dashboard markdown; **no** public live dashboard UI |
| **D5** | Release shape | Versioned train: tag **`v2.5.4`**, bump Python package, `CHANGELOG.md`, migration note |

### 3.1 Canonical starter destinations

| Starter | Delivery path | Source (do not reinvent) |
|---------|---------------|--------------------------|
| OpenAPI provider | `examples/starters/openapi-provider/` | `examples/openapi_petstore/` + `docs/adapters/openapi.md` |
| TypeScript consumer | `examples/starters/typescript-consumer/` | `apps/example-nextjs/` (consumer patterns) + `packages/typescript/client` + `docs/sdks/typescript.md` |
| MCP Auth Bridge | `examples/starters/mcp-auth-bridge/` | `examples/mcp_auth_bridge/` + `docs/adapters/mcp-auth-bridge.md` |

Thin starter = README with ≤1 smoke command + minimal entrypoint (prefer wrap/re-export of parent example over duplicated logic).

### 3.2 Metric proxies (accepted)

| PRD metric | Accepted proxy / source |
|------------|-------------------------|
| Site→docs clicks | `data-cta` + Vercel Analytics + `/api/telemetry`; optional `TELEMETRY_SITE_METRICS_JSON` |
| npm installs | `scripts/telemetry/collect_npm.py` (≥ `@asap-protocol/client`, `@asap-protocol/mastra`, `@asap-protocol/openai-agents`) |
| PyPI installs | `scripts/telemetry/collect_pypi.py` / aggregate (≥ `asap-protocol`, `asap-compliance`) |
| Registered agents | `scripts/telemetry/collect_registry.py` → `registry.json` |
| Guide views | GitHub traffic/referrers via `collect_github.py` + site→docs CTR; **not** a new MkDocs analytics plugin |

---

## 4. Baseline inventory (do not rebuild)

Lab II and prior trains already shipped much of the distribution surface. v2.5.4 **extends** this; it does not replace it.

| Area | Already present | Gap for this PRD |
|------|-----------------|------------------|
| Homepage shell | `apps/web/src/app/page.tsx` — Hero, WhatsNew, Features, HowItWorks | Hero still marketplace-primary; narrative D1 not applied |
| CTA instrumentation | `apps/web/src/lib/telemetry/homepage-cta-ids.ts`, `CtaClickTracker` | Hero CTAs still point to browse/register; incomplete docs routing on some feature/DX cards |
| Examples | `examples/openapi_petstore/`, `examples/mcp_auth_bridge/`, `examples/workflow_asap_connector/`, … | No `examples/starters/` pack |
| TS consumer app | `apps/example-nextjs/` | Not packaged as a thin starter |
| Telemetry | `scripts/telemetry/*`, `docs/maintainers/telemetry.md`, `.github/workflows/telemetry-weekly.yml`, `/api/telemetry` | Package coverage incomplete; schedule may need secrets; no public UI (by design) |
| Public guide | Tutorials / adapters / integrations under `docs/` | No `docs/guides/build-for-agents.md` |

---

## 5. Requirements

| ID | Requirement | Priority | Artifact | Acceptance (falsifiable) |
|----|-------------|----------|----------|--------------------------|
| **DIST-001** | Update `apps/web` homepage for agent-first software story | MUST | Hero, metadata, How it Works, What's new, feature framing | Primary hero copy matches §6; marketplace CTAs secondary; version badge/terminal not stale |
| **DIST-002** | Link homepage sections to concrete GitHub docs/starters/examples | MUST | Landing CTAs + feature/DX docs links | Every primary homepage CTA resolves to a live docs/starter/example URL; `data-cta` IDs remain stable |
| **DIST-003** | Starter templates for strongest adoption paths | MUST | `examples/starters/{openapi-provider,typescript-consumer,mcp-auth-bridge}/` | Exactly the D2 trio; each has README + headless smoke ≤60s |
| **DIST-004** | Lightweight adoption metrics (operational) | SHOULD | Collectors + `private/telemetry/dashboard.md` + runbook + CI dispatch | Aggregate covers npm≥3 + PyPI≥2 packages; runbook documents weekly ops; **no** new `apps/web` metrics UI |
| **DIST-005** | Public "Build for agents" guide | MUST | `docs/guides/build-for-agents.md` + `mkdocs.yml` | Guide published; linked from starters index (+ docs/index); homepage primary CTA link lands with S3 CTA routing (DIST-001/002) |
| **DIST-006** | Keep pricing, paid timing, fundraising private | MUST | Public copy gate | Grep/review of homepage + new guide + starter READMEs finds no private GTM/pricing/fundraising |

### 5.1 Dependencies

| Requirement | Depends on |
|-------------|------------|
| DIST-001 / DIST-002 | DIST-005 paths known; DIST-003 starter URLs preferred for primary CTAs |
| DIST-003 | D2/D3; parent examples remain canonical |
| DIST-004 | Existing telemetry stack; secrets for scheduled CI optional until configured |
| DIST-005 | D1 narrative; links to D2 starters |
| DIST-006 | Continuous on every PR that touches public copy |

---

## 6. Public narrative (canonical)

> The next users of software are agents. ASAP gives them the machine-readable foundation they need: discoverable capabilities, scoped identity, compliance checks, and SDKs that turn existing APIs into agent-ready interfaces.

**Homepage hierarchy (D1):** lead with this story and CTAs into the guide + starters; keep Explore Agents / Register Agent as secondary proof of the open marketplace.

---

## 7. Success metrics

| Metric | Target |
|--------|--------|
| Homepage primary CTAs → docs/starters/examples | Present, live, and trackable via `data-cta` |
| Starter templates | Exactly **3** at the D2 paths (thin wrappers) |
| Adoption metrics | Documented + runnable aggregate (≥1 maintainer run or CI `workflow_dispatch`); dashboard markdown under `private/telemetry/` (gitignored) |
| Release | Tag `v2.5.4` + PyPI `asap-protocol==2.5.4` |

---

## 8. Definition of Done

- [x] DIST-001 … DIST-003, DIST-005, DIST-006 green
- [x] DIST-004 green **or** explicit maintainer deferral recorded on the roadmap (SHOULD) — satisfied; secrets gap documented
- [x] [docs-review-checklist](../../engineering/tasks/v2.5.4/docs-review-checklist.md) signed for shipped surface
- [x] [release-checklist](../../engineering/tasks/v2.5.4/release-checklist.md) §§1–6 complete (merge → tag → publish → handoff)
- [x] Public copy free of private GTM / pricing / fundraising

---

## 9. Out of scope (defer)

| Item | Where / note |
|------|----------------|
| Full Design System Revamp | Separate design track; copy/routing only here |
| Scaffold generator / `create-asap` CLI | Post–v2.5.4 if demanded |
| Public live metrics dashboard UI | Explicitly out (D4) |
| New MkDocs analytics plugin | Out; use GitHub + site CTR proxies |
| `@asap-protocol/mcp-auth` npm package | [v2.5.0 backlog](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md) |
| Pricing, paid timing, fundraising, private GTM | Local `product/strategy/` only |
| Formal Spec / A2A bridge | [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md) |
| Fourth starter (workflow connector) | Optional follow-up; Lab II example already public |

---

## 10. Sprint mapping (tasks)

| Sprint | Focus | PRD |
|--------|-------|-----|
| S0 | Scope lock (confirm D1–D5 + baseline) | §3–§4 |
| S1 | Thin starter pack | DIST-003 |
| S2 | Build for agents guide | DIST-005 |
| S3 | Homepage narrative + CTA routing | DIST-001, DIST-002, DIST-005 (homepage link), DIST-006 |
| S4 | Telemetry operations | DIST-004 |
| S5 | Release v2.5.4 | DoD / D5 |

See [tasks-v2.5.4-roadmap.md](../../engineering/tasks/v2.5.4/tasks-v2.5.4-roadmap.md).

---

## 11. Handoff inputs for v2.5.5 (Formal Spec)

> **Confirmed at S5 ship (2026-07-18).** Dist Loop is a **soft** input to Formal Spec (narrative + examples), not a hard implementation gate.

| Input | Locked path / value | Spec use |
|-------|---------------------|----------|
| Canonical narrative (D1) | §6 paragraph + homepage hierarchy | Tone for SPEC examples; ASAP ≠ replace MCP |
| Guide | `docs/guides/build-for-agents.md` | Public onboarding cited from Spec / COMPAT guide |
| OpenAPI starter | `examples/starters/openapi-provider/` | Provider onboarding examples |
| TypeScript starter | `examples/starters/typescript-consumer/` | Consumer / SDK examples |
| MCP Auth starter | `examples/starters/mcp-auth-bridge/` | SPEC-009 narrative + COMPAT |
| Metric proxies (optional) | `docs/maintainers/telemetry.md` + DIST-004 | Adoption evidence only; not Spec MUST |
| OOS inherited (do not pull into Spec as Dist debt) | `create-asap` CLI, public metrics UI, Design System Revamp, fourth workflow starter, pricing/GTM | Stay deferred |
| Still backlog (not Dist, not Spec MUST) | `@asap-protocol/mcp-auth` npm — [v2.5.0 backlog](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md) | npm patch TBD |
| TSOA `@asap-protocol/openapi` | Conditional P3 on [prd-v2.5.5](./prd-v2.5.5-formal-spec-interop.md) §3.5 | Defer unless demand at Spec kickoff |

**Successor PRD:** [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md)
**Economy (later):** [prd-v3.0-economy.md](./prd-v3.0-economy.md) — Dist metrics are candidate proxies for launch triggers; no pricing copy in Dist.

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-18 | **SHIPPED** — tag `v2.5.4`; PyPI 2.5.4; DoD + §11 handoff confirmed; train CLOSED |
| 2026-07-18 | Status → **IN PROGRESS**; DIST-005 acceptance clarifies homepage link lands with S3 CTA routing |
| 2026-07-18 | §11 handoff inputs for v2.5.5; train cross-links tightened before kickoff |
| 2026-07-18 | **Decisions locked** (D1–D5); baseline inventory; falsifiable DIST criteria; out of scope; sprint mapping; status remains READY FOR KICKOFF |
| 2026-07-16 | Status → **READY FOR KICKOFF** (v2.5.3 shipped) |
| 2026-07-08 | Renumbered v2.5.2 → **v2.5.4** (v2.5.2 = security follow-up) |
| 2026-06-22 | Renumbered v2.3.3 → v2.5.2 |
