# ASAP: Async Simple Agent Protocol

![ASAP Protocol Banner](https://raw.githubusercontent.com/adriannoes/asap-protocol/main/.github/assets/asap-protocol-banner.png)


> A streamlined, scalable, asynchronous protocol for agent-to-agent communication and task coordination. Built as a simpler, more powerful alternative to A2A with native MCP integration and stateful orchestration.

**Quick Info**: `v0.5.0` | `Apache 2.0` | `Python 3.13+` | [Documentation](https://asap-protocol.org) | [PyPI](https://pypi.org/project/asap-protocol/0.5.0/) | [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)

⚠️ **Alpha Release**: ASAP Protocol is currently in **alpha** (v0.5.0). We're actively developing and improving the protocol based on real-world usage. Your feedback, contributions, and suggestions are essential to help us evolve and make ASAP better for the entire community. See our [Contributing](https://github.com/adriannoes/asap-protocol#contributing) section to get involved!

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges that existing protocols like A2A don't fully address:
1. **$N^2$ Connection Complexity**: Most protocols assume static point-to-point HTTP connections that don't scale.
2. **State Drift**: Lack of native persistence makes it impossible to reliably resume long-running agentic workflows.
3. **Fragmentation**: No unified way to handle task delegation, artifact exchange, and tool execution (MCP) in a single envelope.

**ASAP** provides a production-ready communication layer that simplifies these complexities. It introduces a standardized, stateful orchestration framework that ensures your agents can coordinate reliably across distributed environments.

### Key Features

- **Stateful orchestration** — Task state machine with snapshotting for resumable workflows.
- **Schema-first** — Pydantic v2 + JSON Schema for cross-agent interoperability.
- **Async-native** — `asyncio` + `httpx`; sync and async handlers supported.
- **MCP integration** — Tool execution and coordination in a single envelope.
- **Observable** — `trace_id` and `correlation_id` for debugging.
- **Security (v0.5.0)** — Bearer auth, replay prevention, HTTPS, rate limiting (100 req/min). Opt-in.

## Installation

We recommend using [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv add asap-protocol
```

Or with pip:

```bash
pip install asap-protocol
```

📦 **Available on [PyPI](https://pypi.org/project/asap-protocol/0.5.0/)**

For reproducible environments, prefer `uv` when possible.

## Requirements

- **Python**: 3.13 or higher
- **Dependencies**: Automatically installed via `uv` or `pip`
- **Optional**: For development, see [Contributing](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md).

## Quick Start

### 1. Create an Agent (Server)

```python
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

manifest = Manifest(
    id="urn:asap:agent:echo-agent",
    name="Echo Agent",
    version="0.5.0",
    description="Echoes task input as output",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo back the input")],
        state_persistence=False,
    ),
    # Development: HTTP localhost is allowed
    # Production: Always use HTTPS (e.g., "https://api.example.com/asap")
    endpoints=Endpoint(asap="http://127.0.0.1:8001/asap"),
)

registry = HandlerRegistry()
registry.register("task.request", create_echo_handler())

app = create_app(manifest, registry)
```

### 2. Send a Task (Client)

```python
import asyncio
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.client import ASAPClient

async def main():
    request = TaskRequest(
        conversation_id="conv_01HX5K3MQVN8",
        skill_id="echo",
        input={"message": "hello from client"},
    )
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:echo-agent",
        payload_type="task.request",
        payload=request.model_dump(),
    )
    # Development: HTTP localhost is allowed (with warning)
    # Production: Always use HTTPS (e.g., "https://api.example.com")
    async with ASAPClient("http://127.0.0.1:8001") as client:
        response = await client.send(envelope)
        print(response.payload)

if __name__ == "__main__":
    asyncio.run(main())
```

## API Overview

Core models:

- `Envelope`: protocol wrapper with routing and tracing metadata
- `TaskRequest`, `TaskResponse`, `TaskUpdate`, `TaskCancel`: task lifecycle payloads
- `MessageSend`, `ArtifactNotify`: messaging and artifacts
- `StateQuery`, `StateRestore`: snapshot state operations
- `McpToolCall`, `McpToolResult`, `McpResourceFetch`, `McpResourceData`: MCP integration

Transport:

- `create_app`: FastAPI application factory
- `HandlerRegistry`: payload dispatch registry (supports both sync and async handlers)
- `ASAPClient`: async HTTP client with automatic retry for server errors (5xx)

## Documentation

- [Spec](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/docs/general-specs.md)
- [Docs](https://asap-protocol.org)
- [API Reference](https://asap-protocol.org)
- [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)
- [PyPI Package](https://pypi.org/project/asap-protocol/0.5.0/)

## When to Use ASAP?

ASAP is ideal for:
- **Multi-agent orchestration**: Coordinate tasks across multiple AI agents
- **Stateful workflows**: Long-running tasks that need persistence and resumability
- **MCP integration**: Agents that need to execute tools via Model Context Protocol
- **Production systems**: High-performance, type-safe agent communication

If you're building simple point-to-point agent communication, a basic HTTP API might suffice. ASAP shines when you need orchestration, state management and multi-agent coordination.

## Advanced Topics

Explore these guides for detailed information on specific features:

- **[State Management](https://github.com/adriannoes/asap-protocol/blob/main/docs/state-management.md)**: Task lifecycle, state machine, and snapshot persistence for resumable workflows.
- **[Error Handling](https://github.com/adriannoes/asap-protocol/blob/main/docs/error-handling.md)**: Structured error taxonomy and recovery patterns for robust agent communication.
- **[Transport Layer](https://github.com/adriannoes/asap-protocol/blob/main/docs/transport.md)**: HTTP/JSON-RPC binding details, async handlers, and server configuration.
- **[Security](https://github.com/adriannoes/asap-protocol/blob/main/docs/security.md)**: Production security practices, rate limiting, DoS protection, and authentication.
- **[Observability](https://github.com/adriannoes/asap-protocol/blob/main/docs/observability.md)**: Tracing, metrics, and logging for debugging multi-agent systems.
- **[Testing](https://github.com/adriannoes/asap-protocol/blob/main/docs/testing.md)**: Testing strategies and utilities for ASAP-based agents.

### Advanced Examples

Run the built-in multi-agent demo to see ASAP in action:

```bash
uv run python -m asap.examples.run_demo
```

The package includes **14+ real-world examples** in [`src/asap/examples/`](https://github.com/adriannoes/asap-protocol/tree/main/src/asap/examples). Full list and usage: [Examples README](src/asap/examples/README.md).

| Category | Examples |
|----------|----------|
| **Core** | `run_demo`, `echo_agent`, `coordinator`, `secure_handler` |
| **Orchestration** | `orchestration` (multi-agent, task coordination, state tracking) |
| **State** | `long_running` (checkpoints, resume after crash), `state_migration` (move state between agents) |
| **Resilience** | `error_recovery` (retry, circuit breaker, fallback) |
| **Integration** | `mcp_integration` (MCP tools via envelopes) |
| **Auth & limits** | `auth_patterns` (Bearer, validators, OAuth2 concept), `rate_limiting` (per-sender, per-endpoint) |
| **Concepts** | `websocket_concept` (WebSocket design), `streaming_response` (TaskUpdate streaming), `multi_step_workflow` (pipeline) |

Run any example: `uv run python -m asap.examples.<module_name> [options]`

### CLI Tools

The ASAP CLI provides utilities for schema management. See [CLI documentation](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md#cli) or run `asap --help` for available commands.

## Contributing

We love contributions! Whether it's fixing a bug, improving documentation or proposing a new feature.. your help is welcome.

**As an alpha release, community feedback and contributions are essential** for ASAP Protocol's evolution. We're actively working on improvements and your input helps shape the future of the protocol. Every contribution, from bug reports to feature suggestions, documentation improvements and code contributions, makes a real difference.

Check out our [Contributing Guidelines](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md) to get started. It's easier than you think! 🚀

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](https://github.com/adriannoes/asap-protocol/blob/main/LICENSE) file for details.