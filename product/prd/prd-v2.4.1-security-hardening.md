# PRD: ASAP Protocol v2.4.1 — Security Hardening Patch

> **Product Requirements Document**
>
> **Version**: 2.4.1
> **Status**: ✅ **SHIPPED** (2026-06-14)
> **Created**: 2026-06-06
> **Last Updated**: 2026-06-22 (public retrospective; execution in `engineering/tasks/private/v2.4.1/`)

---

## 1. Executive Summary

v2.4.1 was a **defensive patch** — no wire-protocol or manifest schema changes. It shipped OAuth2 `iss`/`aud` validation, fail-closed identity binding, web-app SSRF/redirect hardening, and dependency security bumps already merged on `main` after v2.4.0.

---

## 2. Shipped scope

| Area | Deliverable |
|------|-------------|
| OAuth2 | `validate_jwt()` enforces `iss`/`aud` when `ASAP_AUTH_ISSUER` / `ASAP_AUTH_AUDIENCE` set |
| Identity binding | 403 when `manifest_id` configured but subject unmapped (fail-closed) |
| Web app | Open redirect block, health-check SSRF hardening, Zod strict query params |
| Dependencies | `fastapi>=0.136.1` (PYSEC-2026-161), transitive pin updates per `SECURITY.md` |

---

## 3. Shipped requirements (summary)

| ID group | Status |
|----------|--------|
| SEC-OAUTH-001..004 | ✅ |
| SEC-ID-001..002 | ✅ |
| SEC-WEB-001..005 | ✅ |
| SEC-DEP-001..003 | ✅ |
| REL-001..005 | ✅ |

Full requirement tables: `product/prd/private/prd-v2.4.1-security-hardening.md` (local).

---

## 4. Deferred to v2.5.x

| Item | Target |
|------|--------|
| `extra="forbid"` on ingress models | v2.5.4 (optional patch) |
| Operator API auth (`/usage`, `/sla`, `/audit`) | v2.5.4 |
| Redis-backed `JtiReplayCache` | v2.5.4 |
| MCP Auth Bridge | **v2.5.0** |
| Formal RFC spec | **v2.5.3** |

---

## 5. Related documents

- **CHANGELOG**: [CHANGELOG.md](../../CHANGELOG.md#241---2026-06-14)
- **Migration**: [docs/migration.md](../../docs/migration.md#upgrading-from-v240-to-v241)
- **Predecessor**: [prd-v2.4.0-edge-ai-discovery.md](./prd-v2.4.0-edge-ai-discovery.md)
- **Successor train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
- **Execution**: [`engineering/tasks/private/v2.4.1/tasks-v2.4.1-security-hardening.md`](../../engineering/tasks/private/v2.4.1/tasks-v2.4.1-security-hardening.md)
- **CHANGELOG**: [CHANGELOG.md](../../CHANGELOG.md#241---2026-06-14)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Public retrospective PRD; private PRD remains detailed source |
