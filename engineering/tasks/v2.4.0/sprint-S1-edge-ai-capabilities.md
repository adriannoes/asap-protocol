# Sprint S1: Edge-AI & Hardware Capability Advertising (v2.4)

> **Goal:** Optional `manifest.capabilities.hardware` + `inference`; mirror to `RegistryEntry`; marketplace filters; `find_by_*` discovery helpers.
> **Parent Roadmap:** [tasks-v2.4.0-roadmap.md](./tasks-v2.4.0-roadmap.md)
> **Proposal:** [asap-protocol-edge-ai-capabilities.md](../../../product/prd/private/asap-protocol-edge-ai-capabilities.md)
> **Consumer literals:** [asap-protocol-questions-for-upstream.md](../../../product/prd/private/asap-protocol-questions-for-upstream.md) §3, §4, §7.12
> **Prerequisite:** S0 optional (parallel OK); design lock in roadmap T0 table
> **Branch suggestion:** `feat/edge-ai-capabilities`

---

## Relevant Files

### Schema & models
- `schemas/entities/manifest.schema.json` — `Capability` + `HardwareCapability`, `InferenceCapability`, `LocalModelInfo` ($defs)
- `schemas/examples/shellclaw-jetson-capabilities.json` — Jetson `capabilities` example snippet
- `tests/contract/test_schema_evolution.py` — backward compat + ShellClaw Jetson/RPi schema tests
- `src/asap/models/entities.py` — `Capability`, `HardwareCapability`, `InferenceCapability`, `LocalModelInfo` (Task 1.1)
- `src/asap/models/enums.py` — `HardwareClass`, `HardwareIoType`, `InferenceMode` (Task 1.1)
- `tests/models/test_entities.py` — ShellClaw Jetson/RPi capability round-trip tests (Task 1.1)

### Registry & registration
- `src/asap/discovery/registry.py` — `RegistryEntry`, `derive_registry_hardware_fields`, `generate_registry_entry`, `find_by_*` (Tasks 1.2–1.3)
- `tests/discovery/test_registry.py` — hardware `find_by_*` filters + multi-agent fixture (Task 1.3)
- `src/asap/registry/auto_registration.py` — entry built via `generate_registry_entry` (hardware mirror, Task 1.2.3)
- `scripts/process_registration.py` — `derive_registry_hardware_fields` on IssueOps manifest fetch (Task 1.2.4)
- `tests/discovery/test_registry.py` — `RegistryEntry` hardware fields + derivation unit tests (Task 1.2)
- `tests/scripts/test_process_registration.py` — derived fields on successful registration (Task 1.2.4)
- `tests/registry/test_auto_registration.py` — PR entry hardware mirror (Task 1.2.3)
- `scripts/validate_registry.py`
- `registry.json` — example entries

### Web
- `apps/web/src/lib/registry-schema.ts` — Zod optional `hardware_class`, `inference_modes`, `hardware_io` (Task 1.4.1)
- `apps/web/src/types/registry.d.ts` — mirror types on `RegistryAgent` (Task 1.4.1)
- `apps/web/src/lib/hardware-labels.ts` — enum label formatter for filters/detail (Task 1.4)
- `apps/web/src/app/browse/browse-content.tsx` — Edge & Hardware sidebar filters (Task 1.4.2)
- `apps/web/src/app/browse/__tests__/browse-content.test.tsx` — hardware filter tests (Task 1.4.2)
- `apps/web/src/app/agents/[id]/agent-detail-client.tsx` — hardware + inference blocks (Task 1.4.3)
- `apps/web/src/app/docs/register/page.tsx` — optional `hardware` / `inference` manifest docs (Task 1.5.1)
- `docs/transport.md` — closed enums + tag migration (Task 1.5.2)
- `docs/registry/auto-registration.md` — derived registry fields note (Task 1.5.2)
- `.github/ISSUE_TEMPLATE/register_agent.yml` — manifest-derived hardware note (Task 1.5.3)

