# PRD: ASAP Protocol v2.2.1 — Patch & Carry-over

> **Product Requirements Document**
>
> **Version**: 2.2.1
> **Status**: DRAFT
> **Created**: 2026-04-17
> **Last Updated**: 2026-04-17
> **Predecessor**: [prd-v2.2-protocol-hardening.md](./prd-v2.2-protocol-hardening.md) (✅ shipped 2026-04-15)
> **Successor**: [prd-v2.3-scale.md](./prd-v2.3-scale.md) — Adoption Multiplier

---

## 1. Executive Summary

### 1.1 Purpose

v2.2.1 is a **small, defensive patch release** that closes the carry-over backlog identified in the v2.2.0 delivery audit (2026-04-17). It does not introduce new protocol surface area. Three items remain from v2.2.0:

- **SELF-002 (SHOULD)**: `WebAuthnVerifier` is a Protocol with a placeholder `True` implementation. Real biometric/hardware proof-of-presence is missing.
- **COMP-006 (COULD)**: `asap compliance-check --url ...` CLI subcommand was specified but not exposed in `src/asap/cli.py`.
- **AUD-005 (COULD)**: Audit log export is reachable via `GET /audit` JSON, but no CLI subcommand was shipped.

Plus security/maintenance:

- Routine dependency CVE sweeps (continuation of pip-audit/Dependabot triage).
- Documentation polish exposed by v2.2.0 release (link rot, examples drift).

> [!NOTE]
> **Scope discipline**: Anything that requires new protocol features, new endpoints, or new data models belongs in v2.3, not here. v2.2.1 is **strictly a carry-over patch**.

### 1.2 Strategic Context

Releasing v2.2.1 quickly (1–2 weeks) frees v2.3 to focus on the **Adoption Multiplier** scope (OpenAPI Adapter, TypeScript SDK, Auto-Registration) without dragging the carry-over.

| Layer | v2.2.1 Investment |
|-------|------------------|
| Identity & Auth | Finish WebAuthn (SELF-002) |
| Tooling/DX | CLI commands (COMP-006, AUD-005) |
| Security | Dependency hygiene |
| Protocol | **No changes** (additive-only minor patch) |

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| WebAuthn real | High-risk capability registration validates real WebAuthn assertions (no placeholder) | P0 |
| Compliance CLI | `asap compliance-check --url <agent>` returns Compliance Harness v2 report | P1 |
| Audit export CLI | `asap audit export --since ... --until ... --format {json,csv}` exports tamper-evident chain | P1 |
| Dependency hygiene | `pip-audit` clean on `main`; `npm audit` clean on `apps/web` | P2 |

---

## 3. User Stories

### Security Engineer (WebAuthn)
> As a **security engineer**, I want **agents controlling the browser to require a real WebAuthn ceremony** (FIDO2 attestation, `userVerification: required`) **so that** an agent cannot silently approve its own capability requests.

### Compliance Operator (CLI)
> As a **compliance operator**, I want to run `asap compliance-check --url https://agent.example.com` **so that** I can validate any third-party agent against the v2.2 spec from CI without writing Python.

### Enterprise Auditor (Audit Export)
> As an **enterprise auditor**, I want to run `asap audit export --since 2026-04-01 --format csv > audit.csv` **so that** I can hand the tamper-evident log to my auditors without manually paginating `GET /audit`.

---

## 4. Functional Requirements

### 4.1 Real WebAuthn Verification (P0)

Replaces the placeholder `WebAuthnVerifier` with a concrete implementation backed by `webauthn` (or `fido2`).

| ID | Requirement | Priority |
|----|-------------|----------|
| WAUTH-001 | New optional dependency `asap-protocol[webauthn]` installs `webauthn>=2.6` | MUST |
| WAUTH-002 | `WebAuthnVerifierImpl` class implementing `WebAuthnVerifier` Protocol with real assertion verification | MUST |
| WAUTH-003 | Registration ceremony helper: `start_webauthn_registration(host_id) -> challenge`, `finish_webauthn_registration(host_id, attestation)` | MUST |
| WAUTH-004 | Authentication ceremony helper: `start_webauthn_assertion(host_id) -> challenge`, `finish_webauthn_assertion(host_id, assertion) -> bool` | MUST |
| WAUTH-005 | Persistent storage Protocol `WebAuthnCredentialStore` (in-memory + SQLite implementations) | MUST |
| WAUTH-006 | `userVerification: "required"` enforced for capability approval flows when `agent_controls_browser=True` | MUST |
| WAUTH-007 | Documented threat model update in `docs/security/self-authorization-prevention.md` (section "Real WebAuthn") | MUST |
| WAUTH-008 | Migration note in `docs/migration.md` from placeholder Protocol to real verifier (zero-config when `[webauthn]` extra is not installed: behavior unchanged) | MUST |

