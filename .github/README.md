# ASAP: Async Simple Agent Protocol

![ASAP Protocol Banner](.cursor/docs/asap-protocol-banner.png)

> A streamlined, scalable, asynchronous protocol for agent-to-agent communication and task coordination. Built as a simpler, more powerful alternative to A2A with native MCP integration and stateful orchestration.

**Quick Info**: `v0.5.0` | `Apache 2.0` | `Python 3.13+` | [Documentation](docs/index.md) | [PyPI](https://pypi.org/project/asap-protocol/0.5.0/) | [Changelog](CHANGELOG.md)

⚠️ **Alpha Release**: ASAP Protocol is currently in **alpha** (v0.5.0). We're actively developing and improving the protocol based on real-world usage. Your feedback, contributions, and suggestions are essential to help us evolve and make ASAP better for the entire community. See our [Contributing](#contributing) section to get involved!

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges that existing protocols like A2A don't fully address:
1. **$N^2$ Connection Complexity**: Most protocols assume static point-to-point HTTP connections that don't scale.
2. **State Drift**: Lack of native persistence makes it impossible to reliably resume long-running agentic workflows.
3. **Fragmentation**: No unified way to handle task delegation, artifact exchange, and tool execution (MCP) in a single envelope.

**ASAP** provides a production-ready communication layer that simplifies these complexities. It introduces a standardized, stateful orchestration framework that ensures your agents can coordinate reliably across distributed environments.

### Security-First Design

v0.5.0 introduces comprehensive security hardening:
- **Authentication**: Bearer token authentication with configurable token validators
- **Replay Attack Prevention**: Timestamp validation (5-minute window) and optional nonce tracking
- **DoS Protection**: Built-in rate limiting (100 req/min), request size limits (10MB), and thread pool bounds
- **HTTPS Enforcement**: Client-side HTTPS validation in production mode
- **Secure Logging**: Automatic sanitization of sensitive data (tokens, credentials, nonces) in logs
- **Input Validation**: Strict schema validation with Pydantic v2 for all incoming requests

All security features are **opt-in** to maintain backward compatibility with existing deployments.

### Key Features

- **Stateful Orchestration**: Native task state machine with built-in snapshotting for durable, resumable agent workflows.
- **Schema-First Design**: Strict Pydantic v2 models providing automatic JSON Schema generation for guaranteed cross-agent interoperability.
- **High-Performance Core**: Built on Python 3.13+, leveraging `uvloop` (C) and `pydantic-core` (Rust) for ultra-low latency validation and I/O.
- **Observable Chains**: First-class support for `trace_id` and `correlation_id` to debug complex multi-agent delegation.
- **MCP Integration**: Uses the Model Context Protocol (MCP) as a tool-execution substrate, wrapped in a high-level coordination envelope.
- **Async-Native**: Engineered from the ground up for high-concurrency environments using `asyncio` and `httpx`. Supports both sync and async handlers with automatic event loop management.
- **Security-Hardened (v0.5.0)**: Authentication (Bearer tokens), replay attack prevention (timestamp + nonce validation), HTTPS enforcement, secure logging, and comprehensive input validation. All security features are opt-in for backward compatibility.
- **DoS Protection**: Built-in rate limiting (100 req/min), request size limits (10MB), and thread pool bounds to prevent resource exhaustion attacks.

💡 **Performance Note**: Pure Python codebase leveraging Rust-accelerated dependencies (`pydantic-core`, `orjson`, `python-ulid`) for native-level performance without build complexity.

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
- **Optional**: For development, see [Contributing](CONTRIBUTING.md)

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

- [Spec](.cursor/docs/general-specs.md)
- [Docs](docs/index.md)
- [API Reference](docs/api-reference.md)
- [Changelog](CHANGELOG.md)
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

- **[State Management](docs/state-management.md)**: Task lifecycle, state machine, and snapshot persistence for resumable workflows.
- **[Error Handling](docs/error-handling.md)**: Structured error taxonomy and recovery patterns for robust agent communication.
- **[Transport Layer](docs/transport.md)**: HTTP/JSON-RPC binding details, async handlers, and server configuration.
- **[Security](docs/security.md)**: Production security practices, rate limiting, DoS protection, and authentication.
- **[Observability](docs/observability.md)**: Tracing, metrics, and logging for debugging multi-agent systems.
- **[Testing](docs/testing.md)**: Testing strategies and utilities for ASAP-based agents.

### Examples & Demos

Run the built-in multi-agent demo to see ASAP in action:

```bash
uv run python -m asap.examples.run_demo
```

See [`src/asap/examples/`](src/asap/examples/) for complete example implementations.

### CLI Tools

The ASAP CLI provides utilities for schema management. See [CLI documentation](docs/index.md#cli) or run `asap --help` for available commands.

## Contributing

We love contributions! Whether it's fixing a bug, improving documentation or proposing a new feature.. your help is welcome.

**As an alpha release, community feedback and contributions are essential** for ASAP Protocol's evolution. We're actively working on improvements and your input helps shape the future of the protocol. Every contribution, from bug reports to feature suggestions, documentation improvements and code contributions, makes a real difference.

Check out our [Contributing Guidelines](CONTRIBUTING.md) to get started. It's easier than you think! 🚀

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.