### Tests
- `tests/discovery/test_registry.py`
- `tests/models/test_entities.py` (or equivalent)
- `tests/fixtures/registry/shellclaw-v1.0-entry.json` — derived `hardware_class`, `inference_modes`, `hardware_io` (Task 1.6)
- `tests/fixtures/manifests/shellclaw-jetson-v1.0.json`, `shellclaw-rpi-v1.1.json` (Task 1.6)
- `docs/examples/registry-shellclaw.md` — Jetson registry example (not in live `registry.json`)

### TypeScript SDK (if in scope for v2.4)
- `packages/typescript/client/src/discovery.ts` — `RegistryEntry` hardware fields + parsers (Task 1.7.1)
- `packages/typescript/client/test/discovery.test.ts` — hardware field parse tests (Task 1.7.1)

---

## Canonical ShellClaw values (for tests & docs)

### Jetson v1.0 — `capabilities` extensions (when S1 merged)

```json
"hardware": {
  "class": "edge_accelerator",
  "model": "jetson_orin_nano_super_8gb",
  "io": ["gpio", "i2c"]
},
"inference": {
  "modes": ["cloud", "local_cuda"],
  "local_models": [
    {
      "id": "Phi-3-mini-4k-instruct-Q4_K_M",
      "quantization": "Q4_K_M"
    }
  ]
}
```

- **Skills v1.0 (manifest + registry):** `assistant`, `edge_briefing`, `server_admin`, `gpio_control` — **not** `sensor_read` / `camera_capture` until ShellClaw v1.2.
- **`asap_version`:** `2.1.0` (agent honest claim; separate from PyPI `2.4.0` spec package).
- **Throughput:** omit until ShellClaw Wave 8 benchmarks; then optional self-reported field.

### RPi v1.1 — docs-only example (§7.12 context doc)

- `hardware.class`: `sbc`
- `hardware.model`: `raspberry_pi_zero_2w`
- `hardware.io`: `["gpio", "i2c"]`
- `inference.modes`: `["cloud", "local_cpu"]`
- `local_models[0].id`: `tinyllama-1.1b-chat-Q4_K_M` (no throughput required)

### Registry mirror (derived at registration)

| Manifest source | `RegistryEntry` field |
|-----------------|----------------------|
| `capabilities.hardware.class` | `hardware_class` |
| `capabilities.inference.modes` | `inference_modes` |
| `capabilities.hardware.io` | `hardware_io` (optional v2.4 — multi-select filter) |

Do **not** require registrants to duplicate these in IssueOps body when manifest URL is provided.

---

## Trigger / Enables / Depends on

**Trigger:** Edge / hardware agents cannot be discovered beyond free-form `tags`.

**Enables:** ShellClaw v1.0.1+ structured listing; orchestrators filter by CUDA / GPIO; future agent mesh routing.

**Depends on:** Existing `Capability` model; E4 category/tags (shipped v2.1).

---

## Acceptance Criteria

- [x] `manifest.schema.json` validates optional `hardware` + `inference`; existing manifests unchanged
- [x] Pydantic `Capability` round-trips ShellClaw Jetson + RPi fixtures
- [x] `RegistryEntry` accepts optional `hardware_class`, `inference_modes`, `hardware_io`
- [x] `process_registration` / `auto_registration` populate derived fields from signed manifest when present
- [x] Browse filters: hardware class, inference mode, I/O (multi-select)
- [x] `find_by_hardware_class`, `find_by_inference_mode`, `find_by_io` implemented with tests
- [x] Docs + register page mention new optional manifest fields
- [x] Example in `registry.json` or `docs/examples/` (Jetson structured entry)

---

## Task 1.0: JSON Schema — `hardware` + `inference`

