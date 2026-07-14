# MCP Integration

This guide describes how to use the Model Context Protocol (MCP) with ASAP. The implementation follows **MCP spec 2025-11-25** and supports the stdio transport plus the tools feature (list and call).

## Overview

- **MCP server**: Exposes tools over stdio; clients (e.g. IDEs, Claude Desktop) launch the server as a subprocess and send JSON-RPC messages.
- **MCP client**: Connects to a server process, performs the initialize handshake, and can list tools and call them.

ASAP provides:

- `asap.mcp.MCPServer`: Build a server that exposes tools over stdio.
- `asap.mcp.MCPClient`: Connect to an MCP server (e.g. for tests or automation).
- Protocol types in `asap.mcp.protocol` (JSON-RPC, Initialize, Tool, CallToolResult, etc.).

## Integration modes (v2.5.0)

ASAP supports two complementary ways to combine MCP with agent communication. Pick the mode that matches your transport and auth surface.

| | **Mode A — Native stdio MCP** | **Mode B — MCP-over-ASAP envelope** |
|:--|:------------------------------|:------------------------------------|
| **Wire** | MCP JSON-RPC over stdio (`MCPServer` / `MCPClient`) | ASAP `Envelope` with `payload_type` `mcp_tool_call` / `mcp_tool_result` |
| **Typical use** | IDE hosts (Claude Desktop, Cursor) launch your server as a subprocess | A2A agents invoke MCP tools on a remote peer via HTTP/WebSocket |
| **Auth (v2.5.0)** | Opt-in via [`asap.adapters.mcp.protect_server`](adapters/mcp-auth-bridge.md) — Agent JWT + capability grants on each `tools/call` | Existing ASAP transport auth (Host/Agent JWT, capability grants on the HTTP server) |
| **Reference** | [`examples/mcp_auth_bridge/`](../examples/mcp_auth_bridge/) | [`src/asap/examples/mcp_integration.py`](../src/asap/examples/mcp_integration.py) (`McpToolCall` / `mcp_tool_call`) |

### Mode A: native stdio MCP + Auth Bridge

Use `asap.mcp.MCPServer` when a host application starts your process and speaks MCP over stdin/stdout. To enforce Agent JWT and capability grants on protected tools, wrap the server with `protect_server` from `asap.adapters.mcp` — see the **[MCP Auth Bridge adapter guide](adapters/mcp-auth-bridge.md)** for architecture, `MCPAuthConfig`, error codes, and a runnable example.

**Lab II Path A (experimental):** [NeMo Agent Toolkit](integrations/nemo-agent-toolkit.md) demonstrates NAT `mcp_client` (stdio) calling an ASAP-protected MCP server — see also [Automation connector security](guides/automation-connector-security.md) (§ Mode A vs Mode B). Workflow connectors that stay on OpenAPI/HTTP do not require MCP; see [Workflow connectors](integrations/workflow-connectors.md).

**Opt-in migration (MCP-DOC-004):** Unprotected `MCPServer` usage remains fully valid. Protection is explicit: call `protect_server` only when you want JWT + grant checks on `tools/call`. Existing deployments do not need to change until operators opt in.

**Deferred in v2.5.0:** An MCP `initialize` session-token handshake (negotiating a token once at connect instead of per-call `_meta`) is **not shipped** in this release — see [design lock §3](../engineering/tasks/v2.5.0/design-lock-mcp-auth-bridge.md). Clients must pass the Agent JWT on each protected `tools/call` via `_meta.asap_agent_jwt` until a future release adds session tokens.

### Mode B: MCP inside ASAP envelopes

When agents already communicate over ASAP HTTP (or WebSocket), invoke MCP tools by sending envelopes with `payload_type` `mcp_tool_call` and a `McpToolCall` payload (`tool_name`, `arguments`, optional `mcp_context`). The recipient returns `mcp_tool_result`. This path does not use the stdio Auth Bridge; authorization follows your ASAP server's existing middleware.

