# ASAP thin starters (v2.5.4)

Thin wrappers around the canonical parent examples and apps. Prefer these entrypoints for a fast smoke; use the parent paths for the full implementation.

For the adoption path (discover → execute → escalate), see [Build for Agents](../../docs/guides/build-for-agents.md).

## Starters

| Starter | Path | Parent | Docs |
|---------|------|--------|------|
| OpenAPI provider | [`openapi-provider/`](./openapi-provider/) | [`examples/openapi_petstore/`](../openapi_petstore/) | [`docs/adapters/openapi.md`](../../docs/adapters/openapi.md) |
| TypeScript consumer | [`typescript-consumer/`](./typescript-consumer/) | [`apps/example-nextjs/`](../../apps/example-nextjs/) | [`docs/sdks/typescript.md`](../../docs/sdks/typescript.md) |
| MCP Auth Bridge | [`mcp-auth-bridge/`](./mcp-auth-bridge/) | [`examples/mcp_auth_bridge/`](../mcp_auth_bridge/) | [`docs/adapters/mcp-auth-bridge.md`](../../docs/adapters/mcp-auth-bridge.md) |

## Design

Each starter is a short script that invokes the parent via subprocess (or a thin Node CLI for TypeScript). Parent trees remain the source of truth—do not treat starter directories as a second copy of OpenAPI fragments, server code, or Next.js apps.