- [x] **1.0.1** Extend `Capability` in `schemas/entities/manifest.schema.json`
  - **What:** Add optional `hardware` and `inference` objects per proposal §7.3–7.4 (`additionalProperties: false`, closed enums).
  - **Why:** Source of truth for compliance + non-Python agents.
  - **Verify:** `asap-compliance` or schema test loads existing manifest fixtures without mutation.

- [x] **1.0.2** Add JSON Schema examples under `schemas/examples/` (optional)
  - **What:** `shellclaw-jetson-capabilities.json` snippet.
  - **Verify:** AJV / `jsonschema` validation in CI if present.

---

## Task 1.1: Pydantic models

- [x] **1.1.1** Add submodels in `src/asap/models/entities.py`
  - **What:**
    - `HardwareCapability` — `class`, `model`, `io` (all optional per ShellClaw hard-rejects on *required*)
    - `InferenceCapability` — `modes`, `local_models`
    - `LocalModelInfo` — `id`, `quantization`, `throughput_tokens_per_second` (optional `float`)
  - **Pattern:** `ConfigDict(extra="forbid")` on nested models.
  - **Verify:** `Capability.model_validate` with ShellClaw Jetson fixture; without new fields still passes.

- [x] **1.1.2** Wire into `Capability` model
  - **What:** `hardware: HardwareCapability | None = None`, `inference: InferenceCapability | None = None`.
  - **Verify:** `tests/models/` — backward compat + new fields.

**Task 1.1 complete** (Pydantic models + tests).

---

## Task 1.2: RegistryEntry mirror + derivation

- [x] **1.2.1** Extend `RegistryEntry` in `src/asap/discovery/registry.py`
  - **What:**
    ```python
    hardware_class: str | None = None
    inference_modes: list[str] = Field(default_factory=list)
    hardware_io: list[str] = Field(default_factory=list)
    ```
  - **Verify:** `RegistryEntry.model_validate` with derived fields only.

- [x] **1.2.2** Add `derive_registry_hardware_fields(manifest: Manifest) -> dict[str, Any]`
  - **What:** Extract from `manifest.capabilities.hardware` / `.inference`; return kwargs for `RegistryEntry`.
  - **Verify:** Unit test Jetson manifest → `edge_accelerator`, `["cloud","local_cuda"]`, `["gpio","i2c"]`.

- [x] **1.2.3** Integrate into `src/asap/registry/auto_registration.py`
  - **What:** After manifest fetch/validate, merge derived fields into entry before bot PR.
  - **Verify:** Integration test or unit mock — entry JSON includes derived fields.

- [x] **1.2.4** Integrate into `scripts/process_registration.py` (if manifest URL fetched)
  - **What:** When registration flow loads manifest, call derivation helper.
  - **Verify:** `tests/scripts/test_process_registration.py` — extended fixture.

**Task 1.2 complete** (RegistryEntry mirror + derivation + registration integration).

---

## Task 1.3: Discovery helpers

- [x] **1.3.1** Implement filters in `src/asap/discovery/registry.py`
  - **What:**
    - `find_by_hardware_class(registry, cls: str) -> list[RegistryEntry]`
    - `find_by_inference_mode(registry, mode: str) -> list[RegistryEntry]`
    - `find_by_io(registry, io_type: str) -> list[RegistryEntry]`
  - **Pattern:** Mirror `find_by_skill()`.
  - **Verify:** `tests/discovery/test_registry.py` — multi-agent fixture.

- [x] **1.3.2** Export from `src/asap/discovery/__init__.py` if public API — N/A (`find_by_skill` not re-exported; same for hardware helpers)

---

## Task 1.4: Web marketplace filters

- [x] **1.4.1** Zod + types
  - **Files:** `apps/web/src/lib/registry-schema.ts`, `apps/web/src/types/registry.d.ts`
  - **What:** Optional `hardware_class`, `inference_modes`, `hardware_io`.
  - **Verify:** `npm run build` in `apps/web`.

