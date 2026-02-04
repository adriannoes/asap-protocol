# MCP Specification Reference (2025-11-25)

> **Purpose**: Align ASAP MCP implementation with the **current** Model Context Protocol spec.  
> **Spec version**: **2025-11-25** (current as of 2025-11-25).  
> **Source**: https://modelcontextprotocol.io/specification/2025-11-25

Use this document when implementing Task 12.2 (MCP server/client) so the protocol is up to date.

---

## Version and lifecycle

- **Protocol version string**: `"2025-11-25"`.
- **Initialization**: Client sends `initialize` with `protocolVersion`, `capabilities`, `clientInfo` (Implementation). Server responds with `protocolVersion`, `capabilities`, `serverInfo` (Implementation), optional `instructions`. Client then sends notification `notifications/initialized`.
- **clientInfo / serverInfo** (Implementation): `name`, `version` required; optional: `title`, `description`, `icons`, `websiteUrl`.

---

## JSON-RPC 2.0

- **Request**: `jsonrpc: "2.0"`, `id` (string|number, MUST NOT be null), `method`, optional `params`.
- **Response**: `jsonrpc: "2.0"`, `id`, and either `result` or `error` (not both).
- **Error**: `code` (int), `message` (string), optional `data`.
- **Notification**: `jsonrpc: "2.0"`, `method`, optional `params`; **no `id`**.

---

## Stdio transport

- Client launches server as subprocess; server reads from stdin, writes to stdout.
- **Message framing**: One JSON-RPC message per line; messages **MUST NOT** contain embedded newlines (newline-delimited JSON).
- UTF-8 encoding. stderr may be used for logging; stdout must only contain valid MCP messages.

---

## Tools (server feature)

- **tools/list**  
  - Request params: optional `cursor`.  
  - Result: `tools` (array of Tool), optional `nextCursor`.

- **Tool** (per 2025-11-25):  
  - `name` (required), `description` (required), `inputSchema` (required; JSON Schema object, not null).  
  - Optional: `title`, `icons`, `outputSchema`, `annotations`.  
  - Tools with no parameters: use e.g. `inputSchema: { "type": "object", "additionalProperties": false }`.

- **tools/call**  
  - Request params: `name`, `arguments` (object).  
  - Result: `content` (array of content items), `isError` (boolean). Optional: `structuredContent` (object).  
  - **TextContent**: `type: "text"`, `text` (string); optional `annotations`.

- **Errors**: Protocol errors (e.g. unknown tool) → JSON-RPC `error`. Tool execution errors (e.g. validation) → result with `isError: true` and `content` describing the error.

---

## Capabilities (relevant subset)

- **Server** (initialize result): `tools: { listChanged?: true }` to expose tools and optionally notify when the list changes.
- **Client** (initialize params): Can send minimal `capabilities: {}` if only using tools.

---

## Differences from 2024-11-05 (for implementation)

- Protocol version string is `2025-11-25`.
- **Implementation** (clientInfo/serverInfo): optional `title`, `description`, `icons`, `websiteUrl` added.
- **Tool**: optional `title`, `icons`, `outputSchema`, `annotations`; `inputSchema` MUST be a valid JSON Schema object (not null).
- **InitializeResult**: optional `instructions` (string) for client/model hints.
- **CallToolResult**: optional `structuredContent` for structured output; tool execution errors should use `isError: true` in result (not only protocol error) to allow model self-correction.
- Stdio: same (newline-delimited, no embedded newlines).
- Lifecycle: same (initialize → result → notifications/initialized).

---

## References

- [Spec overview](https://modelcontextprotocol.io/specification/2025-11-25)
- [Lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
- [Transports (stdio)](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [Schema reference](https://modelcontextprotocol.io/specification/2025-11-25/schema) (TypeScript schema)
