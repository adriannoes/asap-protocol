# PRD: ASAP Protocol v2.5.3 — Adapter Lab II

> **Product Requirements Document**
>
> **Version**: 2.5.3
> **Status**: SHIPPED (tag [`v2.5.3`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.3), 2026-07-16)
> **Created**: 2026-04-28 (as v2.3.2); **renumbered**: 2026-06-22 → v2.5.1; **2026-07-08 → v2.5.3**
> **Last Updated**: 2026-07-16
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.2-security-follow-up.md](./prd-v2.5.2-security-follow-up.md)
> **Successor**: [prd-v2.5.4-distribution-loop.md](./prd-v2.5.4-distribution-loop.md) (✅ shipped 2026-07-18) → next [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md)
> **Tasks**: [engineering/tasks/v2.5.3/tasks-v2.5.3-roadmap.md](../../engineering/tasks/v2.5.3/tasks-v2.5.3-roadmap.md)
>
> **Migration note**: Formerly `product/prd/private/prd-v2.3.2-enterprise-workflow-adapters.md` (v2.3.2), then `prd-v2.5.1-adapter-lab-ii.md`. v2.5.1 was consumed by the code quality patch (2026-06-26); this work slipped again when v2.5.2 absorbed the security follow-up train.

---

## 1. Purpose

v2.5.3 expands adoption testing into **enterprise and workflow-heavy ecosystems** after v2.5.0 delivers MCP auth, v2.5.1/v2.5.2 harden the core, and v2.3.1 (Adapter Lab I) validated high-signal TypeScript frameworks (Mastra + OpenAI Agents).

**Question to answer:** which teams need ASAP because their agents must cross organizational, cloud, or workflow boundaries?

This release is not “support every enterprise stack.” It ships **one** solid prototype plus security/docs/site surface, then records what should stay open-source vs move to hosted/enterprise later (LAB2-005).

---

## 2. Strategic decisions (locked 2026-07-11)

| ID | Decision |
|----|----------|
| **D1** | **Default primary (MUST):** n8n / Activepieces-style **workflow → ASAP capabilities** prototype (docs + runnable example). Answers the Lab II question without requiring .NET. Prefer reuse of OpenAPI adapter / capability mapping over a new protocol surface. |
| **D2** | **Microsoft Agent Framework / Semantic Kernel** is **conditional P0**. Promote to a full sprint only if S0 finds Azure/.NET demand (`adapter-request` issues, partner ask, or maintainer-confirmed signal). Otherwise: short research note only. |
| **D3** | **Haystack** and **Letta** stay P1: provider / memory-safety **recipes** (docs) unless demand promotes one to a second prototype after the primary ships. |
| **D4** | **Zapier / Make** = research note only (P2). No partnership chase in this release. |
| **D5** | **`@asap-protocol/mcp-auth` is out of scope** (npm patch TBD). LAB2-006 = Python Auth Bridge patterns when an example exposes MCP. |
| **D6** | No protocol fork. No new public methods on `src/asap/transport/{server,client}.py` (existing Lab I CI lint still applies). |
| **D7** | **NVIDIA NeMo Agent Toolkit** (`nvidia-nat`, ex-AgentIQ) is a **planned Lab II spike (S1c)** — not demand-gated like D2. Default **go**. Position ASAP as identity/capability **complement** to NAT’s native A2A + MCP (do not claim A2A replacement). Pin upstream at spike start (map: [research-nemo-agent-toolkit.md](../../engineering/tasks/v2.5.3/research-nemo-agent-toolkit.md)). Third-party NAT plugin package (`nemo-agent-toolkit-asap`) is **out of ship**; Path A MCP bridge demo preferred; Path B Agent Card → Manifest docs always. |

---

## 3. Scope

| Candidate | Priority | Hypothesis | Deliverable in v2.5.3 |
|-----------|----------|------------|------------------------|
| n8n / Activepieces-style automation | **P0 default** | Workflow builders expose automations as agent capabilities | Connector prototype + guide + example (**LAB2-002**) |
| Microsoft Agent Framework / Semantic Kernel | P0 if Azure demand | Enterprise/.NET/Azure needs identity + capability grants | Interop spike + .NET guide **only if D2 gate passes** |
| **NVIDIA NeMo Agent Toolkit** | **P0 planned spike (D7)** | GPU/enterprise teams already on NAT need ASAP policy when crossing org boundaries; NAT already speaks A2A+MCP | Research map + guide + optional MCP bridge demo (**S1c**); not a release blocker |
| Haystack | P1 | RAG teams need discoverable retrieval agents | Recipe doc (optional second prototype) |
| Letta | P1 | Persistent-memory assistants need scoped remote tool access | Capability + memory safety guide |
| Zapier / Make | P2 | Broad audience; partnership risk | Research only |

---

## 4. Carry-over from v2.5.0: `@asap-protocol/mcp-auth`

