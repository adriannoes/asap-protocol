# ASAP: Async Simple Agent Protocol

![Version](https://img.shields.io/pypi/v/asap-protocol?label=version)
![License](https://img.shields.io/github/license/adriannoes/asap-protocol)
![Python](https://img.shields.io/pypi/pyversions/asap-protocol)
![CI Status](https://img.shields.io/github/actions/workflow/status/adriannoes/asap-protocol/ci.yml?branch=main&label=CI)
![Coverage](https://img.shields.io/codecov/c/github/adriannoes/asap-protocol)
![PyPI Downloads](https://img.shields.io/pypi/dm/asap-protocol)

![ASAP Protocol Banner](.cursor/docs/asap-protocol-banner.png)

> A streamlined, scalable, asynchronous protocol for agent-to-agent communication and task coordination. Built as a simpler, more powerful alternative to A2A with native MCP integration and stateful orchestration.

**Quick Info**: `v0.1.0` | `Apache 2.0` | `Python 3.13+` | [Documentation](docs/index.md) | [PyPI](https://pypi.org/project/asap-protocol/) | [Changelog](CHANGELOG.md)

⚠️ **Alpha Release**: ASAP Protocol is currently in **alpha** (v0.1.0). We're actively developing and improving the protocol based on real-world usage. Your feedback, contributions, and suggestions are essential to help us evolve and make ASAP better for the entire community. See our [Contributing](#contributing) section to get involved!

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges that existing protocols like A2A don't fully address:
1. **$N^2$ Connection Complexity**: Most protocols assume static point-to-point HTTP connections that don't scale.
2. **State Drift**: Lack of native persistence makes it impossible to reliably resume long-running agentic workflows.
3. **Fragmentation**: No unified way to handle task delegation, artifact exchange, and tool execution (MCP) in a single envelope.

**ASAP** provides a production-ready communication layer that simplifies these complexities. It introduces a standardized, stateful orchestration framework that ensures your agents can coordinate reliably across distributed environments.

### Key Features

- **Stateful Orchestration**: Native task state machine with built-in snapshotting for durable, resumable agent workflows.
- **Schema-First Design**: Strict Pydantic v2 models providing automatic JSON Schema generation for guaranteed cross-agent interoperability.
- **High-Performance Core**: Built on Python 3.13+, leveraging `uvloop` (C) and `pydantic-core` (Rust) for ultra-low latency validation and I/O.
- **Observable Chains**: First-class support for `trace_id` and `correlation_id` to debug complex multi-agent delegation.
- **MCP Integration**: Uses the Model Context Protocol (MCP) as a tool-execution substrate, wrapped in a high-level coordination envelope.
- **Async-Native**: Engineered from the ground up for high-concurrency environments using `asyncio` and `httpx`. Supports both sync and async handlers with automatic event loop management.
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

📦 **Available on [PyPI](https://pypi.org/project/asap-protocol/)**

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
    version="0.1.0",
    description="Echoes task input as output",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo back the input")],
        state_persistence=False,
    ),
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
- [PyPI Package](https://pypi.org/project/asap-protocol/)

## When to Use ASAP?

ASAP is ideal for:
- **Multi-agent orchestration**: Coordinate tasks across multiple AI agents
- **Stateful workflows**: Long-running tasks that need persistence and resumability
- **MCP integration**: Agents that need to execute tools via Model Context Protocol
- **Production systems**: High-performance, type-safe agent communication

If you're building simple point-to-point agent communication, a basic HTTP API might suffice. ASAP shines when you need orchestration, state management, and multi-agent coordination.

## Advanced Examples

### State Snapshots

```python
from datetime import datetime, timezone
from asap.models.entities import StateSnapshot
from asap.state import InMemorySnapshotStore

store = InMemorySnapshotStore()
snapshot = StateSnapshot(
    id="snap_01HX5K7R...",
    task_id="task_01HX5K4N...",
    version=1,
    data={"status": "submitted", "progress": 0},
    created_at=datetime.now(timezone.utc),
)
store.save(snapshot)
latest = store.get("task_01HX5K4N...")
```

### Error Recovery

```python
from asap.errors import InvalidTransitionError

try:
    raise InvalidTransitionError(from_state="submitted", to_state="completed")
except InvalidTransitionError as exc:
    payload = exc.to_dict()
    print(payload["code"])
```

### Async Handlers

Handlers can be either synchronous or asynchronous:

```python
# Sync handler
def my_sync_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
    # Process synchronously
    return response_envelope

# Async handler
async def my_async_handler(envelope: Envelope, manifest: Manifest) -> Envelope:
    # Process asynchronously (e.g., database calls, API requests)
    result = await some_async_operation()
    return response_envelope

registry.register("task.request", my_async_handler)  # Works with both!
```

### Security & DoS Protection

ASAP includes built-in protection against common attack vectors:

```python
from asap.transport.server import create_app

app = create_app(
    manifest,
    rate_limit="50/minute",        # Per-sender rate limiting
    max_request_size=5_000_000,    # 5MB request size limit  
    max_threads=16,                # Thread pool bounds
)
```

**Environment Variables**:
- `ASAP_RATE_LIMIT`: Rate limit (default: "100/minute")
- `ASAP_MAX_REQUEST_SIZE`: Max request size (default: 10MB)
- `ASAP_MAX_THREADS`: Thread pool size (default: min(32, cpu_count + 4))

See [Security Guide](docs/security.md) for production recommendations.

### Multi-Agent Flow

Run the built-in demo to see two agents exchanging messages:

```bash
uv run python -m asap.examples.run_demo
```

### CLI Tools

The ASAP CLI provides utilities for schema management:

```bash
# Export all JSON schemas
asap export-schemas --output-dir ./schemas

# List available schemas
asap list-schemas

# Show a specific schema
asap show-schema envelope

# Validate JSON against a schema
asap validate-schema message.json --schema-type envelope

# Verbose output
asap export-schemas --verbose
```

## Contributing

We love contributions! Whether it's fixing a bug, improving documentation or proposing a new feature.. your help is welcome.

**As an alpha release, community feedback and contributions are essential** for ASAP Protocol's evolution. We're actively working on improvements and your input helps shape the future of the protocol. Every contribution, from bug reports to feature suggestions, documentation improvements and code contributions, makes a real difference.

Check out our [Contributing Guidelines](CONTRIBUTING.md) to get started. It's easier than you think! 🚀

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.