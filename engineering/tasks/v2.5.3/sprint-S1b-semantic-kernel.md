# Sprint S1b: Semantic Kernel / Microsoft Agent Framework (conditional)

**PRD**: D2, §6 promotion gates  
**Branch**: `feat/v2.5.3-s1b-semantic-kernel` → **`release/2.5.3`**  
**Depends on**: [S0](./sprint-S0-candidate-lock.md) **D2 = go**

**Trigger:** Azure/.NET demand gate passed in S0.  
**Enables:** Optional second public surface; never blocks S4.  
**Depends on:** S0 go decision.

---

## Goal

Produce an **interop spike + .NET-oriented guide** showing how ASAP identity/capabilities sit beside Microsoft Agent Framework / Semantic Kernel. Prefer guide + thin sample over a full .NET SDK in this release.

If the spike exceeds ~1 week or needs protocol changes: stop, publish research notes, mark **not maintained**.

---

## Tasks

- [ ] **2b.1 Scope check**
  - [ ] Confirm target API surface (SK vs Agent Framework naming as of spike date)
  - [ ] Decide: guide-only vs guide + minimal C# sample repo path under `examples/`

- [ ] **2b.2 Guide**
  - [ ] `docs/integrations/semantic-kernel.md` (or `microsoft-agent-framework.md`)
  - [ ] Map: Agent JWT / capabilities ↔ how tools are registered on the MS side
  - [ ] Explicit status banner: **research / experimental** vs **maintained**
  - [ ] Leave MkDocs nav + home index to **S3**

- [ ] **2b.3 Optional sample**
  - [ ] Minimal sample only if it runs in CI or has a clear “requires .NET SDK” maintainer path
  - [ ] Do not block release on NuGet publish

---

## Acceptance criteria

- [ ] Guide merged or explicitly deferred with reason in demand sheet
- [ ] No protocol fork
- [ ] Status (research vs maintained) is obvious in the first screen of the doc

## Skip condition

If S0 records **no-go**, mark this sprint **SKIPPED** in the roadmap table and do not open a branch.
