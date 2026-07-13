# Docs review checklist — v2.5.3 Adapter Lab II

> **Purpose**: Single checklist so Lab II docs land consistently across MkDocs, `docs/index.md`, cross-links, migration, and the web app.  
> **Owned by**: [sprint-S3-docs-review.md](./sprint-S3-docs-review.md) (execution); S1 / S1b / S1c / S2 **produce** pages that this review wires up.  
> **Do not** invent pages here — only verify, link, and fix nav/stale copy.

---

## 1. New pages expected this release

| Page | Producer sprint | Status |
|------|-----------------|--------|
| `docs/integrations/workflow-connectors.md` (or `n8n.md`) | S1 | ☐ |
| `docs/guides/automation-connector-security.md` | S2 | ☐ |
| `docs/integrations/nemo-agent-toolkit.md` | S1c (default go) | ☐ / skip |
| `docs/integrations/semantic-kernel.md` (or MAF name) | S1b (if D2 go) | ☐ / skip |
| Example READMEs under `examples/workflow_*`, `examples/nemo_agent_toolkit_asap/` | S1 / S1c | ☐ |

Each new page MUST: English, HTTPS/TLS note where network is involved, link to security guide when automation/MCP is involved, and an explicit **status** (maintained / experimental / research).

---

## 2. MkDocs nav (`mkdocs.yml`)

Current gap (as of 2026-07-12): **Integrations** only lists Mastra + OpenAI Agents; **Adapters** (OpenAPI, MCP Auth Bridge) are missing from `nav` even though files exist under `docs/adapters/`.

- [ ] Add **Adapters** section (or nest under Integrations):
  - [ ] `adapters/openapi.md`
  - [ ] `adapters/mcp-auth-bridge.md`
- [ ] Extend **Integrations**:
  - [ ] Keep Mastra + OpenAI Agents
  - [ ] Add workflow connectors (S1)
  - [ ] Add NeMo Agent Toolkit if S1c shipped
  - [ ] Add Semantic Kernel if S1b shipped
- [ ] Extend **Guides**:
  - [ ] `guides/automation-connector-security.md`
  - [ ] Confirm MCP / OpenAPI still reachable (via Adapters or Guides)
- [ ] Smoke: `uv run mkdocs build --strict` (or project’s documented MkDocs command) — fix broken nav paths

---

## 3. Docs home (`docs/index.md`)

- [ ] Bump “Latest reference implementation” blurb for **v2.5.3** when releasing (S4 may own final version string; S3 can draft)
- [ ] Features / Documentation lists: link new Lab II pages
- [ ] Keep MCP Auth Bridge + OpenAPI + Lab I adapters accurate (no stale “next is v2.5.3” after ship)
- [ ] Mention NeMo / workflow only if pages exist

---

## 4. Cross-link pass (existing docs)

Update only where Lab II changes the story; avoid drive-by rewrites.

| File | What to check |
|------|----------------|
| `docs/mcp-integration.md` | Point to Auth Bridge; if NAT/workflow examples use MCP, link them |
| `docs/adapters/mcp-auth-bridge.md` | “See also” → NAT guide + automation security (if Path A) |
| `docs/adapters/openapi.md` | “See also” → workflow connectors (OpenAPI reuse path) |
| `docs/integrations/mastra.md` | Optional footer: sibling integrations index / Lab II pages |
| `docs/integrations/openai-agents.md` | Same |
| `docs/migration.md` | Section **Upgrading from v2.5.2 → v2.5.3** (S4 finalizes; S3 can stub) |
| `docs/troubleshooting.md` | One stub for connector auth / MCP grant denials if examples introduce new failure modes |
| `docs/security.md` | Link automation-connector-security if it belongs in the security TOC |
| `docs/tutorials/multi-agent.md` | Only if multi-agent narrative should mention NAT/workflow (optional) |
| `README.md` (repo root) | Short pointer to new integrations if README lists them today |

---

## 5. Taxonomy & naming

Keep the split clear for readers:

| Folder | Use for |
|--------|---------|
| `docs/adapters/` | First-party ASAP packages (`asap.adapters.*`) — OpenAPI, MCP Auth Bridge |
| `docs/integrations/` | Framework / ecosystem guides (Mastra, OpenAI Agents, workflow, NAT, SK) |
| `docs/guides/` | Cross-cutting how-tos (security, ShellClaw, compliance) |

- [ ] New Lab II pages follow this split (do not put NAT under `adapters/` unless we ship `asap.adapters.nat`)
- [ ] Titles use sentence case; status banner on experimental pages

---

## 6. Web app / CTAs (LAB2-004)

- [ ] `apps/web` developer-experience / FeaturesSection / WhatsNewRibbon: cards or links for shipped Lab II guides
- [ ] Telemetry CTA ids if new docs CTAs are added (`homepage-cta-ids.ts` pattern)
- [ ] No Distribution Loop hero rewrite (v2.5.4)

---

## 7. Consistency / quality gate

- [ ] No broken relative links among new + touched pages
- [ ] No secrets / Keycloak default passwords copied into ASAP docs (link upstream NAT examples instead)
- [ ] NAT docs: ASAP complements A2A/MCP — never “ASAP replaces A2A in NeMo”
- [ ] `@asap-protocol/mcp-auth` still described as deferred where HTTP MCP middleware is mentioned
- [ ] English only in committed docs

---

## 8. Sign-off

| Role | Sign-off |
|------|----------|
| S3 owner | ☐ Docs checklist complete for pages that shipped |
| S4 owner | ☐ Version strings + migration section match tag `v2.5.3` |

---

## Change log

| Date | Change |
|------|--------|
| 2026-07-12 | Initial checklist from `docs/` + `mkdocs.yml` audit for Lab II |
