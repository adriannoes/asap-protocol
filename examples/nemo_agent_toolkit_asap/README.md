# NeMo Agent Toolkit ↔ ASAP (Path A) — experimental local demo

**Status:** experimental / maintainer-reproducible spike (ASAP v2.5.3 S1c Path A).  
**Not** a production integration and **not** published as an NVIDIA NAT plugin.

## What this proves

| Layer | Behavior |
|-------|----------|
| Transport | NAT `mcp_client` **stdio** → ASAP `protect_server` stdio (`asap_mcp_server.py`) |
| Tools | Public `echo`; protected `secure_action` (grant + Agent JWT) |
| Auth carriage | NAT does **not** send `_meta.asap_agent_jwt`. The ASAP child **mints** a demo Agent JWT and sets `ASAP_AGENT_JWT` (`allow_env_jwt_fallback=True`, same idea as `examples/mcp_auth_bridge/`) |

## Honest auth note

- **Dev-only env JWT fallback.** Suitable for a single-agent local demo.
- **Not** production Host/Agent JWT minting or multi-tenant isolation.
- **NAT OAuth2 / Keycloak / `mcp_oauth2` ≠ ASAP Agent JWT + capability grants.** Do not wire Keycloak for this example.
- Streamable-http / HTTP MCP Auth Bridge is **out of scope** here — see [backlog-mcp-auth-typescript.md](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md).
- `asap_mcp_server.py` routes ASAP structlog to **stderr** before `run_stdio`. With `ASAP_AGENT_JWT` set, auth log lines would otherwise land on **stdout** and corrupt MCP JSON-RPC (breaks NAT `mcp_client` / ASAP `MCPClient`).

Research decision: [research-nemo-agent-toolkit.md](../../engineering/tasks/v2.5.3/research-nemo-agent-toolkit.md) §10.3.

## Prerequisites

- **Python 3.13** only for the joint example (ASAP ∩ `nvidia-nat` 1.8.x)
- [uv](https://github.com/astral-sh/uv)
- ASAP repo checkout with dependencies:

```bash
uv sync
```

Optional (full NAT workflow only):

```bash
uv pip install -r examples/nemo_agent_toolkit_asap/requirements.txt
```

Pin: **`nvidia-nat[mcp]==1.8.0`** (optional path; **not** a required ASAP core dep). The `a2a` extra is not required for Path A.

**NIM / `NVIDIA_API_KEY`:** only needed for `nat run` with the sample `react_agent` YAML. Prefer the **ASAP-side smoke** below (no LLM).

## Layout

| Path | Role |
|------|------|
| `asap_mcp_server.py` | Stdio MCP server; reuses `examples/mcp_auth_bridge/`; injects `ASAP_AGENT_JWT` |
| `smoke_asap_side.py` | Headless ASAP proof (no `nvidia-nat`) |
| `configs/config-mcp-client-stdio.yml` | NAT `mcp_client` stdio → ASAP server |
| `requirements.txt` | Optional NAT pin |
| `.env.example` | Placeholders only |
| `run_demo.sh` | Launcher: ASAP smoke, optional `nat run` |

## Commands

### 1. ASAP-side smoke (recommended happy path — no NAT, no NIM)

From the repository root:

```bash
uv run python examples/nemo_agent_toolkit_asap/smoke_asap_side.py
```

Includes stdio subprocess (server injects JWT; client calls without `_meta`):

```bash
uv run python examples/nemo_agent_toolkit_asap/smoke_asap_side.py --stdio
```

Or:

```bash
./examples/nemo_agent_toolkit_asap/run_demo.sh smoke
./examples/nemo_agent_toolkit_asap/run_demo.sh smoke-stdio
```

Pytest (always runs ASAP side; does not require `nvidia-nat`):

```bash
uv run pytest tests/examples/test_nemo_agent_toolkit_asap.py -v
```

### 2. Run the ASAP stdio server alone

```bash
uv run python examples/nemo_agent_toolkit_asap/asap_mcp_server.py
```

Negative control (no env JWT injection — protected calls need `_meta` or a pre-set env):

```bash
uv run python examples/nemo_agent_toolkit_asap/asap_mcp_server.py --no-env-jwt
```

### 3. Full NAT path (optional — requires NIM)

Install NAT, set `NVIDIA_API_KEY`, run from **repo root** so `uv run python examples/...` resolves:

```bash
uv pip install -r examples/nemo_agent_toolkit_asap/requirements.txt
export NVIDIA_API_KEY='your-key'   # never commit
nat run --config_file examples/nemo_agent_toolkit_asap/configs/config-mcp-client-stdio.yml \
  --input "Call echo with message hello, then secure_action with action demo"
```

Or:

```bash
./examples/nemo_agent_toolkit_asap/run_demo.sh nat
```

If `nat` is missing, the script exits with a clear skip message (does not fail ASAP CI).

## Negative path

| Condition | Expected |
|-----------|----------|
| `secure_action` without JWT (no env, no `_meta`) | `asap:auth_required` |
| Valid JWT but no grant / wrong capability | `asap:capability_denied` (see mcp_auth_bridge docs) |

Smoke covers the auth_required case. Grant denial semantics: [docs/adapters/mcp-auth-bridge.md](../../docs/adapters/mcp-auth-bridge.md).

## HTTP / streamable-http gap

ASAP `protect_server` is **stdio Mode A**. NAT OAuth examples use **streamable-http**. Bridging those without inventing a protocol fork is deferred — pointer: [engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md](../../engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md).

## Related

- Public interop guide: [`docs/integrations/nemo-agent-toolkit.md`](../../docs/integrations/nemo-agent-toolkit.md)
- Reference server/client: [`examples/mcp_auth_bridge/`](../mcp_auth_bridge/)
- Adapter guide: [`docs/adapters/mcp-auth-bridge.md`](../../docs/adapters/mcp-auth-bridge.md)
- Sprint: [`engineering/tasks/v2.5.3/sprint-S1c-nemo-agent-toolkit.md`](../../engineering/tasks/v2.5.3/sprint-S1c-nemo-agent-toolkit.md)
