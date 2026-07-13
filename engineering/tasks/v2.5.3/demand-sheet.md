# Demand sheet — Adapter Lab II (v2.5.3) S0

**Date**: 2026-07-13  
**Author context**: S0 Candidate lock kickoff (maintainer LGTM decisions applied)  
**Repo**: [adriannoes/asap-protocol](https://github.com/adriannoes/asap-protocol)  
**PRD**: [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md)  
**Sprint**: [sprint-S0-candidate-lock.md](./sprint-S0-candidate-lock.md)  
**Branch**: `feat/v2.5.3-s0-s1-workflow` → `release/2.5.3` (exists on origin; not recreated)

---

## Method

1. Listed repo labels (`gh label list --repo adriannoes/asap-protocol --limit 100`).
2. Confirmed **no `adapter-request` label** (and no equivalent adapter-demand label).
3. Searched issues with keywords (`gh issue list --state all --limit 50 --search …`) for each Lab II candidate and a combined OR query.
4. Treated partner / Discord / email demand as **in-repo maintainer-logged only** (no private CRM dump in this sheet).

**Combined search (2026-07-13):**

```text
n8n OR activepieces OR haystack OR letta OR semantic-kernel OR 'semantic kernel'
OR nemo OR nvidia-nat OR zapier OR make.com
```

Result: **0 issues**.

Per-keyword searches for the same terms also returned **0** matching issues. A search for `adapter-request` / `adapter request` only hit Lab I promotion-gate reviews (#158 Mastra, #159 OpenAI Agents) — **not** demand for Lab II candidates; those are excluded from the counts table below.

---

## Counts (GitHub issues)

| Candidate | Open | Closed | Notes |
|-----------|------|--------|-------|
| Semantic Kernel / Microsoft Agent Framework | 0 | 0 | No keyword hits; no `adapter-request` label |
| Haystack | 0 | 0 | Honest zero |
| Letta | 0 | 0 | Honest zero |
| n8n / Activepieces | 0 | 0 | Honest zero (primary still locked by PRD D1 default) |
| Zapier / Make | 0 | 0 | Honest zero |
| NeMo Agent Toolkit / nvidia-nat | 0 | 0 | Honest zero; D7 go is maintainer default, not issue volume |

**Labels snapshot:** `bug`, `documentation`, `enhancement`, `good first issue`, `frontend`, `question`, `backend`, `dependencies`, `security`, `refactor`, `test`, `resolved`, `deferred` — **no `adapter-request`**.

---

## Discord / email / partner asks (since Lab I, 2026-05-21)

No maintainer-logged partner asks recorded in-repo for Semantic Kernel / MAF, Haystack, Letta, n8n/Activepieces, Zapier/Make, or NeMo Agent Toolkit since Lab I. **Treat as zero unless override.**

---

## Primary decision (D1)

**Confirmed (DEFAULT, no swap):** n8n / Activepieces-style **workflow → ASAP capabilities**.

- Meets LAB2-002 (workflow/API → capabilities).
- Issue volume does not favor another candidate; PRD default stands.
- **Reuse path:** prefer existing **OpenAPI adapter** over a new package or thin custom wire format.
- PRD changelog: **not updated** (primary did not swap).

---

## S1b go/no-go (D2) — Semantic Kernel

**Original S0 decision (2026-07-13): no-go** — evidence below is unchanged.

**Rationale (S0):** Gate requires ≥1 credible Azure/.NET partner ask, ≥3 `adapter-request` issues for SK/MAF, or maintainer override. There is no `adapter-request` label; keyword search found **0** SK/MAF issues; no in-repo partner asks. Initial maintainer LGTM at S0: **no-go**.

**Maintainer override (2026-07-13): go** → run [sprint-S1b-semantic-kernel.md](./sprint-S1b-semantic-kernel.md) despite zero GitHub demand.

**Override rationale:** Explicit LGTM to pursue a **research / experimental** interop guide in v2.5.3 as part of the combined Lab II **S1b + S1c** initiative on branch `feat/v2.5.3-s1b-s1c-spikes`. Demand evidence remains zero; this is not a promotion to a maintained .NET SDK or NuGet surface. Prefer **guide-only** (see [research-semantic-kernel.md](./research-semantic-kernel.md)).

**In this release (override):** research/experimental Microsoft Agent Framework / Semantic Kernel interop guide only. No protocol fork; no NuGet publish.

---

## S1c go/no-go (D7) — NeMo Agent Toolkit

**Decision: go (DEFAULT)** → schedule [sprint-S1c-nemo-agent-toolkit.md](./sprint-S1c-nemo-agent-toolkit.md).

- Research map present: [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md).
- Issue volume is zero; go is **maintainer/PRD default**, not demand-driven.
- **Path intent:** prefer Path A (thin demo) when capacity allows; otherwise guide-only. **Refine Path A vs guide-only in S1c §2c.2** at spike start. Path C (third-party NAT plugin) remains deferred post–v2.5.3.

---

## P1 / P2 parking

**Haystack / Letta (P1):** recipe-only for v2.5.3 unless promoted under PRD §6 (credible demand + capacity). Do not schedule dedicated sprints.

**Zapier / Make (P2):** research-only. No prototype or first-class guide in this release.

---

## Acceptance checklist (S0)

| Criterion | Status |
|-----------|--------|
| Counts + method documented | Done |
| Primary (D1) locked, no swap | Done |
| S1b (D2) no-go + “not this release” note | Superseded: original no-go kept; **override go** recorded 2026-07-13 |
| S1c (D7) go + research map + Path intent | Done |
| P1/P2 parking recorded | Done |
| `release/2.5.3` on origin | Confirmed (`261e53b…`) |
