# Product (`product/`)

This folder holds **product-level** documentation for the ASAP Protocol: PRDs, architecture decision records (ADRs), and design guides.

## What lives here

| Area | Role |
|------|------|
| **`prd/`** | Product Requirements Documents — versioned specs and shipped scope. |
| **`decision-records/`** | ADRs (indexed via `README.md` and `ADR-INDEX.md`). |
| **`design/`** | UI/UX source of truth (`design-system.md`, mobile strategy, references). |
| **`checkpoints.md`** | Post-release documentation review schedule (PRD updates, velocity, retros). |

## Local-only / ignored paths

Per `.gitignore`, the following are **not committed** to the remote (keep them locally if you use them):

- **`strategy/`** — Long-form vision, roadmap-to-marketplace, deferred backlog (optional local checkout).
- **`private/`**, **`private-roadmap/`**, **`prd/private/`**, and selective **`prd/prd-v2.3.[1-9]-*.md`** — Commercial or tactical drafts.

Public READMEs and docs should prefer **`decision-records/`**, **`prd/`** (public filenames), and **`docs/`** for links that must work on GitHub.

## Directory layout (overview)

```
product/
├── README.md                 # This file
├── checkpoints.md          # Post-release doc review milestones (follow-up)
├── strategy/                 # Local-only when ignored (vision, roadmap, backlog)
├── decision-records/         # ADRs
├── design/                   # Design system & UX references
└── prd/                      # PRDs (including private/ when present locally)
```

### Current roadmap status

| Version | Status | PRD | Focus |
|---|---|---|---|
| v2.1.0 / v2.1.1 | ✅ Released | `prd-v2.1-ecosystem.md` | Consumer SDK + ecosystem |
| **v2.2.0** | **✅ Released (2026-04-15)** | `prd-v2.2-protocol-hardening.md` | Identity, capabilities, streaming, batch, audit |
| **v2.2.1** | **✅ Released (2026-04-21)** | `prd-v2.2.1-patch.md` | WebAuthn real, CLI compliance/audit |
| v2.3.0 — Adoption Core | 🚧 DRAFT (adoption-first) | `prd-v2.3-scale.md` | OpenAPI Adapter, TypeScript SDK, reference examples |
| v2.3.1 — Adapter Lab I | 🔒 Private planning | `prd/private/prd-v2.3.1-adapter-lab.md` | OpenAI Agents SDK, Google ADK, Mastra, LangGraph validation |
| v2.3.2 — Adapter Lab II | 🔒 Private planning | `prd/private/prd-v2.3.2-enterprise-workflow-adapters.md` | Microsoft Agent Framework, Haystack, Letta, workflow automation |
| v2.3.3 — Distribution Loop | 🔒 Private planning | `prd/private/prd-v2.3.3-distribution-loop.md` | Templates, docs, homepage, metrics, developer activation |
| v2.4.0 — Spec & Interop | 🚧 VISION DRAFT (rescoped) | `prd-v2.4-adoption.md` | MCP Auth Bridge, Formal Spec, Introspection, Privacy |
| v3.0 — Economy | 🔭 Long-term | `prd-v3.0-economy.md` | Settlement, billing |

> **Strategic note**: Registry API Backend (PostgreSQL), Intent-Based Search, Orchestration Primitives, Delegated/Autonomous Mode formalization, and DeepEval remain deferred until their triggers materialize. The v2.3.x train now treats adoption as the primary product: make existing APIs, SDKs, CLIs, and agent frameworks usable by agents with minimal human coordination.

> **Visibility policy**: Public docs should explain the stable protocol, released capabilities, adoption guides, and high-level roadmap. Detailed go-to-market, pricing, private feature timing, fundraising, and near-term tactical PRDs live in ignored private folders.

## Key entrypoints

- **[Decision index](./decision-records/README.md)** — ADR catalog.
- **[Documentation checkpoints](./checkpoints.md)** — When to refresh PRDs and retros after releases.
- **`prd/`** — Versioned requirements; open files matching shipped releases for authoritative scope.