- [x] **1.4.2** Browse sidebar filters
  - **File:** `apps/web/src/app/browse/browse-content.tsx`
  - **What:** Dropdown hardware class; inference mode (any / cloud-only / local_cuda / …); I/O badge multi-select.
  - **Pattern:** Existing category/tags filters (E4).
  - **Verify:** Manual with seed + ShellClaw fixture entry.

- [x] **1.4.3** Agent detail — display structured capabilities when present
  - **File:** `apps/web/src/app/agents/[id]/agent-detail-client.tsx`
  - **Verify:** Jetson example shows hardware + inference blocks.

---

## Task 1.5: Docs & registration UX

- [x] **1.5.1** Update `apps/web/src/app/docs/register/page.tsx`
  - **What:** Document optional `hardware` / `inference` in manifest; link to schema; note `tags` remain valid supplement.

- [x] **1.5.2** Update transport/discovery docs (`docs/transport.md`, `docs/registry/auto-registration.md`)
  - **What:** Closed enums table; migration from `tags: ["cuda","jetson",...]` to structured fields.

- [x] **1.5.3** Issue template (optional)
  - **File:** `.github/ISSUE_TEMPLATE/register_agent.yml`
  - **What:** Note that hardware/inference are inferred from manifest URL when auto-registration is used; no manual duplicate fields.

**Task 1.5 complete** (docs & registration UX).

---

## Task 1.6: Examples & fixtures

- [x] **1.6.1** Extend `tests/fixtures/registry/shellclaw-v1.0-entry.json` (post-S1 structured)
  - **What:** Add `hardware_class`, `inference_modes`, `hardware_io` derived values; keep `tags` for backward-compat demo.

- [x] **1.6.2** Add manifest fixtures
  - **Files:** `tests/fixtures/manifests/shellclaw-jetson-v1.0.json`, `shellclaw-rpi-v1.1.json`
  - **Source:** Context doc §3 + §7.12.

- [x] **1.6.3** Optional: add commented example block to `registry.json` or `docs/examples/registry-shellclaw.md`
  - **What:** Do not add ShellClaw to live registry until ShellClaw opens registration PR.

---

## Task 1.7: TypeScript client (optional same release)

- [x] **1.7.1** Extend `packages/typescript/client/src/discovery.ts` types + parsers
  - **Verify:** `npm test` in package.

---

## Task 1.8: Release

- [x] **1.8.1** Version bump `pyproject.toml` → `2.4.0` (+ `src/asap/__init__.py`, `@asap-protocol/client@2.4.0`; `asap-compliance` unchanged at `1.2.0`)
- [x] **1.8.2** CHANGELOG — feat(discovery): hardware and inference capability advertising
- [x] **1.8.3** Notify ShellClaw — [shellclaw-s1-structured-fields-handoff.md](./shellclaw-s1-structured-fields-handoff.md) (Wave 6.2 branch B per Q-ASAP)

---

## Risks

| Risk | Mitigation |
|------|------------|
| Enum churn before community Discussion | Ship closed enums per T0; CONTRIBUTING note for extensions |
| Self-reported throughput misleading | Optional field; UI label "self-reported" |
| Non-Python agents (ShellClaw C) lag schema | Schema-first; ShellClaw Task 5.1 manifest refactor precedes structured fields |
| `process_registration` does not fetch manifest | Derivation only guaranteed in auto-registration until 1.2.4 done |

---

## Definition of Done

- [x] All acceptance criteria checked
- [x] Pre-push CI green (ruff, mypy, pytest, web build) — full pre-push run 2026-05-24 (3439 pytest, ~92.8% cov; apps/web lint/tsc/vitest/build; TS client 105 tests)
- [x] Discussion or issue linked in CHANGELOG (community feedback tracked) — [#176](https://github.com/adriannoes/asap-protocol/issues/176)
- [x] ShellClaw informed for optional migration off `tags` (handoff doc; external notify when tag ships)
