# Sprint S1: Workflow → ASAP prototype (v2.5.3)

**PRD**: LAB2-001, LAB2-002  
**Branch**: `feat/v2.5.3-s1-workflow` → **`release/2.5.3`**  
**Depends on**: [S0](./sprint-S0-candidate-lock.md) primary = workflow (default)

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

- [ ] **2.1 Spike shape (≤0.5 day)**
  - [ ] Choose concrete target: n8n webhook/API **or** Activepieces-style HTTP workflow **or** local mock workflow OpenAPI that mimics either
  - [ ] Map 2–3 workflow actions → capability IDs / skills
  - [ ] Write spike notes in PR description or `examples/.../DESIGN.md`

- [ ] **2.2 Runnable example**
  - [ ] Create `examples/workflow_asap_connector/` (name may be `n8n_asap_connector` if n8n-specific)
  - [ ] Include `README.md` with install, run, and “what a remote agent sees”
  - [ ] Include minimal OpenAPI (or reuse petstore pattern) if that is the bridge
  - [ ] Happy path: list capabilities / invoke one skill without real SaaS credentials (mock server OK)

- [ ] **2.3 Integration guide**
  - [ ] Add `docs/integrations/workflow-connectors.md` (or `n8n.md`)
  - [ ] Cover: capability mapping, discovery (well-known / manifest), failure modes
  - [ ] Link OpenAPI adapter docs and Lab I adapters for contrast (framework vs workflow)
  - [ ] Leave MkDocs nav + `docs/index.md` wiring to **S3** ([docs-review-checklist.md](./docs-review-checklist.md))

- [ ] **2.4 Tests / smoke**
  - [ ] Unit or smoke tests for any new Python helpers (≥ existing project standards)
  - [ ] Document manual smoke: command + expected output in example README
  - [ ] `uv run ruff check` / targeted pytest green on the PR

- [ ] **2.5 Compliance where shape permits**
  - [ ] If the example agent shape fits, note which Compliance Harness checks apply (SHOULD, not ship-blocker)

---

## Acceptance criteria

- [ ] LAB2-002 met: ≥1 enterprise/workflow example converting workflow/API → ASAP capabilities
- [ ] LAB2-001 met: reuses existing interfaces; no protocol fork
- [ ] Guide linked from docs index (final index + MkDocs nav wiring finishes in **S3**)
- [ ] Transport growth lint clean for the PR

## Relevant files

### New

- `examples/workflow_asap_connector/` (or renamed)
- `docs/integrations/workflow-connectors.md`

### Reference

- `examples/openapi_petstore/`
- `docs/adapters/openapi.md`
- `src/asap/adapters/openapi/`
