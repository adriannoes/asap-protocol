# Sprint S0: ShellClaw Marketplace Onboarding

> **Goal:** Answer ShellClaw §5 concrete asks; document static-manifest registration; optional `built_with` enum UX.
> **Parent Roadmap:** [tasks-v2.4.0-roadmap.md](./tasks-v2.4.0-roadmap.md)
> **Context (literals):** [asap-protocol-questions-for-upstream.md](../../../product/prd/private/asap-protocol-questions-for-upstream.md) §3–§6
> **Not a blocker:** ShellClaw v1.0 Wave 6 ships with `tags` workaround per Q-ASAP.

---

## Relevant Files

- `tests/fixtures/registry/shellclaw-v1.0-entry.json` — literal ShellClaw §4 registry entry for validation tests
- `tests/fixtures/registry/shellclaw-v1.0-agents-array.json` — dry-run for `scripts/validate_registry.py`
- `product/prd/private/asap-protocol-questions-for-upstream.md` — status Answered + link to guide (ShellClaw notification)
- `src/asap/discovery/registry.py` — `RegistryEntry`, `online_check`
- `scripts/validate_registry.py` — Lite registry validation
- `scripts/process_registration.py` — IssueOps → `registry.json`
- `src/asap/registry/auto_registration.py` — `POST /registry/agents`
- `src/asap/registry/anti_spam.py` — auto `self-signed` tag
- `src/asap/crypto/trust_levels.py` — `TrustLevel.SELF_SIGNED` = `"self-signed"`
- `.github/ISSUE_TEMPLATE/register_agent.yml` — `built_with`, `category`
- `tests/discovery/test_registry.py` — `test_shellclaw_v1_fixture_validates`, `online_check: false` fixture
- `docs/guides/shellclaw-registry.md` — static manifest + §5 answers for ShellClaw Wave 6
- `docs/index.md` — link to shellclaw-registry guide
- `CHANGELOG.md` — Unreleased ShellClaw marketplace blurb (§6)
- `.github/ISSUE_TEMPLATE/register_agent.yml` — `ShellClaw` in `built_with` dropdown
- `apps/web/src/app/docs/register/page.tsx` — `built_with` options + static manifest note
- `apps/web/src/app/dashboard/register/register-form.tsx` — `ShellClaw` in `BUILT_WITH_OPTIONS`
- `apps/web/src/app/browse/browse-content.tsx` — audited: no `online_check` / reachability on cards (doc § Browse UI)

---

## Locked answers for ShellClaw (publish in docs when S0 ships)

### §5.1 Registry entry validity — **YES, with notes**

The literal entry in the context doc §4 **should pass** `RegistryEntry.model_validate` and `validate_registry.py`:

| Field | Status |
|-------|--------|
| `id` | `urn:asap:agent:shellclaw` — valid URN |
| `category` | `Infrastructure` — canonical enum |
| `tags` | Valid; `self-signed` **must not** be submitted manually — `anti_spam.py` adds it |
| `built_with` | `Other` — valid today |
| `verification` | `null` — valid (`VerificationStatus \| None`) |
| `online_check` | `false` — supported ([`test_registry_entry_accepts_online_check_false`](../../../tests/discovery/test_registry.py)) |
| `endpoints.http` + `endpoints.manifest` | Valid map keys per ADR-15 |

**Action for ShellClaw:** Replace `https://shellclaw.example.com/asap` placeholder before public listing if UI shows “offline”; acceptable for IssueOps with `online_check: false`.

**Auto-registration:** If `POST /registry/agents` is used, compliance harness may fail on **live** reachability — ShellClaw v1.0 should prefer **IssueOps** until v1.0.1 tunnel (per ShellClaw Q-URL).

### §5.2 `built_with` enum — **Optional task below** (cosmetic)

`Other` is sufficient for v1.0. Adding `ShellClaw` improves Browse/filter discoverability.

### §5.3 Trust label — **YES, unchanged**

`trust_level: "self-signed"` (hyphen) remains the correct `TrustLevel` value. Signed manifest `signature.trust_level` matches `SignatureBlock` schema.

