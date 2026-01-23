# ASAP: Async Simple Agent Protocol

> A streamlined, scalable, asynchronous protocol for agent-to-agent communication and task coordination.

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges:
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
- **Async-Native**: Engineered from the ground up for high-concurrency environments using `asyncio` and `httpx`.

> 💡 **Performance Note**: Pure Python codebase leveraging Rust-accelerated dependencies (`pydantic-core`, `orjson`, `python-ulid`) for native-level performance without build complexity.

## Installation

We recommend using [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv add asap-protocol
```

Or with pip:

```bash
pip install asap-protocol
```

For reproducible environments, prefer `uv` when possible.

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
- `HandlerRegistry`: payload dispatch registry
- `ASAPClient`: async HTTP client for agent communication

## Documentation

- [Spec](.cursor/docs/general-specs.md)
- [Docs](docs/index.md)
- [API Reference](docs/api-reference.md)

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

### Multi-Agent Flow

Run the built-in demo to see two agents exchanging messages:

- `uv run python -m asap.examples.run_demo`

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.