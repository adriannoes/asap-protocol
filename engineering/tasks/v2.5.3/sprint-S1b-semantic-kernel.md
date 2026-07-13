# Sprint S1b: Semantic Kernel / Microsoft Agent Framework (conditional)

**PRD**: D2, §6 promotion gates  
**Branch**: `feat/v2.5.3-s1b-s1c-spikes` → **`release/2.5.3`**  
**Depends on**: [S0](./sprint-S0-candidate-lock.md); [demand-sheet.md](./demand-sheet.md) **maintainer override (2026-07-13)**  
**Research**: [research-semantic-kernel.md](./research-semantic-kernel.md)

**Trigger:** S0 recorded D2 **no-go** on demand; maintainer override reopened S1b for a research/experimental guide (combined S1b+S1c initiative).  
**Enables:** Optional second public surface; never blocks S4.  
**Depends on:** Demand-sheet override + 2b.1 scope lock.

---

## Goal

Produce an **interop spike + .NET-oriented guide** showing how ASAP identity/capabilities sit beside Microsoft Agent Framework / Semantic Kernel. Prefer guide + thin sample over a full .NET SDK in this release.

If the spike exceeds ~1 week or needs protocol changes: stop, publish research notes, mark **not maintained**.

### 2b.1 decision (2026-07-13)

See [research-semantic-kernel.md](./research-semantic-kernel.md).

- **Target API surface:** **Microsoft Agent Framework (MAF)** is the primary public naming (GA 1.0, April 2026). Semantic Kernel is maintenance/legacy — mention for migration readers only.
- **Deliverable:** **guide-only** → `docs/integrations/microsoft-agent-framework.md` (research/experimental). No C# sample under `examples/` in this release (no in-repo .NET CI / maintainer path).

---

## Tasks

- [x] **2b.1 Scope check**
  - [x] Confirm target API surface (SK vs Agent Framework naming as of spike date)
  - [x] Decide: guide-only vs guide + minimal C# sample repo path under `examples/`

- [x] **2b.2 Guide**
  - [x] `docs/integrations/microsoft-agent-framework.md` (SK called out as legacy / migration)
  - [x] Map: Agent JWT / capabilities ↔ how tools are registered on the MS side
  - [x] Explicit status banner: **research / experimental** vs **maintained**
  - [x] Leave MkDocs nav + home index to **S3**

- [x] **2b.3 Optional sample** — **skipped / N/A (guide-only)**
  - [x] No C# sample under `examples/` (2b.1 deliverable = guide-only; no in-repo .NET CI)
  - [x] Do not block release on NuGet publish

---

## Acceptance criteria

- [x] Guide exists at `docs/integrations/microsoft-agent-framework.md` (nav/index deferred to S3; 2b.3 N/A — guide-only)
- [x] No protocol fork
- [x] Status (research vs maintained) is obvious in the first screen of the doc

## Relevant files

| Path | Role |
|------|------|
| [`docs/integrations/microsoft-agent-framework.md`](../../../docs/integrations/microsoft-agent-framework.md) | Public interop guide (2b.2) |
| [`research-semantic-kernel.md`](./research-semantic-kernel.md) | 2b.1 naming + deliverable lock |

## Skip condition

If S0 records **no-go** *and* there is no maintainer override, mark this sprint **SKIPPED** in the roadmap table and do not open a branch. *(Override applied 2026-07-13 — sprint **Done** guide-only; 2b.3 skipped.)*

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-13 | T3 | Approved with caveats | [review-v2.5.3-S1b-S1c-spikes-20260713.md](../../code-review/private/review-v2.5.3-S1b-S1c-spikes-20260713.md) |
