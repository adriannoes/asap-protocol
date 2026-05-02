# Documentation Checkpoints

> **Purpose**: Formal review points to update documentation with learnings (product follow-up after releases).
> **Location**: Lives under **`product/`** because it drives PRD updates and retros, not day-to-day engineering execution.
> **Created**: 2026-02-06
> **Updated**: 2026-05-02 — Status roll-up verified against Git + `pyproject.toml`; CP-1–CP-6 archive checklists marked `[x]`.

---

## Status roll-up (verified in-repo)

Use this section first; the checkpoint sections below add detail or archive.

**Evidence snapshot** (refresh with `git log` and [`pyproject.toml`](../pyproject.toml)):
- **`pyproject.toml`** sets **`version = "2.2.1"`** — local packaging is **not** at **2.3.0** yet; **S5** (bump + PyPI/npm) remains open.
- **S1 OpenAPI adapter**: first package commit **`cedb3f9`** — `2026-05-01` 19:16 -0300 (`feat(openapi): add OpenAPI 3.x adapter package`). Merge to `main`: **`04c56be`** — `2026-05-02` 01:03 -0300 (`feat(openapi): OpenAPI 3.x adapter (#132)`). Review notes: [`engineering/code-review/v2.3.0/pr-132-openapi-adapter.md`](../engineering/code-review/v2.3.0/pr-132-openapi-adapter.md) (**2026-05-01**).

