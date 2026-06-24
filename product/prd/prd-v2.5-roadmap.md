# PRD: ASAP Protocol v2.5.x — Interop & Adoption Train

> **Product Requirements Document (train index)**
>
> **Version**: 2.5.x
> **Status**: ACTIVE PLANNING
> **Created**: 2026-06-22
> **Last Updated**: 2026-06-22
>
> **Predecessor**: [prd-v2.4.1-security-hardening.md](./prd-v2.4.1-security-hardening.md) (✅ shipped 2026-06-14)
> **Successor (long-term)**: [prd-v3.0-economy.md](./prd-v3.0-economy.md)

---

## 1. Why v2.5.x exists

Between **v2.4.1** (security patch) and **v3.0** (economy), the project needs a coherent minor train that:

1. **Closes the MCP auth gap** — ASAP identity on MCP tool execution (convergência A2A+MCP alinhada à literatura recente sobre taxonomias de protocolos de agentes).
2. **Continues adoption** — framework/workflow adapters e distribution loop (antes planejados como v2.3.2/v2.3.3).
3. **Finalizes standards-track artifacts** — spec formal, introspection, privacy (antes em `prd-v2.4-adoption.md`).

### Versioning history (rescope log)

| Old label | New label | Reason |
|-----------|-----------|--------|
| `prd-v2.4-adoption.md` (Spec & Interop) | **v2.5.0–v2.5.3** | Número **2.4.0** foi usado para Edge-AI Discovery |
| `prd-v2.3.2` (Adapter Lab II) | **v2.5.1** | Post-2.4.1; executar após MCP Auth Bridge |
| `prd-v2.3.3` (Distribution Loop) | **v2.5.2** | Post-2.5.1 |
| Spec formal + introspection + privacy | **v2.5.3** | Standards track após adoption loop |
| v2.4.1 §8 security follow-ups | **v2.5.4** (opcional patch) | Não bloqueia interop |

---

## 2. Train schedule

| Version | Codename | Primary outcome | PRD | Status |
|---------|----------|-----------------|-----|--------|
| **v2.5.0** | MCP Auth Bridge | ASAP Agent JWT + capabilities em MCP `tools/call` | [prd-v2.5.0-mcp-auth-bridge.md](./prd-v2.5.0-mcp-auth-bridge.md) | **IN PROGRESS** — [tasks roadmap](../../engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md) |
| **v2.5.1** | Adapter Lab II | Enterprise/workflow adapters (ex v2.3.2) | [prd-v2.5.1-adapter-lab-ii.md](./prd-v2.5.1-adapter-lab-ii.md) | Planned (after 2.5.0) |
| **v2.5.2** | Distribution Loop | Homepage, templates, métricas (ex v2.3.3) | [prd-v2.5.2-distribution-loop.md](./prd-v2.5.2-distribution-loop.md) | Planned (after 2.5.1) |
| **v2.5.3** | Formal Spec & Interop | RFC spec, introspection, privacy, cross-protocol | [prd-v2.5.3-formal-spec-interop.md](./prd-v2.5.3-formal-spec-interop.md) | Planned |
| **v2.5.4** | Security Follow-up | `extra="forbid"`, operator API auth, Redis replay (ex v2.4.1 §8) | *(inline in train — patch PRD when triggered)* | Optional |

**Execution rule:** v2.5.1 and v2.5.2 **do not start** until v2.5.0 ships. v2.5.3 may overlap planning/docs-only work but implementation waits for stable MCP Auth Bridge APIs.

---

## 3. Strategic positioning (pilha federada)

```
L4 Interaction     ASAP agent-to-agent (v2.2+)
L3 Execution       MCP tools ← v2.5.0 Auth Bridge fecha este gap
L2 Discovery       well-known + Lite Registry (v2.3+)
L1 Identity        Host/Agent JWT + capabilities (v2.2+)
```

Narrativa pública: **ASAP não substitui MCP** — fornece a camada de identidade e policy que MCP não padroniza.

---

## 4. Prerequisites (train-wide)

| Prerequisite | Status |
|-------------|--------|
| v2.4.1 security patch shipped | ✅ 2026-06-14 |
| Capability model stable (v2.2+) | ✅ |
| Agent JWT + Host JWT (v2.2+) | ✅ |
| MCP server/client in tree (`asap.mcp`) | ✅ stdio + tools |
| Envelope MCP payloads (`McpToolCall`) | ✅ A2A path only — not native MCP auth |
| OpenAPI Adapter (v2.3.0) | ✅ |

---

## 5. Non-goals (entire v2.5 train)

| Feature | When |
|---------|------|
| Economy / billing | v3.0 |
| Federated registry | v3.x+ |
| gRPC binding | TBD |
| Schema negotiation runtime (Agora-style) | Out of scope |
| Registry API backend (PostgreSQL) | Deferred until 500-agent trigger |

---

## 6. Related documents

- **Shipped v2.4.0**: [prd-v2.4.0-edge-ai-discovery.md](./prd-v2.4.0-edge-ai-discovery.md)
- **Shipped v2.4.1**: [prd-v2.4.1-security-hardening.md](./prd-v2.4.1-security-hardening.md)
- **Adoption foundation**: [prd-v2.3-scale.md](./prd-v2.3-scale.md)
- **Legacy redirect**: [prd-v2.4-adoption.md](./prd-v2.4-adoption.md)
- **Tasks**: [engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md](../../engineering/tasks/v2.5.0/tasks-v2.5.0-roadmap.md)

---

## Change Log

| Date | Change |
|------|--------|
| 2026-06-22 | Parent tasks 1.0–5.0 added to sprint index; awaiting LGTM for detailed sub-tasks |