### §5.4 Static manifest hosting — **YES**

`online_check: false` skips reachability pings. Browse lists agents normally (no Offline badge on cards); detail/dashboard show **Demo** — **not a rejection**. Wave 6 marketplace registration does **not** require a live `POST /asap` endpoint in v1.0.

### §5.5 Manifest URL path — **YES**

Static hosting at `https://adriannoes.github.io/shellclaw/manifest.json` (no `.well-known` on GitHub Pages) is acceptable for `endpoints.manifest` in `registry.json`. The `.well-known/asap/` convention applies on the **agent's own domain** when live; not required on third-party static hosts.

---

## Trigger / Enables / Depends on

**Trigger:** ShellClaw Phase 5 Wave 6 (marketplace registration) approaching.

**Enables:** Confident IssueOps PR; no upstream schema work required for v1.0 listing.

**Depends on:** Existing v2.3 Lite Registry + Issue template (E4 shipped).

---

## Acceptance Criteria

- [x] Context doc §4 registry JSON validates: `uv run python scripts/validate_registry.py` (fixture or dry-run entry)
- [x] Maintainer guide documents static manifest + `online_check: false` + manifest URL conventions
- [x] Issue template optionally lists `ShellClaw` under `built_with`
- [x] ShellClaw notified (issue comment or doc link) with §5.1–§5.5 answers

---

## Task 0.1: Validate ShellClaw registry fixture

- [x] **0.1.1** Add `tests/fixtures/registry/shellclaw-v1.0-entry.json`
  - **What:** Copy literal JSON from context doc §4 (update manifest URL if final path differs).
  - **Verify:** `RegistryEntry.model_validate(json.load(...))` passes in `tests/discovery/test_registry.py`.

- [x] **0.1.2** Add test `test_shellclaw_v1_fixture_validates`
  - **File:** `tests/discovery/test_registry.py`
  - **Verify:** `pytest tests/discovery/test_registry.py -k shellclaw` green.

---

## Task 0.2: Document static-manifest registration

- [x] **0.2.1** Create `docs/guides/shellclaw-registry.md` (or section in `docs/guides/registry-verification-review.md`)
  - **What:** Document:
    - `online_check: false` for GitHub Pages–only manifests
    - Acceptable `endpoints.manifest` on `*.github.io` without `.well-known`
    - Placeholder `endpoints.http` until live tunnel
    - Do not put `self-signed` in `tags` (auto-added)
    - IssueOps vs auto-registration for static-only agents
  - **Verify:** Doc review; link from `docs/index.md`.

- [x] **0.2.2** Add ShellClaw changelog blurb (context doc §6) to `CHANGELOG.md` under Unreleased when listing merges

---

## Task 0.3: Optional — `built_with: ShellClaw`

- [x] **0.3.1** Add `ShellClaw` to register_agent.yml dropdown
  - **File:** `.github/ISSUE_TEMPLATE/register_agent.yml`
  - **What:** Insert after `OpenClaw` or before `Other`. Mirror in `process_registration.py` if enum validation exists (free string today — verify).
  - **Verify:** Manual: template shows new option.

- [x] **0.3.2** Document in register docs page (`apps/web/src/app/docs/register/`) if framework list is duplicated in UI copy

---

## Task 0.4: Browse UX spot-check (static agents)

- [x] **0.4.1** Manual: seed agent with `online_check: false` — confirm Browse does not hard-fail; note any “offline” badge behavior in doc §5.4
  - **File:** `apps/web/src/app/browse/browse-content.tsx` (read-only audit)
  - **Verify:** Record behavior in `docs/guides/shellclaw-registry.md`.

---

## Definition of Done

- [x] ShellClaw §5 answers published in-repo (this sprint + [guide](../../../docs/guides/shellclaw-registry.md) + context doc status)
- [x] Fixture test green (`pytest -k shellclaw`; `validate_registry.py` on `shellclaw-v1.0-agents-array.json`)
- [x] ShellClaw Wave 6.2 unblocked for IssueOps path (handoff block in guide; no schema changes; `built_with` + `online_check: false` documented)
