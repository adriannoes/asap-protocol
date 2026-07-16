# Docs review checklist — v2.5.3 Adapter Lab II

> **Purpose**: Single checklist so Lab II docs land consistently across MkDocs, `docs/index.md`, cross-links, migration, and the web app.  
> **Owned by**: [sprint-S3-docs-review.md](./sprint-S3-docs-review.md) (execution); S1 / S1b / S1c / S2 **produce** pages that this review wires up.  
> **Do not** invent pages here — only verify, link, and fix nav/stale copy.

---

## 1. New pages expected this release

| Page | Producer sprint | Status |
|------|-----------------|--------|
| `docs/integrations/workflow-connectors.md` | S1 | ✅ shipped S1 |
| `docs/guides/automation-connector-security.md` | S2 | ✅ shipped S2 |
| `docs/integrations/nemo-agent-toolkit.md` | S1c (default go) | ✅ shipped S1c (experimental) |
| `docs/integrations/microsoft-agent-framework.md` (not `semantic-kernel.md`) | S1b (D2 go / research) | ✅ shipped S1b (research/experimental) |
| Example READMEs under `examples/workflow_asap_connector/`, `examples/nemo_agent_toolkit_asap/` | S1 / S1c | ✅ shipped |
| `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md` | pre–Lab II | ✅ exist (wired in S3 nav) |

Each new page MUST: English, HTTPS/TLS note where network is involved, link to security guide when automation/MCP is involved, and an explicit **status** (maintained / experimental / research).

---

## 2. MkDocs nav (`mkdocs.yml`)

**Resolved in S3 (2026-07-14):** `mkdocs.yml` now lists **Adapters** (OpenAPI, MCP Auth Bridge) and Lab II **Integrations** / **Guides**. Pre-S3 gap (Mastra + OpenAI Agents only) is closed.

- [x] Add **Adapters** section (or nest under Integrations):
  - [x] `adapters/openapi.md`
  - [x] `adapters/mcp-auth-bridge.md`
- [x] Extend **Integrations**:
  - [x] Keep Mastra + OpenAI Agents
  - [x] Add workflow connectors (S1)
  - [x] Add NeMo Agent Toolkit if S1c shipped
  - [x] Add Microsoft Agent Framework (S1b shipped; page name `microsoft-agent-framework.md`)
- [x] Extend **Guides**:
  - [x] `guides/automation-connector-security.md`
  - [x] Confirm MCP / OpenAPI still reachable (via Adapters or Guides)
- [x] Smoke: `uv run mkdocs build --strict` — Lab II / Adapters nav targets resolve; site builds with `uv run mkdocs build`. **`--strict` still aborts** on pre-existing warnings (missing `api/*` + `contributing.md` nav stubs; out-of-docs link warnings) — not introduced by Lab II pages.

---

## 3. Docs home (`docs/index.md`)

- [x] Bump “Latest reference implementation” blurb for **v2.5.3** when releasing (S4 may own final version string; S3 can draft) — **S3**: keep **v2.5.2** as latest PyPI; mention Lab II docs train + draft migration stub
- [x] Features / Documentation lists: link new Lab II pages
- [x] Keep MCP Auth Bridge + OpenAPI + Lab I adapters accurate (no stale “next is v2.5.3” after ship)
- [x] Mention NeMo / workflow only if pages exist

---

## 4. Cross-link pass (existing docs)

Update only where Lab II changes the story; avoid drive-by rewrites.

| File | What to check | S3 |
|------|----------------|-----|
| `docs/mcp-integration.md` | Point to Auth Bridge; if NAT/workflow examples use MCP, link them | ✅ |
| `docs/adapters/mcp-auth-bridge.md` | “See also” → NAT guide + automation security (if Path A) | ✅ |
| `docs/adapters/openapi.md` | “See also” → workflow connectors (OpenAPI reuse path) | ✅ |
| `docs/integrations/mastra.md` | Optional footer: sibling integrations index / Lab II pages | ✅ |
| `docs/integrations/openai-agents.md` | Same | ✅ |
| `docs/migration.md` | Section **Upgrading from v2.5.2 → v2.5.3** (S4 finalizes; S3 can stub) | ✅ draft |
| `docs/troubleshooting.md` | One stub for connector auth / MCP grant denials if examples introduce new failure modes | ✅ |
| `docs/security.md` | Link automation-connector-security if it belongs in the security TOC | ✅ |
| `docs/tutorials/multi-agent.md` | Only if multi-agent narrative should mention NAT/workflow (optional) | skipped (optional) |
| `README.md` (repo root) | Short pointer to new integrations if README lists them today | ✅ |

---

## 5. Taxonomy & naming

Keep the split clear for readers:

| Folder | Use for |
|--------|---------|
| `docs/adapters/` | First-party ASAP packages (`asap.adapters.*`) — OpenAPI, MCP Auth Bridge |
| `docs/integrations/` | Framework / ecosystem guides (Mastra, OpenAI Agents, workflow, NAT, MAF) |
| `docs/guides/` | Cross-cutting how-tos (security, ShellClaw, compliance) |

- [x] New Lab II pages follow this split (do not put NAT under `adapters/` unless we ship `asap.adapters.nat`)
- [x] Titles use sentence case; status banner on experimental pages (MAF / NAT kept)

---

## 6. Web app / CTAs (LAB2-004)

- [x] `apps/web` developer-experience / FeaturesSection / WhatsNewRibbon: cards or links for shipped Lab II guides
- [x] Telemetry CTA ids if new docs CTAs are added (`homepage-cta-ids.ts` pattern)
- [x] No Distribution Loop hero rewrite (v2.5.4)

*(Owned by task 4.4 — complete.)*

---

## 7. Consistency / quality gate

- [x] No broken relative links among new + touched pages
- [x] No secrets / Keycloak default passwords copied into ASAP docs (link upstream NAT examples instead)
- [x] NAT docs: ASAP complements A2A/MCP — never “ASAP replaces A2A in NeMo”
- [x] `@asap-protocol/mcp-auth` still described as deferred where HTTP MCP middleware is mentioned
- [x] English only in committed docs

---

## 8. Sign-off

| Role | Sign-off |
|------|----------|
| S3 owner | ☑ Docs checklist §§1–7 complete for shipped pages (web §6 done in 4.4); §8 version strings deferred to S4 |
| S4 owner | ☑ Version strings + migration section match tag [`v2.5.3`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.3) (shipped 2026-07-16; PyPI `asap-protocol==2.5.3`) |

---

## Change log

| Date | Change |
|------|--------|
| 2026-07-12 | Initial checklist from `docs/` + `mkdocs.yml` audit for Lab II |
| 2026-07-13 | S3 docs half: inventory marked shipped; MkDocs Adapters + Lab II nav; cross-links; migration stub; learnings + demand snapshot |
| 2026-07-13 | S3 task 4.4: web CTAs / feature cards / DX ecosystem entries for Lab II guides; §6 signed; S3 owner §§1–7 |
| 2026-07-14 | S4: version strings 2.5.3, migration finalized, public URLs → `main`, §8 signed |
| 2026-07-16 | S4: tag/publish confirmed; §8 note updated to shipped |