### 4.2 Compliance Harness CLI (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| CLI-COMP-001 | `asap compliance-check --url <agent-url>` runs Compliance Harness v2 against a remote agent | MUST |
| CLI-COMP-002 | Flags: `--output {text,json}`, `--exit-on-fail`, `--timeout`, `--asap-version` | MUST |
| CLI-COMP-003 | Exit code: 0 if score == 1.0, 1 if any check fails (when `--exit-on-fail`), 2 if transport error | MUST |
| CLI-COMP-004 | Subcommand registered in `src/asap/cli.py`; documented in `docs/cli.md` | MUST |
| CLI-COMP-005 | Example usage in CI (`docs/ci-compliance.md`) | SHOULD |

### 4.3 Audit Export CLI (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| CLI-AUD-001 | `asap audit export --store {sqlite,memory} --db <path>` selects audit backend | MUST |
| CLI-AUD-002 | Filters: `--since`, `--until`, `--urn`, `--limit` | MUST |
| CLI-AUD-003 | `--format {json,csv,jsonl}` output formats | MUST |
| CLI-AUD-004 | `--verify-chain` flag re-runs `verify_chain` and exits non-zero on mismatch | MUST |
| CLI-AUD-005 | Documented in `docs/cli.md` and `docs/audit.md` | MUST |

### 4.4 Maintenance & Docs (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| MAINT-001 | `pip-audit` and `npm audit` clean (or documented overrides) | MUST |
| MAINT-002 | Update README/CHANGELOG/migration to reflect v2.2.1 contents | MUST |
| MAINT-003 | Re-run Compliance Harness v2 against `apps/example-agent` and pin baseline | SHOULD |
| MAINT-004 | Refresh `docs/error-codes.md` if any code added/changed | SHOULD |

---

## 5. Non-Goals

| Feature | Reason | When |
|---------|--------|------|
| OpenAPI Adapter | New protocol-adjacent surface | **v2.3** (Adoption Multiplier) |
| TypeScript SDK | Major new package | **v2.3** |
| Auto-Registration | New endpoint + flow | **v2.3** |
| Registry API Backend | Trigger not met (120/500 agents) | v2.3+ (gated by trigger) |
| Intent-Based Search | Same | v2.3+ |
| Orchestration Primitives | Major new model | v2.3+ |

---

## 6. Technical Considerations

### 6.1 Backward Compatibility

- All changes are **additive** or behind opt-in extras (`pip install asap-protocol[webauthn]`).
- Default behavior unchanged when `[webauthn]` extra is not installed (`WebAuthnVerifier` Protocol still resolves to placeholder for environments that opt out).
- Wire protocol version remains `2.2`.

### 6.2 Testing

- Per `user_rule`: tests written first (TDD).
- Unit + integration coverage for `WebAuthnVerifierImpl` using `webauthn` test vectors.
- CLI commands covered via `click.testing.CliRunner`.
- Compliance Harness v2 baseline pinned for `example-agent`.

### 6.3 Release Process

- Conventional commits, atomic PRs (≤300 lines / ≤10 files each), prior approval for any larger PR.
- Bump `pyproject.toml` to `2.2.1`, update `CHANGELOG.md` `[Unreleased]` → `[2.2.1]`.
- Tag `v2.2.1` after CI green; publish to PyPI; rebuild Docker `:v2.2.1` and `:latest`.

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| WebAuthn real implementation | `WebAuthnVerifierImpl` validates real assertions in tests + example app |
| `asap compliance-check` CLI | Available + documented + used by `apps/example-agent` CI |
| `asap audit export` CLI | Available + documented + verified hash chain export |
| Dependency CVEs | 0 unresolved on release day |

---

## 8. Prerequisites

| Prerequisite | Source |
|-------------|--------|
| v2.2.0 released and stable | ✅ 2026-04-15 |
| No active security incident | continuous |

---

## 9. Related Documents

- **Predecessor**: [prd-v2.2-protocol-hardening.md](./prd-v2.2-protocol-hardening.md)
- **Successor**: [prd-v2.3-scale.md](./prd-v2.3-scale.md) (Adoption Multiplier)
- **Self-Auth Threat Model**: [docs/security/self-authorization-prevention.md](../../../docs/security/self-authorization-prevention.md)
- **Compliance Harness v2**: `src/asap/testing/compliance.py`
- **Audit Store**: `src/asap/economics/audit.py`

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-04-17 | 0.1.0 | Initial DRAFT — captures carry-over from v2.2.0 audit (SELF-002, COMP-006, AUD-005) plus dependency hygiene. Strict patch scope. |
