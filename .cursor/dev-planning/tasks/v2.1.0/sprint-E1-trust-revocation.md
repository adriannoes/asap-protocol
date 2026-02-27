# Sprint E1: Trust & Revocation Foundation

> **Goal**: Trust validation wrapper, revoked_agents.json, IssueOps revoke flow
> **Prerequisite**: v2.0.0; existing `asap.crypto.trust`, `SignatureVerificationError`
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)
> **Estimated Duration**: 4–5 days

---

## Relevant Files

- `src/asap/client/__init__.py` — Client package init
- `src/asap/client/trust.py` — verify_agent_trust, ASAP_CA_PUBLIC_KEY_B64
- `src/asap/client/revocation.py` — is_revoked, RevokedAgentsList
- `src/asap/errors.py` — AgentRevokedException
- `revoked_agents.json` — Revocation list (repo root)
- `.github/ISSUE_TEMPLATE/revoke_agent.yml` — Revoke form
- `.github/workflows/revoke-agent.yml` — IssueOps flow
- `scripts/validate_revoked.py` — Validate revoked_agents.json schema
- `scripts/process_revocation.py` — Parse revoke issues
- `tests/client/__init__.py` — Client test package
- `tests/client/test_trust.py`, `tests/client/test_revocation.py`
- `tests/scripts/test_process_revocation.py`

---

## Trigger / Enables / Depends on

**Trigger:** Consumer SDK (Sprint E2) needs trust validation and revocation check before returning agents.

**Enables:** Sprint E2 (Consumer SDK Core) can validate manifests and reject revoked agents; Sprint E4.6 (Revoked badge) needs revoked_agents.json.

**Depends on:** Existing `asap.crypto.trust.verify_ca_signature`, `asap.errors.SignatureVerificationError`, `tests/fixtures/asap_ca/` for CA key.

---

## Acceptance Criteria

- [x] `asap.client.trust.verify_agent_trust(signed_manifest)` validates Ed25519 using embedded ASAP CA key; raises `SignatureVerificationError` on invalid
- [x] `revoked_agents.json` exists at repo root with schema `{ "revoked": [{ "urn": str, "reason": str, "revoked_at": str }] }`
- [x] IssueOps flow: issue with label `revoke-agent` triggers Action that appends to `revoked_agents.json`
- [x] `asap.client.revocation.is_revoked(urn)` fetches `revoked_agents.json` (no cache) and returns True if URN in list

---

## Task 1.1: Create trust module for SDK

- [x] **1.1.1** Create trust.py with CA key embedding
  - **File**: `src/asap/client/trust.py` (create new)
  - **What**: Create module with embedded ASAP CA public key (base64). Use `tests/fixtures/asap_ca/ca_public_b64.txt` or env `ASAP_CA_PUBLIC_KEY` for override. Import `verify_ca_signature`, `SignedManifest`, `SignatureVerificationError` from crypto.
  - **Why**: SEC-003 — SDK embeds CA key locally (no network call).
  - **Pattern**: `src/asap/crypto/trust.py`; `verify_ca_signature(known_cas=[...])`.
  - **Verify**: Module imports; CA key constant defined.

- [x] **1.1.2** Implement verify_agent_trust
  - **File**: `src/asap/client/trust.py`
  - **What**: Implement `verify_agent_trust(signed_manifest: SignedManifest) -> bool` that calls `verify_ca_signature(signed_manifest, known_cas=[ASAP_CA_B64])`. Re-raise `SignatureVerificationError` from crypto.
  - **Why**: SEC-001, SEC-002 — validate Ed25519; invalid raises.
  - **Verify**: `pytest tests/client/test_trust.py -k "verify_agent_trust"` passes; invalid manifest raises.

- [x] **1.1.3** Write tests for trust module
  - **File**: `tests/client/test_trust.py` (create new)
  - **What**: Test valid Verified manifest passes; invalid/self-signed raises `SignatureVerificationError`; missing public_key raises.
  - **Verify**: `pytest tests/client/test_trust.py -v` passes.

---

## Task 1.2: Create revocation module

- [x] **1.2.1** Add AgentRevokedException and RevokedAgentsList model
  - **File**: `src/asap/errors.py` (modify), `src/asap/client/revocation.py` (create new)
  - **What**: Add `AgentRevokedException(ASAPError)` in errors.py. In revocation.py, add Pydantic model `RevokedAgentsList` with `revoked: list[RevokedEntry]`, `version: str`. `RevokedEntry`: `urn`, `reason`, `revoked_at`.
  - **Why**: Schema for revoked list; SDK raises on revoked.
  - **Verify**: `AgentRevokedException` importable; `RevokedAgentsList.model_validate_json(...)` parses valid JSON.

