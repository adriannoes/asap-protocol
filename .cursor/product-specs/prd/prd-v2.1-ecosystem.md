# PRD: ASAP Protocol v2.1.0 — Ecosystem Enablement

> **Product Requirements Document**
>
> **Version**: 2.1.0
> **Status**: APPROVED
> **Created**: 2026-02-25
> **Last Updated**: 2026-02-25

---

## 1. Executive Summary

### 1.1 Purpose

While v2.0.0 focused on the **supply side** (agent providers registering via IssueOps), v2.1.0 focuses on **demand-side activation** and **ecosystem enrichment**. This release delivers:

- **Consumer SDK**: Python SDK for resolving, trusting, and executing agents from the Lite Registry
- **Framework Integrations**: Native wrappers for LangChain, CrewAI, PydanticAI, and MCP (Claude Desktop, Cursor)
- **Registry UX**: Category/Tags filtering and Agent Revocation for a cleaner, more navigable registry
- **PyPI Distribution**: First official public release of `asap-protocol` to PyPI

> [!NOTE]
> The former `prd-v2.1-consumers.md` is superseded by this document, which adds the Registry UX and PyPI scope. The original Consumer SDK requirements are fully preserved and expanded here.

### 1.2 Strategic Context

```
v2.0 (supply side) → v2.1 (demand side) → v2.2 (scale) → v3.0 (economy)
Providers register    Consumers use SDK    Registry API   Monetization
```

If consumers cannot connect their "Brains" (LLMs) to our "Shells" (agents), the marketplace is a directory, not an ecosystem. v2.1 removes that friction.

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Consumer DX | < 5 lines of code to invoke an agent via SDK | P1 |
| Secure Consumption | 100% of SDK connections auto-validate Ed25519 signatures | P1 |
| Ecosystem Fit | Out-of-the-box Tool bindings for LangChain, CrewAI, MCP | P1 |
| PyPI Presence | `pip install asap-protocol` publicly available | P1 |
| Registry UX | Category/Tags filterable in Browse; revocation IssueOps flow | P2 |

---

## 3. User Stories

### Independent Python Developer
> As a **Python developer**, I want to **`pip install asap-protocol`** so that **I can resolve an agent's URN, validate its trust badge, and `await` a response in 3 lines of code**.

### AI Orchestrator Architect
> As a **developer using CrewAI**, I want to **import a `CrewAIAsapTool`** so that **my agent can delegate tasks to ASAP Marketplace agents without custom HTTP/WebSocket code**.

### Claude Desktop User
> As a **Claude Desktop user**, I want to **install `asap-mcp-server`** so that **I can query and execute remote ASAP agents as native MCP Tools without writing any code**.

### Strict Security Consumer
> As an **enterprise consumer**, I want the **SDK to automatically fail if an agent has been revoked**, so that **I don't execute compromised agents whose signatures are technically still valid**.

### Registry Browser
> As a **developer browsing the marketplace**, I want to **filter agents by category and tags** so that **I quickly find agents relevant to my domain**.

---

## 4. Functional Requirements

### 4.1 Consumer SDK — Core (P1)

All integrations ship in the `asap-protocol` core package (ADR-24).

| ID | Requirement | Priority |
|----|-------------|----------|
| SDK-001 | `asap.client.MarketClient.resolve(urn: str)` fetches Agent Manifest from Lite Registry | MUST |
| SDK-002 | `agent.run(payload: dict)` orchestrates WebSocket/HTTP handshake automatically | MUST |
| SDK-003 | Registry cache: `registry.json` cached 5 min (configurable `ASAP_REGISTRY_CACHE_TTL`). `revoked_agents.json` always fresh (ADR-25) | MUST |
| DOC-001 | Document "Raw Fetch" path (fetching GitHub Pages JSON directly) for non-Python languages | MUST |

