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

- [ ] S0 acceptance checklist green; ShellClaw registry entry in §4 of context doc validates via `validate_registry.py`
- [ ] S1 acceptance checklist green; example Jetson + RPi entries in docs
- [ ] `pyproject.toml` minor version bump; CHANGELOG entry
- [ ] Pre-push CI suite per `.cursor/rules/git-commits.mdc`