- [x] **1.2.2** Implement is_revoked
  - **File**: `src/asap/client/revocation.py`
  - **What**: Implement `async is_revoked(urn: str, revoked_url: str | None = None) -> bool`. Fetch from `revoked_url` or `ASAP_REVOKED_AGENTS_URL` (default GitHub raw). Parse with `RevokedAgentsList`; return True if URN in list. No caching.
  - **Why**: SEC-004, REV-003 — SDK checks before run().
  - **Pattern**: httpx.AsyncClient; `response.json()` → `RevokedAgentsList.model_validate`.
  - **Verify**: `pytest tests/client/test_revocation.py` — mock HTTP; `is_revoked(urn)` returns True when in list.

- [x] **1.2.3** Write tests for revocation module
  - **File**: `tests/client/test_revocation.py` (create new)
  - **What**: Test empty list returns False; URN in list returns True; HTTP error handling; invalid JSON handling.
  - **Verify**: `pytest tests/client/test_revocation.py -v` passes.

---

## Task 1.3: Define revoked_agents.json schema and create file

- [x] **1.3.1** Create revoked_agents.json at repo root
  - **File**: `revoked_agents.json` (create new)
  - **What**: Create file with `{ "revoked": [], "version": "1.0" }`. Valid JSON, parseable by `RevokedAgentsList`.
  - **Why**: REV-001 — canonical revocation list.
  - **Verify**: `python -c "import json; json.load(open('revoked_agents.json'))"` succeeds.

- [x] **1.3.2** Add validate_revoked script (optional)
  - **File**: `scripts/validate_revoked.py` (create new) or extend `scripts/validate_registry.py`
  - **What**: Script that validates `revoked_agents.json` against `RevokedAgentsList` schema. Exit 0 if valid, 1 otherwise.
  - **Why**: CI guardrail for manual edits.
  - **Verify**: `uv run python scripts/validate_revoked.py revoked_agents.json` exits 0.

---

## Task 1.4: Create revoke-agent IssueOps flow

- [x] **1.4.1** Create revoke_agent.yml issue template
  - **File**: `.github/ISSUE_TEMPLATE/revoke_agent.yml` (create new)
  - **What**: Form with fields: agent URN (required), reason (required). Label `revoke-agent`. Follow `remove_agent.yml` structure.
  - **Why**: REV-002 — user submits revoke request.
  - **Pattern**: `.github/ISSUE_TEMPLATE/remove_agent.yml`.
  - **Verify**: Manual: create issue from template; fields and label present.

- [x] **1.4.2** Create process_revocation.py script
  - **File**: `scripts/process_revocation.py` (create new)
  - **What**: Parse issue body (### headers), extract URN and reason. Validate URN exists in registry.json. Load revoked_agents.json, append new entry, save. Write result.json (valid/errors). Use `lib/registry_io`, `lib/debug_id`.
  - **Why**: REV-002 — script does the work.
  - **Pattern**: `scripts/process_removal.py`; `_HEADER_TO_FIELD` mapping; `load_registry`, `save_registry`.
  - **Verify**: `pytest tests/scripts/test_process_revocation.py` passes.

- [x] **1.4.3** Create revoke-agent.yml workflow
  - **File**: `.github/workflows/revoke-agent.yml` (create new)
  - **What**: Trigger on `issues` with label `revoke-agent`. Steps: checkout, setup Python, run process_revocation.py, create PR (git add revoked_agents.json), comment on success/failure. Concurrency group `register-agent`.
  - **Why**: REV-002 — IssueOps automation.
  - **Pattern**: `.github/workflows/remove-agent.yml`; replace `registry.json` with `revoked_agents.json`.
  - **Verify**: Manual: open issue with revoke-agent label; workflow runs; PR created.

- [x] **1.4.4** Write tests for process_revocation
  - **File**: `tests/scripts/test_process_revocation.py` (create new)
  - **What**: Test parse URN/reason from body; URN not in registry fails; valid flow appends to revoked_agents.json; result.json written.
  - **Verify**: `pytest tests/scripts/test_process_revocation.py -v` passes.

---

## Task 1.5: Wire revocation into client package

- [x] **1.5.1** Create client __init__ and exports
  - **File**: `src/asap/client/__init__.py` (create new)
  - **What**: Export `verify_agent_trust`, `is_revoked`, `AgentRevokedException`, `SignatureVerificationError`. Add `asap.client` to `asap/__init__.py` if needed.
  - **Why**: Clean public API for SDK.
  - **Verify**: `from asap.client import verify_agent_trust, is_revoked` works; `pytest tests/client/` passes.

---

## Definition of Done

- [x] `verify_agent_trust` validates manifests; invalid raises `SignatureVerificationError`
- [x] `is_revoked` fetches revoked_agents.json (no cache); returns True when URN in list
- [x] IssueOps revoke flow creates PR updating revoked_agents.json
- [x] All tests pass: `PYTHONPATH=src uv run pytest tests/client/ tests/scripts/test_process_revocation.py -v`