**Developer Experience Target**:
```python
import asyncio
from asap.client import MarketClient

async def main():
    client = MarketClient()
    # 1. Resolves URN from registry.json (cached 5 min)
    # 2. Fetches remote manifest
    # 3. Validates Ed25519 signature automatically
    # 4. Checks revoked_agents.json (always fresh)
    agent = await client.resolve("urn:asap:example:math-agent")
    result = await agent.run({"operation": "add", "a": 5, "b": 10})
    print(result)

asyncio.run(main())
```

---

### 4.2 Built-in Trust Validation (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-001 | `verify_agent_trust(manifest)` validates Ed25519 signature using ASAP CA public key (JCS + RFC 8032) | MUST |
| SEC-002 | `resolve()` raises `SignatureVerificationError` if manifest signature is invalid | MUST |
| SEC-003 | SDK embeds the ASAP CA Public Key to verify `Verified` agents locally (no network call for the key itself) | MUST |
| SEC-004 | SDK fetches `revoked_agents.json` before every `run()` — no cache — and raises `AgentRevokedException` if URN matches | MUST |

---

### 4.3 Framework & Ecosystem Integrations (P1/P2)

All wrappers live inside `asap-protocol` core (`src/asap/integrations/`).

#### The "Pro-Code" Path (AI Frameworks)

| ID | Requirement | Priority |
|----|-------------|----------|
| INT-001 | **LangChain**: `LangChainAsapTool(urn: str)` — inherits `BaseTool`, maps agent Pydantic schema to `args_schema` | MUST |
| INT-002 | **CrewAI**: `CrewAIAsapTool(urn: str)` — compatible with CrewAI's BaseTool | MUST |
| INT-003 | **PydanticAI**: Native integration leveraging ASAP's Pydantic schema validation | SHOULD |
| INT-006 | Any LLM tool wrapper must execute the standard ASAP Handshake and return result sync or async | MUST |

#### The "Tooling" Path (Protocols)

| ID | Requirement | Priority |
|----|-------------|----------|
| INT-007 | **MCP Server** (`asap-mcp-server`): Python package (`asap-protocol[mcp]`), installable via `uvx asap-mcp-server`, exposes ASAP agents as MCP Tools (Claude Desktop, Cursor IDE). See **ADR-24**. | MUST |

---

### 4.4 Economy & Quotas (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| ECO-001 | SDK handles HTTP 429 with exponential backoff (honors `Retry-After` header) | MUST |
| ECO-002 | SDK supports `Authorization: Bearer <token>` passthrough for agents with proprietary auth | MUST |

---

### 4.5 Registry UX — Category/Tags (P2)

Supersedes deferred item §6 in `deferred-backlog.md`.

| ID | Requirement | Priority |
|----|-------------|----------|
| CAT-001 | Extend `RegistryEntry` with optional `category: str \| None` and `tags: list[str]` | MUST |
| CAT-002 | Add `category` dropdown and `tags` input to GitHub Issue registration template | SHOULD |
| CAT-003 | `process_registration.py` parses and writes `category`/`tags` to `registry.json` | SHOULD |
| CAT-004 | Web App Browse page: filter controls for category and tags | SHOULD |

**Proposed categories** (non-exhaustive): `Research`, `Coding`, `Productivity`, `Data`, `Security`, `Infrastructure`, `Creative`, `Finance`.

---

### 4.6 Agent Revocation (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| REV-001 | Create `revoked_agents.json` at repo root — list of revoked URNs with reason and revocation date | MUST |
| REV-002 | IssueOps flow: `revoke-agent` labeled issue triggers Action to append to `revoked_agents.json` | MUST |
| REV-003 | SDK: `resolve()` checks `revoked_agents.json` (always fresh, no cache) before returning agent | MUST |
| REV-004 | Web App: revoked agents show "Revoked" badge and are excluded from search results | SHOULD |

---

