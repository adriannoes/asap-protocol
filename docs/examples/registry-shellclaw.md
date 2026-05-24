# ShellClaw registry example (structured hardware, v2.4)

Reference for Sprint S1 edge-AI capability advertising. **Do not** add this entry to the live [`registry.json`](../../registry.json) until ShellClaw opens a registration PR.

Canonical values match [`engineering/tasks/v2.4.0/sprint-S1-edge-ai-capabilities.md`](../../engineering/tasks/v2.4.0/sprint-S1-edge-ai-capabilities.md) and:

- Registry fixture: [`tests/fixtures/registry/shellclaw-v1.0-entry.json`](../../tests/fixtures/registry/shellclaw-v1.0-entry.json)
- Manifest fixtures: [`tests/fixtures/manifests/shellclaw-jetson-v1.0.json`](../../tests/fixtures/manifests/shellclaw-jetson-v1.0.json), [`shellclaw-rpi-v1.1.json`](../../tests/fixtures/manifests/shellclaw-rpi-v1.1.json)

## Jetson v1.0 — derived registry fields

`hardware_class`, `inference_modes`, and `hardware_io` are **derived from the signed manifest** during auto-registration (or when `process_registration.py` loads the manifest URL). Registrants should not duplicate them in the IssueOps body.

```json
{
  "id": "urn:asap:agent:shellclaw",
  "name": "ShellClaw",
  "description": "…",
  "endpoints": {
    "http": "https://shellclaw.example.com/asap",
    "manifest": "https://adriannoes.github.io/shellclaw/manifest.json"
  },
  "skills": ["assistant", "edge_briefing", "server_admin", "gpio_control"],
  "category": "Infrastructure",
  "tags": ["cuda", "edge-ai", "hardware", "jetson", "local-inference"],
  "hardware_class": "edge_accelerator",
  "inference_modes": ["cloud", "local_cuda"],
  "hardware_io": ["gpio", "i2c"],
  "asap_version": "2.1.0",
  "repository_url": "https://github.com/adriannoes/shellclaw",
  "documentation_url": "https://github.com/adriannoes/shellclaw#readme",
  "built_with": "Other",
  "verification": null,
  "online_check": false
}
```

`tags` remain valid as a backward-compatible supplement for browse filters until agents migrate fully to structured fields.

## Manifest `capabilities` (Jetson v1.0)

See [`schemas/examples/shellclaw-jetson-capabilities.json`](../../schemas/examples/shellclaw-jetson-capabilities.json) for the capabilities-only snippet, or the full manifest fixture under `tests/fixtures/manifests/`.

## RPi v1.1 (docs-only)

`hardware.class`: `sbc`, `hardware.model`: `raspberry_pi_zero_2w`, `inference.modes`: `["cloud", "local_cpu"]`, local model `tinyllama-1.1b-chat-Q4_K_M`. Full manifest: `tests/fixtures/manifests/shellclaw-rpi-v1.1.json` (agent URN `urn:asap:agent:shellclaw-rpi-v1-1` — hyphens only, per `AGENT_URN_PATTERN`).