```python
from asap.models.envelope import Envelope
from asap.models.payloads import McpToolCall
from asap.transport.client import ASAPClient

payload = McpToolCall(request_id="req-1", tool_name="echo", arguments={"message": "hi"})
envelope = Envelope(
    asap_version="0.1",
    sender="urn:asap:agent:caller",
    recipient="urn:asap:agent:mcp-gateway",
    payload_type="mcp_tool_call",
    payload=payload.model_dump(),
)
async with ASAPClient("http://127.0.0.1:8000") as client:
    response = await client.send(envelope)
```

Full walkthrough: `uv run python -m asap.examples.mcp_integration`.

## How to Expose ASAP Agents as MCP Servers

You can expose an ASAP agent’s capabilities as MCP tools by running an MCP server that forwards tool calls to your agent (e.g. via ASAP envelopes).

### 1. Implement an MCP server with tools

```python
from asap.mcp import MCPServer

server = MCPServer(
    name="my-asap-mcp",
    version="1.0.0",
    description="MCP server that forwards to ASAP agent",
)
server.register_tool(
    "task_request",
    your_task_request_handler,
    {"type": "object", "properties": {"conversation_id": {"type": "string"}, "payload": {"type": "object"}}, "required": ["conversation_id"]},
    description="Send a task request to the ASAP agent",
)
# Add more tools as needed
```

Your handler can be sync or async; it receives the tool `arguments` as keyword arguments and can return a string or a dict (serialized to text in the result).

### 2. Run the server over stdio

Clients (e.g. Claude Desktop, Cursor) start your server as a subprocess and talk to it via stdin/stdout. So the process entry point must run the server loop:

```python
# server_runner.py or __main__
import asyncio
from asap.mcp import MCPServer

async def main():
    server = MCPServer(...)
    # register_tool(...)
    await server.run_stdio()

asyncio.run(main())
```

Run with:

```bash
python -m your_package.server_runner
```

Configure the client to use this command so it launches the server and connects over stdio.

### 3. Forward tool calls to ASAP

Inside a tool handler, build an ASAP envelope (e.g. `mcp_tool_call` / `mcp_tool_result` or your own payload types), call your ASAP agent via `ASAPClient.send()`, and map the response into MCP `CallToolResult` (e.g. a single `TextContent` with the result text). The MCP server’s `register_tool` handler return value is turned into text automatically; for more control you could run a small internal MCP server that builds `CallToolResult` explicitly and then have the stdio server return that.

## Connecting Claude / Gemini to ASAP

To connect a host application (e.g. Claude Desktop, or a Gemini-based app) to ASAP via MCP:

1. **Run an MCP server** that exposes tools backed by your ASAP agent (see above). The host starts this server as a subprocess and communicates over stdio.

2. **Configure the host** to use your server command, for example in Claude Desktop’s config add your server under MCP servers with the command that runs your `server_runner` (e.g. `python -m your_package.server_runner`).

3. **Tool discovery**: The host will send `initialize` and then `tools/list`; your server returns the list of tools (name, description, inputSchema). The host can then show these tools to the user or the model.

4. **Tool execution**: When the user or model invokes a tool, the host sends `tools/call` with `name` and `arguments`. Your server executes the handler (and optionally forwards to the ASAP agent), then returns a result with `content` (e.g. `[{"type": "text", "text": "..."}]`) and `isError: false` (or `true` for tool-level errors).

This way, Claude or Gemini can “see” your ASAP-backed tools and call them; your MCP server is the bridge between MCP and ASAP.

## Demo

A minimal demo that starts the built-in demo server (echo tool) and calls it:

```bash
PYTHONPATH=src uv run python examples/mcp_demo.py
```

The demo uses `MCPClient` to start `asap.mcp.server_runner` as a subprocess, performs initialize, lists tools, and calls the `echo` tool.

## Protocol version

This implementation follows **MCP 2025-11-25**. For a short reference of the types and messages used, see [mcp-specs.md](../engineering/references/mcp-specs.md) in the repo.

## Related

- [MCP Auth Bridge](adapters/mcp-auth-bridge.md) — Mode A `protect_server`
- [NeMo Agent Toolkit](integrations/nemo-agent-toolkit.md) — experimental Path A (NAT → ASAP-protected MCP)
- [Automation connector security](guides/automation-connector-security.md) — connector secrets / TLS / grants when MCP is involved
- [Workflow connectors](integrations/workflow-connectors.md) — OpenAPI path (no MCP required)
