# ASAP Protocol Examples

This directory contains real-world examples for the ASAP protocol: minimal agents, demos, and patterns you can reuse.

## Overview

Examples cover:

- **Core flow**: Echo agent, coordinator, and a full demo (run_demo).
- **Advanced patterns**: Multi-agent orchestration, long-running tasks with checkpoints, error recovery, MCP integration, state migration, auth, rate limiting.
- **Concepts**: WebSocket (not implemented), streaming responses, multi-step workflows.

Run any example from the repository root with:

```bash
uv run python -m asap.examples.<module_name> [options]
```

## Running the full demo

Starts the echo agent on port 8001 and the coordinator on port 8000; the coordinator sends a TaskRequest to the echo agent and logs the response.

```bash
uv run python -m asap.examples.run_demo
```

**v1.4.0 Showcase** — Pagination on Usage and SLA history APIs:

```bash
uv run python -m asap.examples.v1_4_0_showcase
```

**v1.3.0 Showcase** — One command to run Delegation, Metering, and SLA together:

```bash
uv run python -m asap.examples.v1_3_0_showcase
```

Run agents individually:

- `uv run python -m asap.examples.echo_agent --host 127.0.0.1 --port 8001`
- `uv run python -m asap.examples.coordinator --echo-url http://127.0.0.1:8001`

---

## Examples by topic

### Core agents and demo

| Module | Description | Usage |
|--------|-------------|--------|
| **run_demo** | Full demo: echo + coordinator, one TaskRequest round-trip | `uv run python -m asap.examples.run_demo` |
| **v1_4_0_showcase** | v1.4.0 E2E: Pagination on Usage & SLA history APIs | `uv run python -m asap.examples.v1_4_0_showcase` |
| **v1_3_0_showcase** | v1.3.0 E2E: Delegation, Metering, SLA breach via WebSocket | `uv run python -m asap.examples.v1_3_0_showcase` |
| **echo_agent** | Minimal echo agent (FastAPI app, manifest, echo handler) | `uv run python -m asap.examples.echo_agent [--host H] [--port P]` |
| **coordinator** | Coordinator that dispatches TaskRequest to echo agent | `uv run python -m asap.examples.coordinator [--echo-url URL] [--message MSG]` |
| **secure_handler** | Reference handler: TaskRequest validation, FilePart URI checks, sanitize_for_logging | Use `create_secure_handler()` in your handler registry (see `docs/security.md`) |

### Multi-agent and orchestration

| Module | Description | Usage |
|--------|-------------|--------|
| **orchestration** | Main agent delegates to 2 sub-agents; task coordination and state tracking | `uv run python -m asap.examples.orchestration [--worker-a-url URL] [--worker-b-url URL]` (start two echo agents on 8001 and 8002 first) |

### State and long-running tasks

| Module | Description | Usage |
|--------|-------------|--------|
| **long_running** | Long-running task with checkpoints (StateSnapshot); save, “crash”, resume | `uv run python -m asap.examples.long_running [--num-steps N] [--crash-after N]` |
| **state_migration** | Move task state between agents (StateQuery, StateRestore, SnapshotStore) | `uv run python -m asap.examples.state_migration` |
| **agent_failover** | Failover demo: primary runs task, crashes; coordinator detects via health, sends StateRestore to backup | `uv run python -m asap.examples.agent_failover` |

### Error recovery and resilience

| Module | Description | Usage |
|--------|-------------|--------|
| **error_recovery** | Retry with backoff, circuit breaker, fallback patterns | `uv run python -m asap.examples.error_recovery [--skip-retry] [--skip-circuit] [--skip-fallback]` |

### MCP and integration

| Module | Description | Usage |
|--------|-------------|--------|
| **mcp_client_demo** | MCP client via stdio: start server subprocess, list tools, call echo | `uv run python -m asap.examples.mcp_client_demo` |
| **mcp_integration** | Call MCP tools via ASAP envelopes (McpToolCall, McpToolResult) | `uv run python -m asap.examples.mcp_integration [--agent-url URL]` (local build only if no URL) |

### Authentication and rate limiting

| Module | Description | Usage |
|--------|-------------|--------|
| **secure_agent** | OAuth2 server (OAuth2Config) + client (OAuth2ClientCredentials); Custom Claims env vars (v1.1) | `uv run python -m asap.examples.secure_agent --server` / `--client` |
| **auth_patterns** | Bearer auth, custom token validators, OAuth2 concept (manifest + create_app) | `uv run python -m asap.examples.auth_patterns` |
| **rate_limiting** | Per-sender and per-endpoint rate limit patterns (create_limiter, ASAP_RATE_LIMIT) | `uv run python -m asap.examples.rate_limiting` |

### Concepts (no full implementation)

| Module | Description | Usage |
|--------|-------------|--------|
| **websocket_concept** | How WebSocket would work with ASAP (comments/pseudocode only) | `uv run python -m asap.examples.websocket_concept` |

### Streaming and workflows

| Module | Description | Usage |
|--------|-------------|--------|
| **streaming_response** | Stream TaskUpdate progress chunks (simulated streaming) | `uv run python -m asap.examples.streaming_response [--chunks N]` |
| **multi_step_workflow** | Multi-step pipeline: fetch → transform → summarize (WorkflowState, run_workflow) | `uv run python -m asap.examples.multi_step_workflow` |

---

## Notes

- The echo agent exposes `/.well-known/asap/manifest.json` for readiness checks.
- Update ports in `asap.examples.run_demo` if you change the defaults.
- Examples use the basic ASAP API; for production, add authentication via `manifest.auth` and follow `docs/security.md`.
