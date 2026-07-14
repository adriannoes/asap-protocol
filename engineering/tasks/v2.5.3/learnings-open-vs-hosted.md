# Learnings: open vs hosted (LAB2-005)

**Date**: 2026-07-13  
**Release train**: Adapter Lab II (v2.5.3)  
**Sprint**: [sprint-S3-docs-review.md](./sprint-S3-docs-review.md)

---

## Summary

Adapter Lab II ships **open** documentation, examples, and security guides. A **hosted** control plane (org policy, SSO, centralized grant administration) remains a later product surface — not part of v2.5.3.

---

## What stays public (open)

| Surface | Rationale |
|---------|-----------|
| Integration / adapter guides under `docs/` | Discoverability without a login wall |
| Runnable examples (`examples/workflow_asap_connector/`, `examples/nemo_agent_toolkit_asap/`, …) | Reproducible Path A / OpenAPI patterns |
| Automation connector security guide | Baseline for secrets, TLS, webhooks, grants |
| First-party packages already on PyPI / npm | Same openness as Lab I |

Open material must remain accurate without claiming hosted features that do not exist yet.

---

## What is hosted later

| Concern | Notes |
|---------|-------|
| Org-wide policy / grant administration | Central UI or API for capability grants across agents |
| SSO / enterprise identity | Beyond per-runtime Host/Agent JWT examples |
| Multi-tenant connector control plane | Credential vaults, shared webhook secrets, audit fan-out |

These do **not** block shipping Lab II docs or examples.

---

## NeMo Agent Toolkit lesson

NAT clarified three layers that must not be conflated:

1. **Open guide + Path A demo** — public interop page + stdio `mcp_client` → ASAP `protect_server` example (shipped experimental in v2.5.3).
2. **Hosted control-plane** — org policy / SSO / managed grants for NAT↔ASAP operators (future; not this release).
3. **Third-party `nemo-agent-toolkit-*` plugin (Path C)** — deferred post–v2.5.3 until Path A is promoted and maintainership is decided.

ASAP complements NAT’s MCP/A2A plugins; it does **not** replace A2A inside NeMo.

---

## Decision for Lab II docs

Keep adapters, integrations, and security guides in the public MkDocs site. Point experimental pages clearly. Defer marketing of hosted control-plane features to a later train (Distribution Loop / product follow-ups), not S3/S4 copy.
