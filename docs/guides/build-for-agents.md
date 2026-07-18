# Build for agents

> The next users of software are agents. ASAP gives them the machine-readable foundation they need: discoverable capabilities, scoped identity, compliance checks, and SDKs that turn existing APIs into agent-ready interfaces.

**Audience:** API providers and agent/app builders.  
**Status:** Maintained (v2.5.4 Distribution Loop). This guide is the public onboarding path into runnable starters and the adapters/SDKs behind them.

## Who this is for

| You are… | Start here |
|----------|------------|
| An **API provider** exposing HTTP/OpenAPI services to agents | [OpenAPI provider starter](#1-openapi-provider) → [OpenAPI adapter](../adapters/openapi.md) |
| An **app/agent builder** calling ASAP from TypeScript | [TypeScript consumer starter](#2-typescript-consumer) → [TypeScript SDK](../sdks/typescript.md) |
| Integrating **native MCP** with ASAP identity and grants | [MCP Auth Bridge starter](#3-mcp-auth-bridge) → [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) |
| New to ASAP agents end-to-end | [Building Your First Agent](../tutorials/first-agent.md) |

## Adoption path

1. **Discover** — advertise capabilities via manifests and (optionally) the Lite Registry.
2. **Execute** — call skills over ASAP transport with typed envelopes and scoped identity.
3. **Escalate** — request stronger approval or narrower grants when a capability needs it.

Thin starters under [`examples/starters/`](../../examples/starters/) wrap the canonical parent examples and apps. Prefer the starters for a fast smoke; use the parent paths for the full implementation.

## Thin starters

Starters are not a second source of truth. Each is a short entrypoint that re-invokes a parent demo. Run smokes from the **repository root** unless a starter README says otherwise.

### 1. OpenAPI provider

Turn an OpenAPI 3.x fragment into ASAP skills and an upstream proxy.

| | |
|--|--|
| Starter | [`examples/starters/openapi-provider/`](../../examples/starters/openapi-provider/) |
| Parent | [`examples/openapi_petstore/`](../../examples/openapi_petstore/) |
| Docs | [OpenAPI adapter](../adapters/openapi.md) |

```bash
uv sync --extra openapi
uv run python examples/starters/openapi-provider/run.py
```

Default smoke uses a **mocked** upstream (offline-friendly). Optional `--live` hits the public PetStore over **HTTPS**; the remote service may error — prefer the mock path for CI.

### 2. TypeScript consumer

Prove Host/Agent identity and consumer APIs with `@asap-protocol/client` without scaffolding a second web app.

| | |
|--|--|
| Starter | [`examples/starters/typescript-consumer/`](../../examples/starters/typescript-consumer/) |
| Parent patterns | [`apps/example-nextjs/`](../../apps/example-nextjs/) |
| Docs | [TypeScript SDK](../sdks/typescript.md) |

```bash
pnpm install
pnpm --filter @asap-protocol/client run build
npm install --prefix examples/starters/typescript-consumer
node examples/starters/typescript-consumer/smoke.mjs
```

Default smoke is **offline** (no API keys, no live gateway). Optional live discovery uses `ASAP_PROVIDER_URL` — set an **HTTPS** provider base URL for remote hosts; plain `http://` is acceptable only for local loopback. Do not commit real tokens; use env placeholders from the starter `.env.example`.

### 3. MCP Auth Bridge

Wrap a native stdio `MCPServer` with Agent JWT verification and capability grants (Mode A).

| | |
|--|--|
| Starter | [`examples/starters/mcp-auth-bridge/`](../../examples/starters/mcp-auth-bridge/) |
| Parent | [`examples/mcp_auth_bridge/`](../../examples/mcp_auth_bridge/) |
| Docs | [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) |

```bash
uv sync
uv run python examples/starters/mcp-auth-bridge/run.py
```

Do **not** pass JWTs on the CLI (`argv` leaks secrets). Prefer least-privilege grants: public tools for non-sensitive reads only; protect mutating tools with Agent JWT and narrow capability constraints. See the parent README and [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) for production warnings (`allow_env_jwt_fallback` is demo-only).

## Deeper docs

| Topic | Link |
|-------|------|
| OpenAPI → ASAP skills | [OpenAPI adapter](../adapters/openapi.md) |
| MCP Mode A protection | [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) |
| Browser / Node client | [TypeScript SDK](../sdks/typescript.md) |
| Echo agent walkthrough | [Building Your First Agent](../tutorials/first-agent.md) |
| Compliance checks | [Compliance Testing](compliance-testing.md) |
| Connector security baseline | [Automation connector security](automation-connector-security.md) |

## Security notes

| Concern | Practice |
|---------|----------|
| **Secrets** | Load tokens and keys from the environment or a secrets manager. Never commit `.env` values or paste JWTs into READMEs/CI logs. |
| **HTTPS/TLS** | Use `https://` for remote providers, upstream APIs, and advertised manifest origins. Local loopback HTTP is fine for demos. Prefer `require_https=True` on ASAP HTTP clients in production — [Security Guide](../security.md). |
| **Least privilege** | Grant only the skills and constraints each agent needs. Map mutating verbs to stronger approval where appropriate — [Capabilities](../capabilities/index.md). |

## See also

- [Starters index](../../examples/starters/) (`examples/starters/`)
- [Docs home](../index.md)
- [MCP integration overview](../mcp-integration.md)