### 4.7 PyPI Distribution (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| PKG-001 | Publish `asap-protocol` to PyPI with all v2.1 features | MUST |
| PKG-002 | Semantic versioning: `2.1.0` | MUST |
| PKG-003 | Optional dependency groups: `asap-protocol[mcp]`, `asap-protocol[langchain]`, `asap-protocol[crewai]` | MUST |
| PKG-004 | CI: GitHub Action to auto-publish to PyPI on tag push (`v*`) | MUST |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Registry API Backend (PostgreSQL) | Trigger not met (< 500 real agents) | v2.2 |
| Node.js / Go SDKs | Python commands the AI orchestrator market | TBD |
| AutoGen / OpenAI Swarm integrations | Lower priority — address with demand data | v2.2 |
| Economy Settlement / Built-in Paywalls | No live marketplace transactions yet | v3.0 |
| Auto-registration without PR | Spam risk; IssueOps sufficient | v2.2 |
| Audit Logging (formal, tamper-evident) | No enterprise customer yet | v2.2+ |

---

## 6. Technical Considerations

### 6.1 Code Structure

```
src/asap/
├── client/
│   ├── __init__.py          # MarketClient public API
│   ├── market.py            # resolve() + run() orchestration
│   ├── trust.py             # verify_agent_trust, SignatureVerificationError
│   ├── revocation.py        # revoked_agents.json check (no cache)
│   └── cache.py             # Registry cache (TTL, configurable)
├── integrations/
│   ├── __init__.py
│   ├── langchain.py         # LangChainAsapTool
│   ├── crewai.py            # CrewAIAsapTool
│   └── pydanticai.py        # PydanticAI binding (SHOULD)
└── mcp/
    ├── __init__.py           # asap-mcp-server entry point
    └── server.py             # FastMCP server exposing ASAP agents
```

### 6.2 Cryptographic Notes

Reuse existing `src/asap/crypto/trust.py` — `verify_ca_signature` function. The Consumer SDK wraps this without adding new cryptographic implementations (DRY principle, RFC 8032 already enforced).

### 6.3 New Dependencies

| Package | Purpose | Optional Group |
|---------|---------|----------------|
| `mcp>=1.0` | MCP Python SDK (FastMCP) | `[mcp]` |
| `langchain-core>=0.2` | `BaseTool` interface | `[langchain]` |
| `crewai>=0.80` | CrewAI BaseTool | `[crewai]` |

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| PyPI installs first week | 100+ |
| Time to First Call (TTFC) | < 2 min from landing page snippet |
| Framework integration usage | Evidence of LangChain/CrewAI production use |
| `asap-mcp-server` adoption | Mentioned in community MCP server lists |
| Agents with category/tags | 80% of new registrations |

---

## 8. Open Questions

- **Q1**: Should the `revoked_agents.json` be signed (to prevent tampering of the revocation list itself)? Initially no — future consideration for v2.2 if adversarial scenarios emerge.
- **Q2**: Should `asap-protocol[langchain]` auto-install `langchain-core` or require it as a peer dependency (to avoid version conflicts)?

---

## 9. Related Documents

- **Supersedes**: The original `prd-v2.1-consumers.md` PRD scope.
- **Tasks**: [tasks-v2.1.0-roadmap.md](../../dev-planning/tasks/v2.1.0/tasks-v2.1.0-roadmap.md) — 6 sprints (E1–E6), roadmap + detailed sprint files
- **Decision Records**: [ADR-24](../decision-records/05-product-strategy.md) (MCP Python vs npm), [ADR-25](../decision-records/04-technology.md) (SDK cache strategy)
- **Deferred Backlog**: [deferred-backlog.md](../strategy/deferred-backlog.md)
- **Roadmap**: [roadmap-to-marketplace.md](../strategy/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../strategy/vision-agent-marketplace.md)
- **Next Version**: [prd-v2.2-scale.md](./prd-v2.2-scale.md)

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-02-25 | 1.0.0 | Initial PRD — consolidates prd-v2.1-consumers.md + Registry UX + PyPI + ADR-24/25 decisions |
