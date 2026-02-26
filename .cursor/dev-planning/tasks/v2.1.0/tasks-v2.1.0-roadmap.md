# Tasks: ASAP Protocol v2.1.0 Roadmap

> **High-level sprint overview** for v2.1.0 (Ecosystem Enablement)
>
> **Parent PRD**: [prd-v2.1-ecosystem.md](../../../product-specs/prd/prd-v2.1-ecosystem.md)
> **Prerequisite**: v2.0.0 released (Lite Registry, IssueOps registration)
> **Target Version**: v2.1.0
> **Focus**: Consumer SDK, Framework Integrations, Registry UX, Agent Revocation, PyPI
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [E1: Trust & Revocation Foundation](./sprint-E1-trust-revocation.md)
> - [E2: Consumer SDK Core](./sprint-E2-consumer-sdk.md)
> - [E3: Framework Integrations](./sprint-E3-framework-integrations.md)
> - [E4: Registry UX (Category/Tags)](./sprint-E4-registry-ux.md)
> - [E5: PyPI Distribution](./sprint-E5-pypi-distribution.md)

---

## Strategic Context

v2.1.0 activates the **demand side** of the marketplace:
- **Consumer SDK**: `MarketClient.resolve(urn)` + `agent.run(payload)` in &lt;5 lines
- **Trust & Revocation**: Ed25519 validation, `revoked_agents.json`, IssueOps revoke flow
- **Framework Integrations**: LangChain, CrewAI, PydanticAI, MCP (Claude Desktop, Cursor)
- **Registry UX**: Category/tags filtering in Browse
- **PyPI**: First public `pip install asap-protocol`

---

## Sprint E1: Trust & Revocation Foundation

**Goal**: Trust validation wrapper, revoked_agents.json, IssueOps revoke flow

**Depends on**: v2.0.0; existing `asap.crypto.trust`, `SignatureVerificationError`

| Task | Sub-tasks | Est. |
|------|-----------|------|
| 1.1 | Create trust module (`verify_agent_trust`) | 1d |
| 1.2 | Create revocation module (`is_revoked`) | 1d |
| 1.3 | Define revoked_agents.json schema | 0.5d |
| 1.4 | Revoke-agent IssueOps flow | 1.5d |
| 1.5 | AgentRevokedException, client exports | 0.5d |

**Definition of Done**: `verify_agent_trust` validates manifests; `is_revoked` fetches list; IssueOps revoke creates PR.

**Detail**: [sprint-E1-trust-revocation.md](./sprint-E1-trust-revocation.md)

---

## Sprint E2: Consumer SDK Core

**Goal**: MarketClient, ResolvedAgent, cache, 429/Bearer, Raw Fetch doc

**Depends on**: Sprint E1 (trust, revocation)

| Task | Sub-tasks | Est. |
|------|-----------|------|
| 2.1 | Registry cache (TTL, ASAP_REGISTRY_CACHE_TTL) | 0.5d |
| 2.2 | MarketClient.resolve() + ResolvedAgent.run() | 2d |
| 2.3 | HTTP 429 exponential backoff | 0.5d |
| 2.4 | Bearer token passthrough | 0.5d |
| 2.5 | Document Raw Fetch path | 0.5d |
| 2.6 | Client package __init__, public API | 0.5d |

**Definition of Done**: `from asap.client import MarketClient`; resolve + run in &lt;5 lines; tests pass.

**Detail**: [sprint-E2-consumer-sdk.md](./sprint-E2-consumer-sdk.md)

---

## Sprint E3: Framework Integrations

**Goal**: LangChain, CrewAI, PydanticAI tools; asap-mcp-server

**Depends on**: Sprint E2 (MarketClient)

| Task | Sub-tasks | Est. |
|------|-----------|------|
| 3.1 | Optional deps [mcp], [langchain], [crewai] | 0.5d |
| 3.2 | LangChainAsapTool | 1d |
| 3.3 | CrewAIAsapTool | 1d |
| 3.4 | PydanticAI integration (SHOULD) | 1d |
| 3.5 | asap-mcp-server entry point | 1.5d |
| 3.6 | Integrations package __init__ | 0.5d |

**Definition of Done**: `LangChainAsapTool(urn)` works; `uvx asap-mcp-server` runs.

**Detail**: [sprint-E3-framework-integrations.md](./sprint-E3-framework-integrations.md)

---

## Sprint E4: Registry UX (Category/Tags)

**Goal**: Category/tags in RegistryEntry, Issue template, process_registration, Browse filters, Revoked badge

**Depends on**: Sprint E1 (for revoked_agents.json in 4.6)

| Task | Sub-tasks | Est. |
|------|-----------|------|
| 4.1 | RegistryEntry category + tags | 0.5d |
| 4.2 | GitHub Issue template (category, tags) | 0.5d |
| 4.3 | process_registration parses category/tags | 1d |
| 4.4 | Browse filters (category, tags) | 1d |
| 4.5 | validate_registry for category/tags | 0.5d |
| 4.6 | Revoked badge + exclude from Browse | 1d |

**Definition of Done**: Browse filterable by category/tags; revoked agents excluded; badge on detail.

**Detail**: [sprint-E4-registry-ux.md](./sprint-E4-registry-ux.md)

---

## Sprint E5: PyPI Distribution

**Goal**: Publish asap-protocol 2.1.0 to PyPI; CI on tag

**Depends on**: Sprints E1–E4 complete

| Task | Sub-tasks | Est. |
|------|-----------|------|
| 5.1 | Bump version to 2.1.0 | 0.5d |
| 5.2 | PyPI publish GitHub Action | 1d |
| 5.3 | Verify optional dependency groups | 0.5d |
| 5.4 | CHANGELOG and release notes | 0.5d |

**Definition of Done**: `pip install asap-protocol` and `pip install asap-protocol[mcp]` work; tag triggers publish.

**Detail**: [sprint-E5-pypi-distribution.md](./sprint-E5-pypi-distribution.md)

---

## Summary

| Sprint | Focus | Sub-tasks | Est. Days |
|--------|-------|-----------|-----------|
| E1 | Trust & Revocation | 13 | 4–5 |
| E2 | Consumer SDK Core | 11 | 4–5 |
| E3 | Framework Integrations | 12 | 5–6 |
| E4 | Registry UX | 13 | 4–5 |
| E5 | PyPI Distribution | 6 | 2–3 |

**Total**: 55 sub-tasks across 5 sprints, ~19–24 days

---

## Dependency Graph

```
E1 (Trust & Revocation)
 ├── E2 (Consumer SDK)
 │    └── E3 (Framework Integrations)
 └── E4 (Registry UX) — 4.6 needs E1 for revoked_agents.json

E2, E3, E4 ──► E5 (PyPI)
```

---

## Related Documents

- **PRD**: [prd-v2.1-ecosystem.md](../../../product-specs/prd/prd-v2.1-ecosystem.md)
- **ADR-24**: MCP Python vs npm (05-product-strategy.md)
- **ADR-25**: SDK cache strategy (04-technology.md)
- **Next**: [prd-v2.2-scale.md](../../../product-specs/prd/prd-v2.2-scale.md)
