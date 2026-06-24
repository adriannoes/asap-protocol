# MCP Auth Bridge reference example

Runnable demo of **Mode A** native MCP protection via `asap.adapters.mcp.protect_server`:

- **`echo`** — public tool (`public_tools`); no Agent JWT required.
- **`secure_action`** — protected; requires a valid Agent JWT, matching `capabilities` claim, and an active registry grant.

Keys and identities are generated **at runtime** (nothing committed to the repo).

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv)

From the repository root:

```bash
uv sync
```

## Run the server

```bash
uv run python examples/mcp_auth_bridge/server.py
```

On startup the server prints a **demo Agent JWT** and usage hints on **stderr** (stdout stays reserved for MCP JSON-RPC).

Help (does not start the stdio loop):

```bash
uv run python examples/mcp_auth_bridge/server.py --help
```

## Agent JWT flow

### 1. Host minting (production pattern)

In production the **host** signs Agent JWTs with its Ed25519 private key after the agent session is registered. This example inlines that flow in `server.py` using the same APIs as `tests/adapters/mcp/conftest.py`:

1. Register `HostIdentity` in `InMemoryHostStore`.
2. Register `AgentSession` in `InMemoryAgentStore`.
3. Mint with `create_agent_jwt(agent_sk, host_thumbprint=..., agent_id=..., aud=..., capabilities=[...])`.

The demo server prints one minted token on stderr for local testing.

### 2. Pass JWT on `tools/call`

MCP clients should attach the token under `_meta`:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "secure_action",
    "arguments": {"action": "ping"},
    "_meta": {"asap_agent_jwt": "<paste-token-from-stderr>"}
  }
}
```

`echo` ignores JWT even if present; `secure_action` rejects calls without a valid token (`asap:auth_required`).

### 3. Dev env fallback

When `MCPAuthConfig.allow_env_jwt_fallback=True` (enabled in this example for local docs only):

```bash
export ASAP_AGENT_JWT='<paste-token-from-stderr>'
```

The middleware reads `ASAP_AGENT_JWT` when `_meta.asap_agent_jwt` is absent. **Do not enable in production.**

## Optional client

Minimal stdio caller that lists tools, calls `echo`, then `secure_action` with `_meta`:

```bash
export ASAP_AGENT_JWT='<paste-token-from-server-stderr>'
uv run python examples/mcp_auth_bridge/client.py
```

Or pass the token explicitly:

```bash
uv run python examples/mcp_auth_bridge/client.py --jwt '<token>'
```

## Reviewer checklist

1. `uv run python examples/mcp_auth_bridge/server.py --help` → exit 0.
2. Start server; copy demo JWT from stderr.
3. Call `echo` without JWT → succeeds.
4. Call `secure_action` without JWT → `asap:auth_required`.
5. Call `secure_action` with `_meta.asap_agent_jwt` (or `ASAP_AGENT_JWT`) → `executed: ...`.

## Related docs

- Adapter guide: [`docs/adapters/mcp-auth-bridge.md`](../../docs/adapters/mcp-auth-bridge.md)
- Mode B (MCP-over-ASAP envelope): `src/asap/examples/mcp_integration.py`
- `initialize` session-token carriage: **deferred** (design-lock §3)
