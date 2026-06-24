# PRD: ASAP Protocol v2.5.1 — Adapter Lab II

> **Product Requirements Document**
>
> **Version**: 2.5.1
> **Status**: PLANNED (blocked until v2.5.0 ships)
> **Created**: 2026-04-28 (as v2.3.2); **renumbered**: 2026-06-22
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md)
> **Successor**: [prd-v2.5.2-distribution-loop.md](./prd-v2.5.2-distribution-loop.md)
>
> **Migration note**: Formerly `product/prd/private/prd-v2.3.2-enterprise-workflow-adapters.md` (v2.3.2). Renumbered post-v2.4.1; executes after MCP Auth Bridge.

---

## 1. Purpose

v2.5.1 expands adoption testing into **enterprise and workflow-heavy ecosystems** after v2.5.0 delivers MCP auth and v2.3.1 (Adapter Lab I) validated high-signal TypeScript frameworks.

**Question to answer:** which teams need ASAP because their agents must cross organizational, cloud, or workflow boundaries?

---

## 2. Scope

| Candidate | Priority | Hypothesis | Deliverable |
|-----------|----------|------------|-------------|
| Microsoft Agent Framework / Semantic Kernel | P0 if Azure demand | Enterprise/.NET/Azure needs identity + capability grants | Interop spike + .NET guide |
| Haystack | P1 | RAG teams need discoverable retrieval agents | Provider recipe |
| Letta | P1 | Persistent-memory assistants need scoped remote tool access | Capability + memory safety guide |
| n8n / Activepieces-style automation | P1 | Workflow builders expose automations as agent capabilities | Connector prototype |
| Zapier / Make | P2 | Broad audience; partnership risk | Research only unless demand |

---

## 3. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| LAB2-001 | Reuse v2.3.0/v2.3.1/v2.5.0 adapter interfaces; no protocol fork | MUST |
| LAB2-002 | Ship ≥1 enterprise/workflow example converting workflow/API → ASAP capabilities | MUST |
| LAB2-003 | Document security for automation connectors (secrets, least privilege, HTTPS/TLS) | MUST |
| LAB2-004 | Homepage/site updates routing to new guides | MUST |
| LAB2-005 | Capture learning: open adapters vs hosted control-plane vs enterprise deployment | MUST |
| LAB2-006 | Where MCP is exposed, use v2.5.0 Auth Bridge patterns | SHOULD |

---

## 4. Open Core notes

**Likely public:** SDK adapter interfaces, connector examples, Compliance Harness guidance.

**Likely private/paid later:** hosted registry workflows, org policy engine, SSO/RBAC, audit exports at scale.

---

## 5. Success metrics

| Metric | Target |
|--------|--------|
| Enterprise/workflow prototype | 1+ |
| Security guide for automation connectors | Published |
| External demand signal | 3+ asks or 1 credible partner conversation |

---

## 6. Related documents

- **v2.3.1 (shipped)**: `product/prd/private/prd-v2.3.1-adapter-lab.md`
- **Adoption foundation**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Renumbered v2.3.2 → v2.5.1; blocked on v2.5.0 |
