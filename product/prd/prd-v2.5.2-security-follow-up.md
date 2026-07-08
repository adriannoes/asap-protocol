# PRD: ASAP Protocol v2.5.2 — Security & Correctness Follow-up

> **Product Requirements Document**
>
> **Version**: 2.5.2
> **Status**: RELEASE PENDING (`release/2.5.2`; tag after merge)
> **Created**: 2026-07-08
> **Parent train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
> **Predecessor**: v2.5.1 code quality patch ([CHANGELOG](../../CHANGELOG.md#251---2026-06-25); execution in `engineering/tasks/private/v2.5.1/`)
> **Successor**: [prd-v2.5.3-adapter-lab-ii.md](./prd-v2.5.3-adapter-lab-ii.md)
>
> **Origin**: Absorbs the former **v2.5.4** optional security slot (v2.4.1 §8 / [#209](https://github.com/adriannoes/asap-protocol/issues/209)) plus v2.5.1 code-review follow-ups (#245–#249) and registry correctness fixes. Consumes the **v2.5.2** version number so Adapter Lab II / Distribution Loop / Formal Spec shift to **v2.5.3–v2.5.5**.

---

## 1. Purpose

v2.5.2 ships the security and correctness work that accumulated on `main` after the v2.5.1 quality patch — without consuming the adoption or standards-track slots.

**Question answered:** can operators harden multi-worker JWT replay, protect operator APIs, and reject unknown ingress fields without waiting for Adapter Lab II?

---

## 2. Scope (shipped on `main`)

### 2.1 Security follow-up from v2.4.1 (#209)

| Area | Deliverable | PR |
|------|-------------|-----|
| Operator API auth | Opt-in `create_app(require_operator_auth=True)` — OAuth2 Bearer + `asap:admin` on `/usage`, `/sla`, `/audit` | [#277](https://github.com/adriannoes/asap-protocol/pull/277) |
| Ingress validation | `TaskRequestConfig` / `CommonMetadata` `extra="forbid"` (**breaking** for clients sending unknown keys) | [#278](https://github.com/adriannoes/asap-protocol/pull/278) |
| Redis JTI replay | Optional `RedisJtiReplayCache` for multi-worker Host/Agent JWT replay protection | [#279](https://github.com/adriannoes/asap-protocol/pull/279) |
| Web rate limits | Optional Upstash Redis / Vercel KV distributed limits in `apps/web` | [#280](https://github.com/adriannoes/asap-protocol/pull/280) |

### 2.2 v2.5.1 code-review follow-ups

| Issue | Deliverable | PR |
|-------|-------------|-----|
| [#245](https://github.com/adriannoes/asap-protocol/issues/245) | Serialize SQLite `execute()` writes with `asyncio.Lock` | [#263](https://github.com/adriannoes/asap-protocol/pull/263) |
| [#246](https://github.com/adriannoes/asap-protocol/issues/246) | Cover `transport_mode="auto"` WS `auth_token` propagation | [#268](https://github.com/adriannoes/asap-protocol/pull/268) |
| [#247](https://github.com/adriannoes/asap-protocol/issues/247) | Bind `correlation_id` on SSE/WebSocket streaming paths | [#265](https://github.com/adriannoes/asap-protocol/pull/265) |
| [#248](https://github.com/adriannoes/asap-protocol/issues/248) | Rewire stale WS unit tests (deleted `handle_message` seam) | [#262](https://github.com/adriannoes/asap-protocol/pull/262) |
| [#249](https://github.com/adriannoes/asap-protocol/issues/249) | JTI replay protection on `GET /asap/agent/status` | [#264](https://github.com/adriannoes/asap-protocol/pull/264) |
| [#243](https://github.com/adriannoes/asap-protocol/issues/243) | Extract `parse_scope` to break middleware import cycle | [#266](https://github.com/adriannoes/asap-protocol/pull/266) |
| [#242](https://github.com/adriannoes/asap-protocol/issues/242) | Move legacy `asap.cli` re-exports to `cli/_compat.py` | [#274](https://github.com/adriannoes/asap-protocol/pull/274) |

### 2.3 Registry correctness

| Deliverable | PR |
|-------------|-----|
| Accept signed manifest envelopes in registration paths | [#224](https://github.com/adriannoes/asap-protocol/pull/224) |
| Map `ManifestValidationError` → HTTP 400 on auto-register | [#227](https://github.com/adriannoes/asap-protocol/pull/227) |

### 2.4 Dependency security

| Deliverable | PR |
|-------------|-----|
| Bump `joserfc`, `python-engineio`, `python-socketio` for `pip-audit` | [#258](https://github.com/adriannoes/asap-protocol/pull/258) |

---

## 3. Non-goals

| Item | Target |
|------|--------|
| Adapter Lab II (enterprise/workflow adapters) | **v2.5.3** |
| Distribution Loop (homepage, templates, metrics) | **v2.5.4** |
| Formal Spec & Interop | **v2.5.5** |
| `@asap-protocol/mcp-auth` HTTP/SSE middleware | npm patch TBD (not this release) |
| Economy / billing | v3.0 |

---

## 4. Breaking changes

| Change | Migration |
|--------|-----------|
| `TaskRequestConfig` / `CommonMetadata` reject unknown fields | [docs/migration.md#upgrading-from-v251](../../docs/migration.md#upgrading-from-v251) — move extensions to `TaskRequest.input` or envelope `extensions` |
| Legacy `from asap.cli import DEFAULT_SCHEMAS_DIR, …` | Import from `asap.cli._compat` or canonical modules (shim removed in v2.6.0 — [#275](https://github.com/adriannoes/asap-protocol/issues/275)) |

Wire protocol and manifest schema are otherwise unchanged.

---

## 5. Success criteria

| Criterion | Status |
|-----------|--------|
| All #209 scope bullets merged | ✅ PRs #277–#280 |
| v2.5.1 follow-ups #245–#249 closed | ✅ |
| CHANGELOG `[2.5.2]` + migration notes | ✅ |
| `pyproject.toml` → `2.5.2`; tag `v2.5.2` | Pending merge + tag |
| Close umbrella [#209](https://github.com/adriannoes/asap-protocol/issues/209) | Pending after tag |

---

## 6. Related documents

- **Train index**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md)
- **Deferred origin**: [prd-v2.4.1-security-hardening.md](./prd-v2.4.1-security-hardening.md) §4
- **Migration**: [docs/migration.md#upgrading-from-v251](../../docs/migration.md#upgrading-from-v251)
- **CHANGELOG**: [CHANGELOG.md](../../CHANGELOG.md) `[Unreleased]` → `[2.5.2]` at ship

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-08 | Created: v2.5.2 absorbs former v2.5.4 security slot + CR/registry follow-ups; adoption PRDs renumbered to v2.5.3–v2.5.5 |
