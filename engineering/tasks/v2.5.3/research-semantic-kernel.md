# Research note: Semantic Kernel / Microsoft Agent Framework ↔ ASAP

> **Status**: Spike-time scope check for Adapter Lab II S1b (Wave 1 / 2b.1)  
> **Spike date**: 2026-07-13  
> **Sprint**: [sprint-S1b-semantic-kernel.md](./sprint-S1b-semantic-kernel.md)  
> **Demand**: [demand-sheet.md](./demand-sheet.md) — S0 **no-go** on GitHub demand; **maintainer override (2026-07-13)** to ship a research/experimental interop guide  
> **PRD**: [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md) D2  
> **ASAP guide status**: **research / experimental** — not a maintained adapter  
> **Public guide (2b.2)**: [`docs/integrations/microsoft-agent-framework.md`](../../../docs/integrations/microsoft-agent-framework.md)

This note locks naming and deliverable shape for 2b.2. The public guide is linked above.

---

## 1. Naming conclusion (as of 2026-07-13)

| Name | Role today | Packages / docs |
|------|------------|-----------------|
| **Microsoft Agent Framework (MAF)** | **Current** Microsoft call-to-action for new agent apps; successor to Semantic Kernel + AutoGen | .NET: `Microsoft.Agents.AI` (NuGet); Python: `agent-framework` (PyPI); docs: aka.ms/AgentFramework/Docs; repo: [microsoft/agent-framework](https://github.com/microsoft/agent-framework) |
| **Semantic Kernel (SK)** | **Maintenance / legacy** track — critical bugs + security; most new features go to MAF | `Microsoft.SemanticKernel` / SK Python; migration guides under Agent Framework docs |

**Evidence (public Microsoft sources):**

- Product FAQ: MAF is the successor to SK for building AI agents; SK remains supported at least one year after MAF leaves Preview / reaches GA ([Semantic Kernel and Microsoft Agent Framework](https://devblogs.microsoft.com/agent-framework/semantic-kernel-and-microsoft-agent-framework/), Oct 2025).
- **MAF 1.0 GA**: announced early April 2026 for .NET and Python ([Microsoft Agent Framework Version 1.0](https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/); tags `dotnet-1.0.0` / `python-1.0.0` on `microsoft/agent-framework`, 2026-04-02).
- Migration: [SK → Agent Framework](https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-semantic-kernel/) (Learn / semantic-kernel-docs tree).

**Guide title / path for 2b.2:** prefer `docs/integrations/microsoft-agent-framework.md`, with a short “Semantic Kernel (legacy)” section pointing at Microsoft’s migration docs. Keep sprint/folder name “semantic-kernel” for PRD continuity; do not brand the public page as SK-first.

---

## 2. Deliverable decision: **guide-only**

| Option | Decision |
|--------|----------|
| Full .NET SDK / NuGet | **Out of scope** (PRD + maintainer) |
| Guide + minimal C# sample under `examples/` | **No** for v2.5.3 Wave 1→2 |
| **Guide-only** research/experimental interop doc | **Yes** |

**Why guide-only:**

1. **No in-repo .NET maintainer path** — CI has Mastra / OpenAI Agents / TypeScript workflows; **no** `setup-dotnet`, `.csproj`, or C# samples under `examples/`.
2. Maintainer override explicitly prefers **guide-only** when a C# sample cannot run in CI or lacks a clear .NET path.
3. Demand remains **zero** GitHub issues; override justifies an experimental doc, not CI matrix expansion.
4. Interop story is conceptual: ASAP Host/Agent JWT + capability grants beside MAF tools / MCP / A2A — does not require a compiled sample to be useful.

**2b.3:** leave unchecked; revisit a thin sample only if a maintainer later adds a documented “requires .NET SDK” path (still no NuGet / no protocol fork).

---

## 3. Guide shape (2b.2 — written)

**Path:** [`docs/integrations/microsoft-agent-framework.md`](../../../docs/integrations/microsoft-agent-framework.md)

- Status banner first: **research / experimental** (not maintained).
- Map ASAP Agent JWT / capabilities ↔ MAF tool registration / MCP-style tool surfaces (honest limits).
- Call out SK only as predecessor / migration audience.
- MkDocs nav + `docs/index.md` deferred to **S3**.

---

## 4. Non-goals

- Protocol fork or new transport methods
- Publishing a NuGet package
- Claiming parity with Lab I first-class adapters (Mastra / OpenAI Agents)