> **Decision (2026-06-24, S4 spike):** Ship `@asap-protocol/mcp-auth` in a **future npm patch** (TBD git tag — **not** tag `v2.5.0.1`, which published **`asap-compliance` 1.3.0** only), **not** in v2.5.0 and **not** as part of Adapter Lab II scope.
>
> **Spike:** [typescript-mcp-auth-spike.md](../../engineering/tasks/v2.5.0/typescript-mcp-auth-spike.md)
> **Backlog:** [backlog-mcp-auth-typescript.md](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md)
> **Source requirements:** [prd-v2.5.0-mcp-auth-bridge.md §5.4](./prd-v2.5.0-mcp-auth-bridge.md#54-typescript-should) (MCP-TS-001..003)

### 4.1 Rationale

| Factor | Detail |
|--------|--------|
| PRD priority | MCP-TS-001..003 are **SHOULD**; Python MCP-AUTH-* / MCP-DOC-* are **MUST** for v2.5.0 |
| Release gate | v2.5.0 shipped the Python stdio MCP Auth Bridge |
| Implementation gap | No `packages/typescript/mcp-auth/`, no public `verifyAgentJwt()` on `@asap-protocol/client` for HTTP/SSE middleware publish CI |

Deferring does **not** block Adapter Lab II. The npm middleware may ship as a patch without delaying this release.

### 4.2 Relation to Adapter Lab II (LAB2-006)

LAB2-006 applies to **Python Auth Bridge patterns** where Adapter Lab II work exposes MCP. It does not require shipping `@asap-protocol/mcp-auth`.

---

## 5. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| LAB2-001 | Reuse v2.3.0/v2.3.1/v2.5.0 adapter interfaces; no protocol fork | MUST |
| LAB2-002 | Ship ≥1 enterprise/workflow example converting workflow/API → ASAP capabilities | MUST |
| LAB2-003 | Document security for automation connectors (secrets, least privilege, HTTPS/TLS) | MUST |
| LAB2-004 | Homepage/site updates routing to new guides | MUST |
| LAB2-005 | Capture learning: open adapters vs hosted control-plane vs enterprise deployment | MUST |
| LAB2-006 | Where MCP is exposed, use v2.5.0 Auth Bridge patterns | SHOULD |

---

## 6. Promotion gates

Promote a **second** candidate (SK / Haystack / Letta) from recipe to maintained prototype only when at least one holds:

- 3+ external `adapter-request` issues (or equivalent asks) for that stack
- A credible partner wants to list an agent on that stack
- The extra prototype fits in &lt;1 week without protocol changes and reuses existing SDK/adapters

The **default primary** (workflow connector) does **not** wait on those gates; it is the Lab II MUST.

**NeMo Agent Toolkit (D7):** S1c always runs as a planned spike. Promote Path A from “guide only” to “runnable example” only when the transport/auth gap analysis says it is honest and ≤1 week. A published `nemo-agent-toolkit-asap` third-party plugin is a **post–v2.5.3** decision.

---

## 7. Open Core notes

**Likely public:** SDK adapter interfaces, connector examples, Compliance Harness guidance, security guide for automation connectors.

**Likely private/paid later:** hosted registry workflows, org policy engine, SSO/RBAC, audit exports at scale.

LAB2-005 must write this down before release (short decision note under `engineering/tasks/v2.5.3/` or local `product/strategy/`).

---

## 8. Success metrics

| Metric | Target |
|--------|--------|
| Enterprise/workflow prototype | 1+ (runnable example + guide) |
| Security guide for automation connectors | Published under `docs/` |
| Homepage/docs CTA to new guides | Present |
| External demand signal | 3+ asks or 1 credible partner conversation (tracked; not a ship blocker if primary ships) |
| Open vs hosted learnings | Written note (LAB2-005) |

---

## 9. Out of scope

| Item | Where it lives |
|------|----------------|
| `@asap-protocol/mcp-auth` | [backlog-mcp-auth-typescript.md](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md) |
| Distribution Loop (homepage hero rewrite, templates pack) | [prd-v2.5.4-distribution-loop.md](./prd-v2.5.4-distribution-loop.md) |
| Formal Spec / A2A runtime bridge | [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md) |
| `nemo-agent-toolkit-asap` third-party NAT plugin publish | Post–v2.5.3 (S1c Path C feasibility only) |
| Governance G5/G6 product work | Local [strategy/roadmap.md §4](../strategy/roadmap.md#4-explore-later-governance-adjacent-g5g6) |
| Registry API PostgreSQL | Trigger-gated — strategy roadmap §3 |

---

## 10. Related documents

- **Tasks**: [tasks-v2.5.3-roadmap.md](../../engineering/tasks/v2.5.3/tasks-v2.5.3-roadmap.md)
- **Docs review**: [docs-review-checklist.md](../../engineering/tasks/v2.5.3/docs-review-checklist.md)
- **v2.3.1 Adapter Lab I (shipped)**: `product/prd/private/prd-v2.3.1-adapter-lab.md`
- **Adoption foundation**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)
- **Security baseline**: [prd-v2.5.2-security-follow-up.md](./prd-v2.5.2-security-follow-up.md)
- **MCP Auth Bridge**: [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md)
- **NAT research map**: [research-nemo-agent-toolkit.md](../../engineering/tasks/v2.5.3/research-nemo-agent-toolkit.md)
- **Strategy hub (local)**: [roadmap.md](../strategy/roadmap.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-11 | **D7**: NeMo Agent Toolkit planned S1c spike; research map linked; third-party NAT plugin out of ship |
| 2026-07-12 | Docs review checklist + S3 docs-review sprint linked for Lab II public surface |
| 2026-07-11 | Status → READY FOR KICKOFF; locked D1–D6; promotion gates; linked task plan; clarified primary = workflow connector |
| 2026-07-08 | Renumbered v2.5.1 → **v2.5.3** (v2.5.1 = quality patch; v2.5.2 = security follow-up) |
| 2026-06-24 | §3: Record S4 defer of `@asap-protocol/mcp-auth` (MCP-TS-001..003) |
| 2026-06-22 | Renumbered v2.3.2 → v2.5.1; blocked on v2.5.0 |
