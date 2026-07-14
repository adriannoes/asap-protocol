# Sprint S2: Security guide & MCP patterns (v2.5.3)

**PRD**: LAB2-003, LAB2-006  
**Branch**: `feat/v2.5.3-s2-s3-docs-review` → **`release/2.5.3`**  
**Depends on**: [S1](./sprint-S1-workflow-prototype.md) example shape known

**Trigger:** Primary prototype exists (even if polish remains).  
**Enables:** Safe public docs; S4 DoD.  
**Depends on:** S1 example + v2.5.0 Auth Bridge docs.

---

## Goal

Publish a security guide for automation/workflow connectors, and wire MCP Auth Bridge guidance wherever the Lab II example exposes MCP.

---

## Tasks

- [x] **3.1 Security guide (LAB2-003)**
  - [x] Add `docs/guides/automation-connector-security.md`
  - [x] Cover at minimum: secrets (env, not repo), least-privilege capability grants, HTTPS/TLS for callbacks, webhook authenticity, rate limits / abuse, what not to put in manifests
  - [x] Cross-link S1 example README

- [x] **3.2 MCP Auth Bridge (LAB2-006)**
  - [x] If S1 (or S1b) exposes MCP tools: show `protect_server` / Mode A vs Mode B pointer to [mcp-auth-bridge.md](../../../docs/adapters/mcp-auth-bridge.md)
  - [x] If MCP is not exposed: add an explicit **N/A** note in the security guide and roadmap DoD
  - Note: workflow primary example is **OpenAPI-only → N/A**; NeMo Path A uses Mode A `protect_server` (stdio) with **dev-only** env JWT fallback

- [x] **3.3 Example hardening pass**
  - [x] Ensure example uses `.env.example` placeholders only
  - [x] Reject any committed tokens; document HTTPS recommendation for production webhooks

---

## Acceptance criteria

- [x] LAB2-003: security guide published (MkDocs nav + docs index wiring complete in **S3** — [docs-review-checklist.md](./docs-review-checklist.md))
- [x] LAB2-006: satisfied or N/A documented
- [x] Example README points to the security guide

## Relevant files

- `docs/guides/automation-connector-security.md` (new)
- `docs/adapters/mcp-auth-bridge.md` (reference)
- `docs/integrations/workflow-connectors.md` (See also → security guide)
- `docs/integrations/nemo-agent-toolkit.md` (See also → security guide + Auth Bridge Mode A/B)
- `examples/workflow_asap_connector/README.md` (modify — security guide links; removed “deferred to S2”)
- `examples/workflow_asap_connector/.env.example` (placeholders + webhook secret stub)
- `examples/nemo_agent_toolkit_asap/README.md` (security guide link)
- `examples/nemo_agent_toolkit_asap/.env.example` (placeholders; env JWT = replace-me)

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-14 | T2 | Approved (attempt 2) | [review-v2.5.3-S2-S3-docs-review-20260714-r2.md](../../code-review/private/review-v2.5.3-S2-S3-docs-review-20260714-r2.md) |
| 2026-07-14 | T2 | Rejected (attempt 1) | [review-v2.5.3-S2-S3-docs-review-20260714.md](../../code-review/private/review-v2.5.3-S2-S3-docs-review-20260714.md) |
