# PRD: ASAP Protocol v2.5.4 — Distribution Loop

> **Product Requirements Document**
>
> **Version**: 2.5.4
> **Status**: PLANNED (blocked until v2.5.3 Adapter Lab II ships)
> **Created**: 2026-04-28 (as v2.3.3); **renumbered**: 2026-06-22 → v2.5.2; **2026-07-08 → v2.5.4**
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: [prd-v2.5.3-adapter-lab-ii.md](./prd-v2.5.3-adapter-lab-ii.md)
> **Successor**: [prd-v2.5.5-formal-spec-interop.md](./prd-v2.5.5-formal-spec-interop.md)
>
> **Migration note**: Formerly `product/prd/private/prd-v2.3.3-distribution-loop.md` (v2.3.3), then `prd-v2.5.2-distribution-loop.md`. v2.5.2 was reassigned to the security follow-up patch (2026-07-08).

---

## 1. Purpose

v2.5.4 turns adoption work from v2.3.0–v2.5.3 into a **repeatable distribution loop**: homepage, docs routing, templates, and lightweight metrics so developers discover ASAP through executable paths.

---

## 2. Scope

| Area | Requirement |
|------|-------------|
| Homepage | Hero, feature cards, "what's new", CTA for agent-first software |
| Docs routing | Every homepage CTA → GitHub docs or runnable examples |
| Templates | OpenAPI provider, TypeScript consumer, top adapter winner(s) |
| Metrics | Site→docs clicks, npm/PyPI installs, registered agents, guide views |
| Narrative | Public "Build for agents" copy (no private GTM) |

---

## 3. Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| DIST-001 | Update `apps/web` homepage for agent-first software story | MUST |
| DIST-002 | Link homepage sections to concrete GitHub docs/examples | MUST |
| DIST-003 | Starter templates for strongest adoption paths (incl. MCP Auth if v2.5.0 winner) | MUST |
| DIST-004 | Lightweight adoption metrics dashboard | SHOULD |
| DIST-005 | Public "Build for agents" guide | MUST |
| DIST-006 | Keep pricing, paid timing, fundraising private | MUST |

---

## 4. Public narrative (draft)

> The next users of software are agents. ASAP gives them the machine-readable foundation they need: discoverable capabilities, scoped identity, compliance checks, and SDKs that turn existing APIs into agent-ready interfaces.

---

## 5. Success metrics

| Metric | Target |
|--------|--------|
| Homepage CTAs → docs/examples | Present and trackable |
| Starter templates | 3+ |
| Adoption dashboard | Live or documented |

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-08 | Renumbered v2.5.2 → **v2.5.4** (v2.5.2 = security follow-up) |
| 2026-06-22 | Renumbered v2.3.3 → v2.5.2 |
