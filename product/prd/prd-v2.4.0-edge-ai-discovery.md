# PRD: ASAP Protocol v2.4.0 — Edge-AI Discovery

> **Product Requirements Document**
>
> **Version**: 2.4.0
> **Status**: ✅ **SHIPPED** (2026-05-24)
> **Created**: 2026-05-01
> **Last Updated**: 2026-06-22 (retrospective PRD; execution lived in `engineering/tasks/v2.4.0/`)

---

## 1. Executive Summary

v2.4.0 delivered **structured edge-AI capability advertising** on signed manifests, mirrored to the Lite Registry and marketplace UI. Wire protocol, OAuth2, and capability authz were unchanged — additive schema fields only.

**Shipped scope:**
- Optional `manifest.capabilities.hardware` and `manifest.capabilities.inference`
- Registry mirror fields (`hardware_class`, `inference_modes`, `hardware_io`)
- Discovery helpers (`find_by_hardware_class`, `find_by_inference_mode`, `find_by_io`)
- Marketplace filters + TypeScript SDK types (`@asap-protocol/client@2.4.0`)
- ShellClaw onboarding docs and fixtures (S0 + S1)

**Not in scope** (deferred to later releases): MCP Auth Bridge, formal RFC spec, registry API backend.

---

## 2. Goals (achieved)

| Goal | Metric | Result |
|------|--------|--------|
| ShellClaw marketplace path | Documented static manifest + IssueOps | ✅ `docs/guides/shellclaw-registry.md` |
| Structured hardware/inference | Schema + registry mirror + UI | ✅ PR [#177](https://github.com/adriannoes/asap-protocol/pull/177) |
| Backward compatibility | Existing manifests unchanged | ✅ Optional fields only |

---

## 3. Shipped Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| EDGE-001 | `HardwareCapability` + `InferenceCapability` on manifest | ✅ |
| EDGE-002 | Closed enums (`HardwareClass`, `InferenceMode`, `HardwareIoType`) | ✅ |
| EDGE-003 | `derive_registry_hardware_fields()` in auto-registration | ✅ |
| EDGE-004 | Registry client `find_by_*` helpers | ✅ |
| EDGE-005 | Web marketplace filters + agent detail blocks | ✅ |
| EDGE-006 | TypeScript `RegistryEntry` hardware fields | ✅ |
| SHELL-001 | ShellClaw fixtures + registry example doc | ✅ |

---

## 4. Related Documents

- **Execution**: [`engineering/tasks/v2.4.0/tasks-v2.4.0-roadmap.md`](../../engineering/tasks/v2.4.0/tasks-v2.4.0-roadmap.md)
- **CHANGELOG**: [`CHANGELOG.md`](../../CHANGELOG.md#240---2026-05-24)
- **Next patch**: [prd-v2.4.1-security-hardening.md](./prd-v2.4.1-security-hardening.md)
- **Next train**: [prd-v2.5-roadmap.md](./prd-v2.5-roadmap.md) → [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Retrospective PRD created; separates shipped v2.4.0 from former `prd-v2.4-adoption.md` vision |
