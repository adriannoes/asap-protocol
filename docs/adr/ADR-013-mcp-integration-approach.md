# ADR-013: MCP Integration Approach

## Context and Problem Statement

ASAP aims to integrate with the Model Context Protocol (MCP) for tool invocation. We need a strategy for MCP tool calls and results within ASAP envelopes.

## Decision Drivers

* Interoperability with MCP ecosystem
* ASAP envelope structure (payload_type, payload)
* Tool call/result as first-class payload types
* Preserve ASAP semantics (sender, recipient, trace_id)

## Considered Options

* MCP-native transport only (no ASAP)
* ASAP wraps MCP messages (McpToolCall, McpToolResult payloads)
* Parallel protocols (ASAP and MCP coexist)
* ASAP as MCP transport adapter

## Decision Outcome

Chosen option: "ASAP wraps MCP messages", because ASAP envelopes can carry MCP tool call and result payloads. Payload types like mcp.tool_call and mcp.tool_result allow agents to invoke MCP tools via ASAP. Preserves trace_id, correlation_id for observability.

### Consequences

* Good, because single transport (ASAP) for agent and MCP flows
* Good, because trace context flows through tool calls
* Bad, because MCP spec may evolve; requires sync
* Neutral, because MCP tool discovery separate from ASAP manifest

### Confirmation

Examples in `asap.examples.mcp_integration`. Payload types for MCP tool invocation. See MCP spec for tool schema.

## Pros and Cons of the Options

### ASAP wraps MCP

* Good, because unified transport; trace context
* Good, because ASAPClient can send MCP payloads
* Bad, because double wrapping (ASAP + MCP)

### Parallel protocols

* Good, because native MCP where needed
* Bad, because two transports; no unified tracing

## More Information

* `asap.examples.mcp_integration`
* [MCP specification](https://spec.modelcontextprotocol.io/)
* Payload types: mcp.tool_call, mcp.tool_result (or equivalent)