| Track | Done (shipped / decided) | Still open (ahead) |
|-------|--------------------------|-------------------|
| **v1.1.0 → v1.4.0** | Releases on the v1.x train shipped per PRDs; Lean Marketplace pivot absorbed into planning (2026-02). CP-1–CP-4 checklists below marked **`[x]`** (milestone closed). | Standalone retros (`v1.1.0-retro` …) may still be missing on disk — only [`v1.0.0-retro.md`](../engineering/lessons-learned/v1.0.0-retro.md) exists **today**; add files if you want them archived. |
| **v2.0.0** | Web app + marketplace usage foundation delivered (M1–M4 era per task docs); protocol moved on through v2.1+. | CP-5/CP-6 “two weeks after launch” metrics + `vision-v2.1.md`-style follow-ups were **not** finalized here; treat as **optional** unless you revisit launch analytics. |
| **v2.1.x / v2.2.x / v2.2.1** | **Released** per [tasks-v2.3.0-adoption-multiplier.md](../engineering/tasks/v2.3.0/tasks-v2.3.0-adoption-multiplier.md) prerequisites (v2.2.0 **2026-04-15**, v2.2.1 **2026-04-21**). No dedicated checkpoint section existed in this doc — learnings live in PRDs, ADRs, and [`engineering/code-review/`](../engineering/code-review/). | Optional: one consolidated retro doc if you want a single narrative for the v2.2 cycle. |
| **v2.3.0 Adoption Multiplier** | **S1** merged (**#132**, commit `04c56be`). Code, docs, and PR-132 review in repo. | **S2–S5**, **`version`** bump to **2.3.0**, PyPI/npm/Docker per [tasks-v2.3.0-adoption-multiplier.md](../engineering/tasks/v2.3.0/tasks-v2.3.0-adoption-multiplier.md). |
| **After v2.3.0** | — | **CP-7** below: doc refresh, PRD / patch-train updates, adoption metrics. |

**Sources of truth for current execution**: [tasks-v2.3.0-adoption-multiplier.md](../engineering/tasks/v2.3.0/tasks-v2.3.0-adoption-multiplier.md), [prd-v2.3-scale.md](./prd/prd-v2.3-scale.md), [AGENTS.md](../AGENTS.md).

---

## Why Checkpoints?

As a solo developer, it's easy to lose context between sprints. These checkpoints ensure:
1. **Lessons captured**: What worked, what didn't
2. **Docs updated**: Next version PRDs refined with learnings  
3. **Estimates adjusted**: Realistic planning based on actual velocity
4. **Context preserved**: Knowledge carries forward across releases (v2.3.x adoption train and beyond)

---

## Checkpoint Schedule

### CP-1 — CP-6 (v1.1.0 through v2.0.0 M4)

These checkpoints were defined during the v1.x / v2.0 marketplace push. **All associated releases have shipped** on the project timeline. Checklist items below are marked **`[x]`** to record that the milestone is **closed** (work absorbed by subsequent releases, ADRs, and PRDs; some optional retros were never written as separate files).

<details>
<summary><strong>CP-1: Post v1.1.0 Release</strong> (archive)</summary>

**When**: After v1.1.0 ships (release preparation done 2026-02-10; publish in Task 4.7).

Pre-release: Release materials (CHANGELOG, README, AGENTS.md, secure_agent example) completed. Full review and velocity update to be done after v1.1.0 ships.

**Review**:
- [x] OAuth2 implementation complexity — update v1.2 estimates?
- [x] WebSocket lessons learned
- [x] Discovery patterns that worked
- [x] State Storage Interface (SD-9): Did SQLite impl meet needs? Is `MeteringStore` interface sufficient for v1.3?
- [x] Agent Liveness (SD-10): Is the health endpoint effective? Is `ttl_seconds` default (300s) appropriate?
- [x] `SnapshotStore` sync vs async: Should we evolve to async Protocol? (Breaking change analysis)
- [x] Lite Registry (SD-11, ADR-15): Is GitHub Pages adequate? Is the multi-endpoint schema flexible enough?
- [x] WebSocket MessageAck (ADR-16): Is `AckAwareClient` timeout (30s default) appropriate? Retransmission working correctly?
- [x] Custom Claims binding (ADR-17): Are Custom Claims practical with all IdPs? Is the allowlist fallback needed often?
- [x] Best Practices Failover doc: Is the `StateQuery`/`StateRestore` pattern sufficient without formal `TaskHandover` payload?
- [x] Time taken vs estimated

**Update**:
- [x] `prd-v1.2-roadmap.md` — refine based on auth + storage learnings
- [x] `prd-v1.3-roadmap.md` — confirm `MeteringStore` interface meets v1.3 needs
- [x] `tasks-v1.2.0-roadmap.md` — adjust estimates (now 4 sprints / 13 tasks post-Lean pivot)
- [x] `lessons-learned/v1.1.0-retro.md` — create retrospective

</details>

<details>
<summary><strong>CP-2: Post v1.2.0 Release</strong> (archive)</summary>

**When**: After v1.2.0 ships

**Review**:
- [x] Ed25519 PKI complexity
- [x] Compliance harness effectiveness — is it usable by third parties?
- [x] Lite Registry (SD-11): Is GitHub Pages still sufficient? Should Registry API Backend be accelerated for v2.0?
- [x] Time taken vs estimated

**Update**:
- [x] `prd-v1.3-roadmap.md` — refine observability based on PKI learnings
- [x] `tasks-v1.3.0-roadmap.md` — adjust estimates (now 3 sprints / 13 tasks post-Lean pivot)
- [x] `lessons-learned/v1.2.0-retro.md` — create retrospective

> [!NOTE]
> Registry API review item removed (deferred to v2.1). Compliance harness is now the primary deliverable to evaluate.

</details>

<details>
<summary><strong>CP-3: Post v1.3.0 Release</strong> (archive)</summary>

**When**: After v1.3.0 ships

**Status**: v1.3.0 released (2026-02-18). Tag v1.3.0 pushed; Sprints E1–E3 done (Metering, Delegation, SLA Framework). Checkpoint review ready.

**Review**:
- [x] Observability metering implementation lessons
- [x] Delegation token complexity
- [x] SLA framework effectiveness
- [x] Lite Registry capacity — can it handle target 100+ agents for v2.0?

**Update**:
- [x] `prd-v2.0-roadmap.md` — major update with all v1.x learnings
- [x] `tasks-v2.0.0-roadmap.md` — realistic estimates (now 4 sprints / 20 tasks post-Lean pivot)
- [x] `lessons-learned/v1.3.0-retro.md` — create retrospective
- [x] Web App tech stack decisions (Next.js + Lite Registry)
- [x] `v2.0-marketplace-usage-foundation.md` — refine with E1/E2/E3 implementation learnings

</details>

<details>
<summary><strong>CP-4: Post v1.4.0 Release</strong> (archive)</summary>

**When**: After v1.4.0 ships

**Review**:
- [x] Type safety impact (mypy checks, runtime stability)
- [x] Memory usage with paginated queries (SLA history)
- [x] Developer experience with stricter types

**Update**:
- [x] `prd-v2.0-roadmap.md` — confirm "Hardening" sprint met v2.0 scale needs
- [x] `tasks-v2.0.0-roadmap.md` — adjust final v2.0 estimate

</details>

<details>
<summary><strong>CP-5: Post v2.0.0 M3 (Developer Experience)</strong> (archive)</summary>

**When**: After completing sprints M1–M3

**Status**: M3 complete (2026-02-21). IssueOps registration + verification flows implemented. Ready for M4 launch prep.

**Review**:
- [x] Lite Registry data layer — is `registry.json` SSG/ISR working well?
- [x] Web App performance with static registry data
- [x] Client-side search/filter UX
- [x] IssueOps flow — Web Form → GitHub Issue → Action: friction level acceptable?
- [x] Verification request flow — form → pre-filled Issue: working as expected?
- [x] NextAuth scope downgrade (`read:user` only) — any missing permissions?

**Update**:
- [x] `sprint-M4-launch-prep.md` — adjust estimates based on M3 velocity
- [x] Evaluate if Registry API Backend should be built for v2.1

**Reference**: [sprint-M3-developer-experience.md](../engineering/tasks/v2.0.0/sprint-M3-developer-experience.md)

</details>

<details>
<summary><strong>CP-6: Post v2.0.0 M4 (Launch)</strong> (archive)</summary>

**When**: 2 weeks after launch

**Review**:
- [x] Launch success metrics (per PRD: 100+ agents, 500+ weekly visits)
- [x] User feedback
- [x] What to do next (v2.1 Registry API Backend? v2.2 DeepEval?)

**Create**:
- [x] `lessons-learned/v2.0.0-retro.md` — comprehensive retrospective
- [x] `vision-v2.1.md` — Registry API Backend + deferred features roadmap

</details>

---

### CP-7: Post v2.3.x Adoption train (documentation & learning)

**When**: After **v2.3.0** ships (S5 complete), or mid-flight if you run a **beta** period before tagging.

**Why**: v2.3.0 rescoped to adoption (OpenAPI, TS SDK, auto-registration, escalation/challenge). This checkpoint captures whether docs and PRDs reflect reality—not registry scale gates.

**Review** (pick what applies once artifacts exist):
- [ ] OpenAPI adapter: DX for Python + framework authors; PetStore / examples sufficient?
- [ ] TypeScript SDK: provider adapters (Vercel AI / OpenAI / Anthropic) — gaps vs npm consumers?
- [ ] Auto-registration: IssueOps vs `POST /registry/agents` — friction, abuse, harness integration?
- [ ] Escalation + `WWW-Authenticate` challenge path — observability and support burden?
- [ ] Coverage / quality bar met for new modules (Python + TS) per Definition of Done?
- [ ] Time taken vs estimated (S1–S5); parallelism assumptions validated?

**Update**:
- [ ] `prd-v2.3-scale.md` — ship checklist vs actual scope; note deferred v2.3.1–v2.3.3 tracks
- [ ] `CHANGELOG.md` + public docs — homepage / apps/web announcement aligned with shipped surface?
- [ ] Optional: `engineering/lessons-learned/v2.3.0-retro.md` — short retrospective (hypothesis: adoption flywheel vs 500-agent trigger)
- [ ] Feed learnings into [prd-v2.4-adoption.md](./prd/prd-v2.4-adoption.md) or patch PRDs as needed

**Reference**: [tasks-v2.3.0-adoption-multiplier.md](../engineering/tasks/v2.3.0/tasks-v2.3.0-adoption-multiplier.md)

---

## Checkpoint Process

For each checkpoint:

1. **Take 30-60 minutes** to review honestly
2. **Update documents** while context is fresh
3. **Adjust estimates** based on actual velocity  
4. **Capture patterns** that can be reused
5. **Commit changes** with descriptive message

---

## Velocity Tracking

Track actual vs estimated to improve future planning:

| Version | Estimated Days | Actual Days | Velocity |
|---------|----------------|-------------|----------|
| v1.1.0 | 31-41 | — | — |
| v1.2.0 | 18-26 | — | — |
| v1.3.0 | 15-22 | ~12 | On track (2026-02 note) |
| v1.4.0 | 5-8 | — | — |
| v2.0.0 | 23-33 | — | — |
| v2.1.x | — | — | — |
| v2.2.x / v2.2.1 | — | — | Shipped 2026-04-15 / 2026-04-21 |

> [!NOTE]
> Estimates updated after Lean Marketplace pivot: v1.2 reduced (6→4 sprints), v1.3 reduced (4→3 sprints), v2.0 reduced (6→4 sprints). Fill **Actual** when you reconcile from sprint notes.

---

## Related Documents

- [PRD v2.0 — Marketplace roadmap](./prd/prd-v2.0-roadmap.md)
- [PRD v2.3 — Adoption multiplier](./prd/prd-v2.3-scale.md)
- [Product strategy ADRs (deferrals & pivots)](./decision-records/05-product-strategy.md)
- [v2.0-marketplace-usage-foundation.md](../engineering/tasks/v2.0.0/v2.0-marketplace-usage-foundation.md) — Usage storage & control for v2.0
- [lessons-learned/](../engineering/lessons-learned/)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-02-06 | Initial checkpoints document |
| 2026-02-12 | **Lean Marketplace pivot**: Updated CP-2 (removed Registry API review), CP-3 (metering→observability), CP-4 (renamed from "Marketplace Core" to "Web App Features"), CP-5 (merged with CP-6, updated metrics). Reduced from 6 checkpoints to 5. Updated velocity estimates. |
| 2026-02-18 | **v1.3.0 release prep**: CP-3 status updated (Sprints E1–E3 complete, PR #50 open). Velocity: v1.3.0 ~12 days actual vs 15–22 estimated. |
| 2026-02-18 | **v1.3.0 released**: Tag v1.3.0 pushed. CP-3 checkpoint review ready. |
| 2026-02-21 | **Sprint M3 complete**: CP-5 updated for M1–M3 (IssueOps, verification flow). Launch prep next. |
| 2026-04-28 | **Relocated** from `engineering/checkpoints.md` to `product/checkpoints.md` as product-level documentation follow-up (links updated). |
| 2026-04-28 | **Status roll-up**: Table for shipped vs ahead; CP-1–CP-6 folded under `<details>` as archive; **CP-7** added for v2.3.x adoption; honesty note on missing retros; velocity rows for v2.2.x. |
| 2026-05-02 | **Repo-verified evidence**: `pyproject.toml` still **2.2.1**; S1 merge **`04c56be`** (2026-05-02 01:03 -0300), first adapter commit **`cedb3f9`** (2026-05-01); linked PR-132 review date. |
| 2026-05-02 | **Archive checklists**: All CP-1–CP-6 items set to **`[x]`** (milestone closed); CP-7 remains **`[ ]`** until post–v2.3.0 review. |
