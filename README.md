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

## Quick Start

### 1. Create an Agent (Server)

```python
from fastapi import FastAPI
from asap.transport import ASAPServer
from asap.models import Agent

app = FastAPI()
agent = Agent(name="my-agent", capabilities=["processing"])
server = ASAPServer(app, agent)

@server.on_task("process")
async def handle_process(task):
    return {"status": "success", "result": "processed"}
```

### 2. Send a Task (Client)

```python
import asyncio
from asap.transport import ASAPClient
from asap.models import TaskRequest

async def main():
    async with ASAPClient("http://localhost:8000") as client:
        response = await client.send(TaskRequest(
            task="process",
            input={"data": "..."}
        ))
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.