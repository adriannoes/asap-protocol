# Product Specs Directory Guide

The `product-specs` directory contains **strategic and product-level documentation** for the ASAP Protocol.

## Directory Structure

```
product-specs/
├── README.md                      # This file
├── strategy/                      # Strategic vision and long-term planning
│   ├── vision-agent-marketplace.md
│   ├── roadmap-to-marketplace.md
│   ├── repository-strategy.md
│   ├── deferred-backlog.md
│   ├── v0-original-specs.md
│   └── user-flow.md
├── decision-records/              # Architecture Decision Records (ADR)
│   ├── README.md                  # Index of decisions
│   ├── 01-architecture.md
│   ├── 02-protocol.md
│   ├── 03-security.md
│   ├── 04-technology.md
│   └── 05-product-strategy.md
└── prd/                           # Product Requirements Documents
    ├── prd-v1-roadmap.md
    ├── prd-v1.1-roadmap.md
    ├── prd-v1.2-roadmap.md
    ├── prd-v1.3-roadmap.md
    ├── prd-v1.4-roadmap.md
    ├── prd-v2.0-roadmap.md
    ├── prd-v2.1-ecosystem.md           # ✅ Shipped (v2.1.0 / v2.1.1)
    ├── prd-v2.2-protocol-hardening.md  # ✅ Shipped (v2.2.0 — 2026-04-15)
    ├── prd-v2.2-scale.md               # ⛔ Superseded → moved to v2.3
    ├── prd-v2.2.1-patch.md             # 🟡 NEXT — carry-over patch (WebAuthn real, CLIs)
    ├── prd-v2.3-scale.md               # 🚧 DRAFT — rescoped to "Adoption Multiplier" (OpenAPI + TS SDK + Auto-Reg)
    ├── prd-v2.4-adoption.md            # 🚧 VISION DRAFT — rescoped to "Spec & Interop" (MCP, Spec, Introspection)
    ├── prd-v3.0-economy.md             # 🔭 Long-term
    ├── prd-a2h-integration.md
    ├── prd-asap-implementation.md
    ├── prd-cross-platform-integration-asap.md
    ├── prd-cross-platform-integration-agentic.md
    ├── prd-design-system-revamp.md
    └── prd-review-schedule.md
```

### Status atual da roadmap

| Versão | Status | PRD | Foco |
|---|---|---|---|
| v2.1.0 / v2.1.1 | ✅ Released | `prd-v2.1-ecosystem.md` | Consumer SDK + ecosystem |
| **v2.2.0** | **✅ Released (2026-04-15)** | `prd-v2.2-protocol-hardening.md` | Identity, capabilities, streaming, batch, audit |
| **v2.2.1** | 🟡 **NEXT (patch)** | `prd-v2.2.1-patch.md` | Carry-over: WebAuthn real, CLI compliance/audit |
| v2.3.0 — Adoption Multiplier | 🚧 DRAFT (rescoped 2026-04-17) | `prd-v2.3-scale.md` | OpenAPI Adapter, TypeScript SDK, Auto-Registration |
| v2.4.0 — Spec & Interop | 🚧 VISION DRAFT (rescoped) | `prd-v2.4-adoption.md` | MCP Auth Bridge, Formal Spec, Introspection, Privacy |
| v3.0 — Economy | 🔭 Long-term | `prd-v3.0-economy.md` | Settlement, billing |

> **Nota estratégica**: Registry API Backend (PostgreSQL), Intent-Based Search, Orchestration Primitives, Delegated/Autonomous Mode formalization e DeepEval foram **deferidos** da v2.3 — voltam quando os triggers (500+ agentes, demanda específica) materializarem. A v2.3 reescopada ataca exatamente o trigger de 500 agentes via OpenAPI Adapter (zero-code onboarding) + TypeScript SDK + Auto-Registration.

## Key Documents

### Strategy (`strategy/`)
- **[Vision](./strategy/vision-agent-marketplace.md)**: North Star for the Agent Marketplace.
- **[Roadmap](./strategy/roadmap-to-marketplace.md)**: Version sequencing from v1.0 through **v2.2.0** (released 2026-04-15) toward v2.3+.
- **[Deferred Backlog](./strategy/deferred-backlog.md)**: Features deprioritized for the Lean Pivot.

### Decisions (`decision-records/`)
- **[Decision Index](./decision-records/README.md)**: Categorized list of all architectural and product decisions.
- Replaces the old monolithic `ADR.md`.

### Requirements (`prd/`)
- Detailed requirements for each version version.
