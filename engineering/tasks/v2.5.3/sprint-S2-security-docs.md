# Sprint S2: Security guide & MCP patterns (v2.5.3)

**PRD**: LAB2-003, LAB2-006  
**Branch**: `feat/v2.5.3-s2-security-docs` → **`release/2.5.3`**  
**Depends on**: [S1](./sprint-S1-workflow-prototype.md) example shape known

**Trigger:** Primary prototype exists (even if polish remains).  
**Enables:** Safe public docs; S4 DoD.  
**Depends on:** S1 example + v2.5.0 Auth Bridge docs.

---

## Goal

Publish a security guide for automation/workflow connectors, and wire MCP Auth Bridge guidance wherever the Lab II example exposes MCP.

---

## Tasks

- [ ] **3.1 Security guide (LAB2-003)**
  - [ ] Add `docs/guides/automation-connector-security.md`
  - [ ] Cover at minimum: secrets (env, not repo), least-privilege capability grants, HTTPS/TLS for callbacks, webhook authenticity, rate limits / abuse, what not to put in manifests
  - [ ] Cross-link S1 example README

- [ ] **3.2 MCP Auth Bridge (LAB2-006)**
  - [ ] If S1 (or S1b) exposes MCP tools: show `protect_server` / Mode A vs Mode B pointer to [mcp-auth-bridge.md](../../../docs/adapters/mcp-auth-bridge.md)
  - [ ] If MCP is not exposed: add an explicit **N/A** note in the security guide and roadmap DoD

- [ ] **3.3 Example hardening pass**
  - [ ] Ensure example uses `.env.example` placeholders only
  - [ ] Reject any committed tokens; document HTTPS recommendation for production webhooks

---

## Acceptance criteria

- [ ] LAB2-003: security guide published (MkDocs nav + docs index wiring complete in **S3** — [docs-review-checklist.md](./docs-review-checklist.md))
- [ ] LAB2-006: satisfied or N/A documented
- [ ] Example README points to the security guide

## Relevant files

- `docs/guides/automation-connector-security.md` (new)
- `docs/adapters/mcp-auth-bridge.md` (reference)
- `examples/workflow_asap_connector/README.md` (modify)
