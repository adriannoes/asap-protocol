# Sprint S1: Workflow → ASAP prototype (v2.5.3)

**PRD**: LAB2-001, LAB2-002  
**Branch**: `feat/v2.5.3-s0-s1-workflow` → **`release/2.5.3`**  
**Depends on**: [S0](./sprint-S0-candidate-lock.md) primary = workflow (default)  
**Status**: Done (2026-07-13)

**Trigger:** S0 locks workflow connector as primary.  
**Enables:** S2 security guide; S3 site links.  
**Depends on:** OpenAPI adapter (`asap.adapters.openapi`) and/or capability grant patterns; examples conventions.

---

## Goal

Ship **one** runnable prototype that turns workflow/automation (or a stand-in workflow HTTP API) into ASAP **capabilities**, with a public integration guide. No protocol changes.

---

## Design constraints

- Prefer composing **OpenAPI Adapter** + manifest skills over inventing a new adapter package
- If a dedicated package is truly needed, put it under `src/asap/adapters/` only with a clear reuse story (LAB2-001)
- Example must run with a single documented command (no secrets required for the happy path; use `.env.example`)
- Do not add public methods to `transport/server.py` or `transport/client.py`

---

## Tasks

- [x] **2.1 Spike shape (≤0.5 day)**
  - [x] Choose concrete target: n8n webhook/API **or** Activepieces-style HTTP workflow **or** local mock workflow OpenAPI that mimics either
  - [x] Map 2–3 workflow actions → capability IDs / skills
  - [x] Write spike notes in PR description or `examples/.../DESIGN.md`

- [x] **2.2 Runnable example**
  - [x] Create `examples/workflow_asap_connector/` (name may be `n8n_asap_connector` if n8n-specific)
  - [x] Include `README.md` with install, run, and “what a remote agent sees”
  - [x] Include minimal OpenAPI (or reuse petstore pattern) if that is the bridge
  - [x] Happy path: list capabilities / invoke one skill without real SaaS credentials (mock server OK)

- [x] **2.3 Integration guide**
  - [x] Add `docs/integrations/workflow-connectors.md` (or `n8n.md`)
  - [x] Cover: capability mapping, discovery (well-known / manifest), failure modes
  - [x] Link OpenAPI adapter docs and Lab I adapters for contrast (framework vs workflow)
  - [x] Leave MkDocs nav + `docs/index.md` wiring to **S3** ([docs-review-checklist.md](./docs-review-checklist.md))

- [x] **2.4 Tests / smoke**
  - [x] Unit or smoke tests for any new Python helpers (≥ existing project standards)
  - [x] Document manual smoke: command + expected output in example README
  - [x] `uv run ruff check` / targeted pytest green on the PR

- [x] **2.5 Compliance where shape permits**
  - [x] If the example agent shape fits, note which Compliance Harness checks apply (SHOULD, not ship-blocker)

---

## Acceptance criteria

- [x] LAB2-002 met: ≥1 enterprise/workflow example converting workflow/API → ASAP capabilities
- [x] LAB2-001 met: reuses existing interfaces; no protocol fork
- [x] Guide published under `docs/integrations/` (MkDocs nav + `docs/index.md` wiring deferred to **S3**)
- [x] Transport growth lint clean for the PR

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-13 | T2 | Approved with caveats | [review-v2.5.3-S0-S1-workflow-20260713-r2.md](../../../code-review/private/review-v2.5.3-S0-S1-workflow-20260713-r2.md) |
| 2026-07-13 | T2 | Rejected | [review-v2.5.3-S0-S1-workflow-20260713.md](../../../code-review/private/review-v2.5.3-S0-S1-workflow-20260713.md) |

## Relevant files

### New

- `examples/workflow_asap_connector/DESIGN.md`
- `examples/workflow_asap_connector/README.md`
- `examples/workflow_asap_connector/openapi-fragment.json`
- `examples/workflow_asap_connector/main.py`
- `examples/workflow_asap_connector/mock_upstream.py`
- `examples/workflow_asap_connector/.env.example`
- `tests/examples/test_workflow_asap_connector.py`
- `docs/integrations/workflow-connectors.md` (Wave 3 / task 2.3)

### Reference

- `examples/openapi_petstore/`
- `docs/adapters/openapi.md`
- `src/asap/adapters/openapi/`
