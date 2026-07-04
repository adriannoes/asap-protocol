# AGENTS.md

> **Context Map for AI Agents**. Use this file to locate project knowledge.
> **Rules Enforcement**: Strictly follow all active `.cursor/rules/*.mdc`.
> **Agent index**: [`.cursor/README.md`](.cursor/README.md) — precedence, canonical commands, rules vs skills.

## Project Context

**ASAP Protocol** (Async Simple Agent Protocol) is a production-ready standard for agent-to-agent communication.
- **Stack**: Python 3.13+, FastAPI, Pydantic v2.
- **Transport**: JSON-RPC 2.0 over HTTP/WebSocket.
- **Status**: v2.5.1 shipped on `main` (2026-06-26). **Current versions:** `pyproject.toml` **2.5.1** · PyPI `asap-protocol` **2.5.1** (tag [`v2.5.1`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.1)) · PyPI `asap-compliance` **1.3.0** (tag [`v2.5.0.1`](https://github.com/adriannoes/asap-protocol/releases/tag/v2.5.0.1)) · npm `@asap-protocol/client` **2.4.1**. v2.5.1 is a behavior-preserving **code quality patch** (thermo-nuclear audit S0–S3 + P0 fixes); **Adapter Lab II slipped to v2.5.2**. See `CHANGELOG.md` `[2.5.1]` and `docs/migration.md#upgrading-from-v250-to-v251`.
- **Framework Integrations**: LangChain, CrewAI, PydanticAI, LlamaIndex, SmolAgents, Vercel AI SDK, MCP (envelope + **MCP Auth Bridge** v2.5.0), OpenClaw, A2H.
- **npm (TypeScript)**: The official client is **`@asap-protocol/client`** (scoped, **public** on npm for v2.4.x). Maintainer workflow: `.github/workflows/publish-typescript.yml`; context: `docs/maintainers/npm-publishing.md`.
- **General contact** (humans coordinating on the protocol; not security): [info@asap-protocol.com](mailto:info@asap-protocol.com) — vulnerabilities: [SECURITY.md](SECURITY.md).

## Quick Start

```bash
uv sync                                     # Install dependencies
uv run pytest -n auto --tb=short            # Fast test run (CI-parity)
uv run uvicorn asap.transport.server:app --reload  # Start dev server
uv run mypy src/ scripts/ tests/ && uv run ruff check src/  # Verify quality
```

For coverage and pre-push gates, see [`.cursor/README.md`](.cursor/README.md#canonical-commands).

## Agent Guidance (rules vs skills)

| I need to… | Read |
|------------|------|
| Run tests or check coverage | [`.cursor/README.md`](.cursor/README.md#canonical-commands) + `testing-standards.mdc` |
| Test rate-limited endpoints / fix 429 flakes | `testing-rate-limiting.mdc` → `skills/testing-rate-limiting/SKILL.md` |
| Write or refactor code | `agent-clean-code.mdc` |
| Choose where new code lives | `architecture-principles.mdc` |
| Commit or push | `git-commits.mdc` (always on) |
| Frontend (`apps/web/`) | `frontend-best-practices.mdc` |
| Security audit | `skills/security-review/SKILL.md` |
| Security PR review (high-confidence) | `.cursor/commands/security-pr-review.md` |
| Code quality review | `skills/code-quality-review/SKILL.md` |

**Precedence:** user rules → always-on rules → scoped/requestable rules → skills → commands → docs. Details in [`.cursor/README.md`](.cursor/README.md).

## Knowledge Map

### 1. Product & Architecture (Read First)
- **Vision & Roadmap**: ADRs and PRDs (`product/decision-records/`, `product/prd/`). Narrative vision files under `product/strategy/` are **local-only** (ignored on the remote).
- **Feature Specs (PRDs)**: `product/prd/`
- **Arch Decisions (ADRs)**: `product/decision-records/`
- **Documentation checkpoints** (post-release PRD follow-up): `product/checkpoints.md`
- **Tech Stack**: `engineering/architecture/tech-stack-decisions.md`
- **MCP Auth Bridge**: `asap.adapters.mcp` (`protect_server`, `MCPAuthConfig`) — [docs/adapters/mcp-auth-bridge.md](docs/adapters/mcp-auth-bridge.md)

### 2. Development Status
- **Active Sprint**: `engineering/tasks/`
- **Adoption Roadmap**: v2.5.1 **code quality patch** shipped (2026-06-26, tag `v2.5.1`); v2.5.0 **MCP Auth Bridge** shipped (2026-06-24); `asap-compliance` **1.3.0** on PyPI (tag `v2.5.0.1`); **Adapter Lab II next as v2.5.2**; `@asap-protocol/mcp-auth` (HTTP/SSE) still deferred.
- **Code Reviews**: `engineering/code-review/`

## Organization

### Project Structure
```text
src/asap/
├── adapters/      # Third-party wire adapters (OpenAPI, MCP auth bridge)
├── models/        # Data models (Envelope, TaskRequest, TaskStream)
├── auth/          # OAuth2/OIDC, Agent Identity, Capabilities, Approval
├── transport/     # HTTP Client/Server, WebSocket, SSE Streaming
├── state/         # Async persistence (AsyncSnapshotStore/AsyncMeteringStore)
├── handlers/      # Task processing logic
├── economics/     # Metering, Delegation, SLA
└── discovery/     # Manifests, Health, Lite Registry
```

### AI Toolbox (Available Capabilities)
- **Agent index**: [`.cursor/README.md`](.cursor/README.md) — start here for rules, skills, and commands
- **Rules**: `.cursor/rules/*.mdc` (auto-loaded or requestable by glob)
- **Commands**: `.cursor/commands/` (Workflows like `create-prd`, `generate-tasks`, `security-pr-review`)
- **Skills**: `.cursor/skills/` (Security review, code quality, rate-limit testing)
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

## Cursor Cloud specific instructions

The VM update script already installs dependencies (`uv sync --all-extras --dev` at the repo root and `npm ci` in `apps/web`). `uv` lives in `~/.local/bin` and is on `PATH` via `~/.profile`/`~/.bashrc`. Python 3.13 is required and managed by `uv` (system `python3` is 3.12; always use `uv run`). Standard commands live in `AGENTS.md` Quick Start and [`.cursor/README.md`](.cursor/README.md#canonical-commands) — reference those rather than duplicating.

Two independent products, testable in isolation (the web app is not wired to the local Python server):

- **Python backend** (`asap-protocol`): dev server `uv run uvicorn asap.transport.server:app --reload` (port 8000). Non-obvious: the JSON-RPC endpoint is `POST /asap` (there is no `/asap/rpc`); health is `GET /health`. Quick smoke test uses method `asap.send` with an envelope whose payload is a `task.request` (see `tests/transport/integration/test_server_core.py` for the exact envelope shape); the built-in `echo` skill returns a `task.response`. No database/Redis needed (in-memory/SQLite by default).
- **Web app** (`apps/web`): dev server `npm run dev` (binds `127.0.0.1:3000`). Non-obvious: `apps/web` is a standalone **npm** project (own `package-lock.json`), separate from the root **pnpm** workspace — do not run it through pnpm. It needs `apps/web/.env.local` (gitignored; copy from `.env.example`); for local dev set `REGISTRY_URL=http://127.0.0.1:3000/registry.json` (served from `public/registry.json`) and a placeholder `AUTH_SECRET`. There is no local `revoked_agents.json` file — a 404 on `REVOKED_URL` is expected and harmless. Playwright E2E needs `npx playwright install`; see `apps/web/docs/playwright-e2e.md` for sandbox browser-path issues.
