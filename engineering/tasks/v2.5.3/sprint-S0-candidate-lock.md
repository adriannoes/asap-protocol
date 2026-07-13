# Sprint S0: Candidate lock & demand check (v2.5.3)

**PRD**: [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md) §2 D1–D7, §6  
**Branch**: `feat/v2.5.3-s0-candidate-lock` → **`release/2.5.3`**  
**Depends on**: v2.5.2 shipped

**Trigger:** Maintainer kickoff of Adapter Lab II.  
**Enables:** S1 primary prototype; optional S1b; planned S1c.  
**Depends on:** PRD locked decisions; GitHub issues / partner notes.

---

## Goal

Confirm the **default primary** (workflow connector) or document an explicit swap; decide go/no-go for Semantic Kernel (D2); confirm **S1c NeMo Agent Toolkit** (D7, default go).

---

## Tasks

- [ ] **1.1 Create integration branch**
  - [ ] `git checkout main && git pull`
  - [ ] `git checkout -b release/2.5.3 && git push -u origin release/2.5.3`
  - [ ] Point this folder’s status to ACTIVE in [tasks-v2.5.3-roadmap.md](./tasks-v2.5.3-roadmap.md) when started

- [ ] **1.2 Demand sheet**
  - [ ] Count open/closed issues with `adapter-request` (or equivalent) for: Semantic Kernel / Microsoft Agent Framework, Haystack, Letta, n8n/Activepieces, Zapier/Make, **NeMo Agent Toolkit / nvidia-nat**
  - [ ] Note Discord / email / partner asks since Lab I (2026-05-21)
  - [ ] Write results into `engineering/tasks/v2.5.3/demand-sheet.md` (can stay local if sensitive)

- [ ] **1.3 Lock primary (D1)**
  - [ ] Default: **n8n / Activepieces-style workflow → ASAP capabilities**
  - [ ] If demand strongly favors another candidate that still meets LAB2-002 (workflow/API → capabilities), document the swap in the demand sheet and update PRD changelog
  - [ ] Confirm reuse path: OpenAPI adapter vs thin custom example (prefer OpenAPI)

- [ ] **1.4 D2 gate (Semantic Kernel)**
  - [ ] **Go** if ≥1 credible Azure/.NET partner ask **or** ≥3 `adapter-request` for SK/MAF **or** maintainer override
  - [ ] **No-go** otherwise → skip [sprint-S1b-semantic-kernel.md](./sprint-S1b-semantic-kernel.md); leave a one-paragraph “not this release” note in demand sheet

- [ ] **1.5 D7 gate (NeMo Agent Toolkit)**
  - [ ] **Default: go** → schedule [sprint-S1c-nemo-agent-toolkit.md](./sprint-S1c-nemo-agent-toolkit.md)
  - [ ] Confirm research map present: [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md)
  - [ ] **No-go** only with explicit maintainer note (capacity); do not silently drop
  - [ ] Record intended Path A vs guide-only based on capacity (can refine in S1c §2c.2)

- [ ] **1.6 P1/P2 parking**
  - [ ] Haystack / Letta: recipe-only unless promoted under PRD §6
  - [ ] Zapier / Make: research-only

---

## Acceptance criteria

- [ ] `release/2.5.3` exists on origin
- [ ] Demand sheet exists with counts + primary decision + S1b go/no-go + **S1c go/no-go (default go)**
- [ ] Roadmap sprint table updated (S0 → In progress / Done; S1b/S1c status set)

## Relevant files

- `engineering/tasks/v2.5.3/demand-sheet.md` (new)
- `engineering/tasks/v2.5.3/tasks-v2.5.3-roadmap.md`
- `engineering/tasks/v2.5.3/research-nemo-agent-toolkit.md`
- `product/prd/prd-v2.5.3-adapter-lab-ii.md` (changelog only if primary swaps)
