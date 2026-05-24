# ShellClaw handoff — v2.4.0 structured capabilities (S1)

> **When:** After `asap-protocol` **2.4.0** is tagged and published (PyPI + npm `@asap-protocol/client`).
> **Audience:** ShellClaw maintainers (`adriannoes/shellclaw` planning / Wave 6.2).
> **No external email** — paste this block into the shellclaw issue or PR.

## Action

**ShellClaw:** structured `hardware` and `inference` fields are available in **v2.4.0**. Use **Wave 6.2 branch B** per Q-ASAP: manifest carries structured capabilities; registry entry fields are **derived at registration** (do not duplicate in IssueOps body when a manifest URL is provided).

## Copy-paste block

```text
ASAP v2.4.0 (S1 edge-AI discovery) — structured fields ready.

- Manifest: optional capabilities.hardware + capabilities.inference (closed enums)
- Registry mirror (derived): hardware_class, inference_modes, hardware_io
- Literals: engineering/tasks/v2.4.0/sprint-S1-edge-ai-capabilities.md § Canonical ShellClaw values
- Example manifest: tests/fixtures/manifests/shellclaw-jetson-v1.0.json
- Example registry shape: tests/fixtures/registry/shellclaw-v1.0-entry.json, docs/examples/registry-shellclaw.md
- Wave 6.2 branch B (Q-ASAP): use structured fields in manifest; keep tags only as supplement if needed
- Wave 6.2 branch A (tags-only) still valid for v1.0 if registration PR opened before v2.4.0 merge

S0 §5 answers unchanged: docs/guides/shellclaw-registry.md
```

## References

- [sprint-S1-edge-ai-capabilities.md](./sprint-S1-edge-ai-capabilities.md)
- [asap-protocol-edge-ai-capabilities.md](../../../product/prd/private/asap-protocol-edge-ai-capabilities.md)
- [shellclaw-registry.md](../../../docs/guides/shellclaw-registry.md) — Wave 6.2 IssueOps (branch A / tags)
