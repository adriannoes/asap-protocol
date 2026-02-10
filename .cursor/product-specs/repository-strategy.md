# Repository Strategy: Monorepo vs. Multi-Repo

> **Type**: Strategic Analysis
> **Context**: Mid-v1.1.0 development, impacts future sprints (v1.2+)
> **Date**: 2026-02-10
> **Status**: DECIDED (Hybrid Monorepo)

---

## Executive Summary

The ASAP Protocol is currently a single repository (`asap-protocol`) containing the Python SDK, JSON-RPC schemas, and documentation. As we move towards the v2.0 Marketplace vision (Registry, Trust, Economy, Web App), we must decide how to structure the codebase.

**Decision**: Maintain a **Hybrid Monorepo** strategy throughout the v1.x cycle. Do not split repositories until v2.0 development begins and the Marketplace Web App requires an independent deployment cycle.

---

## Current Situation

The `asap-protocol` repository currently contains:
- **Protocol SDK**: `src/asap` (transport, auth, discovery, etc.)
- **Schemas**: `schemas/` (JSON-RPC definitions)
- **Documentation**: `docs/` (MkDocs)
- **Infrastructure**: Helm charts, Dockerfiles, CI/CD

The future **Marketplace** (v2.0) will introduce:
- **Registry Service**: FastAPI backend
- **Trust & Economy Services**: Backend logic
- **Web App**: Next.js frontend

---

## Options Analysis

We evaluated three structural options:

### Option A: Total Monorepo
Everything in one repo.
```
asap-protocol/
├── packages/
│   ├── asap-sdk/        ← Protocol (pip install asap-protocol)
│   ├── asap-registry/   ← Marketplace API
│   └── asap-web/        ← Next.js frontend
├── schemas/
└── docs/
```

### Option B: Multi-Repo
Separate repositories for Protocol and Marketplace.
```
GitHub:
├── asap-protocol/       ← SDK + schemas + docs
├── asap-marketplace/    ← Registry API + Trust + Economy + Web App
└── (optional) asap-schemas/  ← Shared schemas
```

### Option C: Hybrid Monorepo (Selected)
Single repo with strict internal boundaries, ready for future extraction.
```
asap-protocol/           ← Main repo
├── src/asap/            ← Python package (Protocol)
├── marketplace/         ← Isolated directory (future Marketplace)
├── schemas/             ← Shared
└── docs/
```

---

## Comparative Analysis

| Criteria | 🟢 Monorepo (A/C) | 🔵 Multi-Repo (B) |
|----------|--------------------|--------------------|
| **Setup Complexity** | Simple — 1 clone, 1 CI | Higher — 2+ repos, cross-versioning |
| **Independent Evolution** | ⚠️ Requires discipline | ✅ Naturally isolated |
| **Shared Code** | ✅ Direct import of schemas/models | ⚠️ Requires published packages or submodules |
| **CI/CD** | 1 pipeline (potentially slower) | Independent, fast pipelines |
| **Release Management** | ⚠️ Release per package needed | ✅ Independent release cycles |
| **Onboarding** | ✅ Everything in one place | ⚠️ Must navigate multiple repos |
| **External Contributors** | ✅ One PR covers protocol + feature | ⚠️ Cross-repo PRs are complex |
| **Tech Stack** | ⚠️ Mixed (Python + Node) | ✅ Clean stack per repo |

---

## Rationale for Hybrid Monorepo

We selected **Option C (Hybrid Monorepo)** for the following reasons:

1.  **Small Team Size**: For a team of 1-2 developers, the operational overhead of multi-repo (multiple CIs, syncing dependencies, releasing packages to use in other repos) is prohibitive.
2.  **Marketplace Code Doesn't Exist Yet**: Splitting repositories before the code exists is premature optimization.
3.  **Tightly Coupled Models**: The Protocol and Marketplace share core data models (`AgentManifest`, `TaskState`, schemas). Managing these version dependencies across repositories introduces significant friction.
4.  **Incremental Roadmap**: Features like the Registry API (v1.2) serve *both* the Protocol and the Marketplace. A hard split creates unnecessary ambiguity about where code belongs.

---

## Implementation Plan

### Phase 1: v1.1.0 - v1.3.0 (Current State)
Continue development within the existing structure. The `marketplace` folder does not exist yet; relevant logic lives within `src/asap` as protocol features (e.g., Auth, basic Discovery).

### Phase 2: v2.0.0 (Marketplace Initialization)
When we begin building the Marketplace Web App and specific backend services:
1.  Create a `marketplace/` directory at the root (sibling to `src/`).
2.  Structure it with `api/` (FastAPI) and `web/` (Next.js).
3.  Treat it as a separate internal "workspace".

### Phase 3: v2.x (Re-assessment)
We will consider extracting `marketplace/` to a separate repository ONLY when:
- The Web App (Next.js) requires a completely independent deployment, versioning, and release cycle from the Protocol SDK.
- The team grows to the point where Protocol engineers and Marketplace engineers are distinct groups.

At that point, extraction will be straightforward (git subtree split) because the code will already be modularized in its own directory.

---

## Conclusion

**Impact on v1.1.0**: None. Proceed with current development.
**Action**: Maintain strict code boundaries. Do not couple SDK logic with future Marketplace logic.
