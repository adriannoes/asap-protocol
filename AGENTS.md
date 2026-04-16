# AGENTS.md

> **Context Map for AI Agents**. Use this file to locate project knowledge.
> **Rules Enforcement**: Strictly follow all active `.cursor/rules/*.mdc`.

## Project Context

**ASAP Protocol** (Async Simple Agent Protocol) is a production-ready standard for agent-to-agent communication.
- **Stack**: Python 3.13+, FastAPI, Pydantic v2.
- **Transport**: JSON-RPC 2.0 over HTTP/WebSocket.
- **Status**: v2.2.0 (Released).
- **Framework Integrations**: LangChain, CrewAI, PydanticAI, LlamaIndex, SmolAgents, Vercel AI SDK, MCP, OpenClaw, A2H.

## Quick Start

```bash
uv sync                                     # Install dependencies
uv run pytest                               # Run tests (add -v for verbose)
uv run uvicorn asap.transport.server:app --reload  # Start dev server
uv run mypy src/ scripts/ tests/ && uv run ruff check src/  # Verify quality
```

## Knowledge Map

### 1. Product & Architecture (Read First)
- **Vision & Roadmap**: `.cursor/product-specs/strategy/`
- **Feature Specs (PRDs)**: `.cursor/product-specs/prd/`
- **Arch Decisions (ADRs)**: `.cursor/product-specs/decision-records/`
- **Tech Stack**: `.cursor/dev-planning/architecture/tech-stack-decisions.md`

### 2. Development Status
- **Active Sprint**: `.cursor/dev-planning/tasks/`
- **Checkpoints**: `.cursor/dev-planning/checkpoints.md`
- **Code Reviews**: `.cursor/dev-planning/code-review/`

## Organization

### Project Structure
```text
src/asap/
├── models/        # Data models (Envelope, TaskRequest, TaskStream)
├── auth/          # OAuth2/OIDC, Agent Identity, Capabilities, Approval
├── transport/     # HTTP Client/Server, WebSocket, SSE Streaming
├── state/         # Async persistence (AsyncSnapshotStore/AsyncMeteringStore)
├── handlers/      # Task processing logic
├── economics/     # Metering, Delegation, SLA
└── discovery/     # Manifests, Health, Lite Registry
```

### AI Toolbox (Available Capabilities)
- **Rules**: `.cursor/rules/*.mdc` (Auto-loaded context)
- **Commands**: `.cursor/commands/` (Workflows like `create-prd`, `generate-tasks`)
- **Skills**: `.cursor/skills/` (Specialized agents for Security, Reviews)
- **Web E2E**: `apps/web/docs/playwright-e2e.md` — Playwright browser path troubleshooting

## Key Architectural Patterns

1.  **Envelope Protocol**: All messages wrapped in `Envelope[T]` (`models/envelope.py`).
2.  **State Machine**: Tasks strictly follow `PENDING → RUNNING → COMPLETED` (`models/files.py`).
3.  **Circuit Breaker**: Transport reliability logic (`transport/http_client.py`).
4.  **Agent Identity**: Per-runtime Ed25519 identity with Host/Agent JWT (`auth/agent_jwt.py`).
5.  **Capability AuthZ**: Constraint-based capability grants (`auth/capabilities.py`).

## Security Context

- **Auth**: OAuth2/OIDC for agent-to-agent (ADR-17); Agent Identity with Host/Agent JWT (v2.2).
- **Identity**: Ed25519 Signed Manifests (v1.2); Per-runtime agent identity with JWK thumbprint (v2.2).
- **Capabilities**: Constraint-based authorization with approval flows (v2.2).
- **Transport**: mTLS optional (v1.2); ASAP-Version negotiation (v2.2).
- **Compliance**: `asap-compliance` package validates specs.
