# v2.4.0 Roadmap — Edge-AI Discovery & ShellClaw Onboarding

> **Context:** [asap-protocol-questions-for-upstream.md](../../../product/prd/private/asap-protocol-questions-for-upstream.md) (ShellClaw v1.0 literals + v2.4 proposal).
> **Related proposal:** [asap-protocol-edge-ai-capabilities.md](../../../product/prd/private/asap-protocol-edge-ai-capabilities.md)
> **PyPI target:** Minor bump after v2.3.x — additive, backward-compatible.

---

## Goals

1. **Unblock ShellClaw v1.0 marketplace listing** with documented answers for static manifest hosting, `online_check: false`, and registry validation (no schema change required).
2. **Ship structured edge-AI discovery** via optional `manifest.capabilities.hardware` + `inference`, mirrored to `RegistryEntry`, Browse filters, and `find_by_*` helpers.

---

## Design lock (T0 — recorded 2026-05-24 from ShellClaw upstream session)

| Question | Decision |
|----------|----------|
| `hardware.class` / `inference.modes` enums | **Closed** vocabulary; extend via PR |
| `throughput_tokens_per_second` | **Optional**, self-reported in v2.4; compliance validation deferred |
| `hardware.io` | **Physical interfaces only** in v2.4 |
| Link to `auth/capabilities.py` runtime grants | **None** — advertising vs authz stay separate |
| Hard rejects | Do not require `io` or throughput; do not rename `edge_accelerator`; no CUDA version sub-enums |

---

## Sprints

| Sprint | File | Goal | Blocks ShellClaw v1.0? |
|--------|------|------|------------------------|
| **S0** | [sprint-S0-shellclaw-marketplace-onboarding.md](./sprint-S0-shellclaw-marketplace-onboarding.md) | Confirm §5 asks; optional `built_with`; docs for static manifest URL | **No** — ShellClaw ships with `tags` workaround |
| **S1** | [sprint-S1-edge-ai-capabilities.md](./sprint-S1-edge-ai-capabilities.md) | Schema + registry mirror + UI filters + SDK helpers | **No** — Wave 6.2 switches to structured fields only if merged before registration PR |

---

## Dependency graph

```
S0 (onboarding docs + small DX)
 │
 ├──────────────────────────────┐
 ▼                              ▼
ShellClaw Wave 6 (tags)    S1 (edge-ai capabilities)
                                    │
                                    ▼
                            ShellClaw optional migration
                            (structured hardware/inference)
```

---

## ShellClaw coordination

Notify `adriannoes/shellclaw` when:

- **S0 complete** — §5 answers published in `docs/guides/shellclaw-registry.md` (or release notes); Wave 6.2 can open IssueOps PR.
- **S1 merged** — Wave 6.2 may use structured fields instead of `tags` (see literals in S1 Task 1.7).
- **S1 release (v2.4.0)** — Handoff: [shellclaw-s1-structured-fields-handoff.md](./shellclaw-s1-structured-fields-handoff.md) (Wave 6.2 branch B per Q-ASAP).

---

## Out of scope (v2.4.0)

- Registry API backend ([#142](https://github.com/adriannoes/asap-protocol/issues/142) / DEFERRED T3)
- Runtime `Capability` authz changes (`src/asap/auth/capabilities.py`)
- Envelope / OAuth2 / capability-escalation changes
- Compliance harness validating `throughput_tokens_per_second`

---

## Definition of Done (release)

- [x] S0 acceptance checklist green; ShellClaw registry entry validates via `validate_registry.py` on `tests/fixtures/registry/shellclaw-v1.0-agents-array.json` (S0 DoD + `pytest -k shellclaw`, 2026-05-24)
- [x] S1 acceptance checklist green; Jetson + RPi in `docs/examples/registry-shellclaw.md` and `tests/fixtures/manifests/shellclaw-jetson-v1.0.json` / `shellclaw-rpi-v1.1.json` (PR [#177](https://github.com/adriannoes/asap-protocol/pull/177) → `shellclaw-integration`)
- [x] `pyproject.toml` minor version bump **2.4.0**; CHANGELOG `[2.4.0]`; `@asap-protocol/client@2.4.0` (community feedback [#176](https://github.com/adriannoes/asap-protocol/issues/176))
- [x] Pre-push CI suite per `.cursor/rules/git-commits.mdc` — ruff, mypy, pytest (3439), apps/web lint/tsc/vitest/build, TS client tests (2026-05-24; see S1 DoD)
- [ ] Maintainer release: tag `v2.4.0`, PyPI/npm publish, docs/landing sync — [release-checklist.md](./release-checklist.md)
