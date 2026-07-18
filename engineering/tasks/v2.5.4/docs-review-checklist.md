# Docs review checklist — v2.5.4 Distribution Loop

> **Purpose**: Single checklist so Distribution Loop docs and web routing land consistently across MkDocs, `docs/index.md`, starters, homepage CTAs, and DIST-006.  
> **Owned by**: [sprint-S3-homepage-routing.md](./sprint-S3-homepage-routing.md) (web/CTA execution) + S2 (guide producer); S1 produces starters that this review wires.  
> **Do not** invent pages here — only verify, link, and fix nav/stale copy.

---

## 1. New pages / packs expected this release

| Page / pack | Producer sprint | Status |
|-------------|-----------------|--------|
| `examples/starters/README.md` + three starters | S1 | ☑ done (2026-07-18) |
| `docs/guides/build-for-agents.md` | S2 | ☑ done (2026-07-18) |
| Homepage hero / CTA copy (agent-first) | S3 | ☐ pending |
| `docs/adapters/openapi.md`, `docs/adapters/mcp-auth-bridge.md`, `docs/sdks/typescript.md` | pre–v2.5.4 | ☐ exist (confirm linked) |

Each new page MUST: English, HTTPS/TLS note where network is involved, explicit **status** (maintained / experimental / research), and DIST-006-safe copy.

---

## 2. MkDocs nav (`mkdocs.yml`)

- [x] Guides: add `guides/build-for-agents.md`
- [ ] Confirm Adapters (OpenAPI, MCP Auth Bridge) still listed
- [ ] Confirm SDKs / tutorials still reachable for consumers linked from the guide
- [ ] Smoke: `uv run mkdocs build` — document any pre-existing `--strict` warnings (do not normalize new failures)

---

## 3. Docs home (`docs/index.md`)

- [x] Mention Distribution Loop / Build for agents when guide ships (See also)
- [ ] Link `examples/starters/` or guide as executable entry
- [ ] Keep version blurb accurate for train state (S5 owns final **2.5.4** string)

---

## 4. Cross-link pass

| File | What to check | Status |
|------|----------------|--------|
| `docs/guides/build-for-agents.md` | Links to all three starters + key adapters/SDK | ☑ (S2) |
| `examples/starters/README.md` | Links to guide + parent examples | ☑ (S1/S2) |
| `docs/adapters/openapi.md` | Optional “See also” → OpenAPI starter | ☑ |
| `docs/adapters/mcp-auth-bridge.md` | Optional “See also” → MCP starter | ☑ |
| `docs/sdks/typescript.md` | Optional “See also” → TS consumer starter | ☑ |
| `docs/migration.md` | Section **Upgrading from v2.5.3 → v2.5.4** (S5 finalizes) | ☐ |
| `README.md` (repo root) | Short pointer to starters/guide if README lists getting-started paths | ☐ |

---

## 5. Taxonomy & naming

| Folder | Use for |
|--------|---------|
| `docs/adapters/` | First-party ASAP packages (`asap.adapters.*`) |
| `docs/integrations/` | Framework / ecosystem guides |
| `docs/guides/` | Cross-cutting how-tos (**Build for agents** lives here) |
| `examples/starters/` | Thin adoption wrappers (not deep demos) |
| `examples/` (non-starters) | Canonical deep examples |

---

## 6. Web CTAs (`apps/web`)

- [ ] Primary hero CTAs → guide and/or `examples/starters/`
- [ ] Secondary marketplace CTAs (browse/register) still present
- [ ] WhatsNew / Features / How it Works primary actions resolve to live URLs
- [ ] `data-cta` IDs listed in `homepage-cta-ids.ts` remain stable or documented if extended
- [ ] No pricing / fundraising / private GTM strings (DIST-006)

---

## 7. Quality

- [ ] English only for public docs and starter READMEs
- [ ] No secrets in examples (`.env.example` placeholders only)
- [ ] Starter smoke commands documented and headless
- [ ] Broken-link spot check for new URLs

---

## 8. Sign-off

### S3 (docs/web surface)

| Item | Owner | Status |
|------|-------|--------|
| §§1–7 for MUST surface | S3 (+ S1/S2 producers) | ☐ |
| DIST-006 grep on touched public copy | S3 | ☐ |

### S5 (version strings)

| Item | Owner | Status |
|------|-------|--------|
| `docs/index.md` / README / migration version strings → **2.5.4** | S5 | ☐ |
| Post-publish swap pending → shipped | S5 | ☐ |

**Sign-off date:** _______________  
**Signer:** _______________
