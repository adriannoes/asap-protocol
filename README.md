# ASAP: Async Simple Agent Protocol (Python SDK)

> A streamlined, scalable, asynchronous protocol for agent-to-agent communication and task coordination.

## Overview

**ASAP Protocol** is a Python library that implements the ASAP specification for building interoperable AI agents. It provides a robust, type-safe foundation for agent-to-agent communication using standard HTTP and JSON-RPC.

### Key Features

- 🐍 **Modern Python**: Built with Python 3.13+ and strict type hinting
- 🚀 **High Performance**: Built on `uv`, `httpx`, and `fastapi` for maximum speed
- 🛡️ **Type Safety**: Full Pydantic v2 integration with exported JSON Schemas
- 🔄 **Async-First**: Native `asyncio` support for high-concurrency workloads
- 📦 **State Management**: Built-in task state machine and persistence utilities
- 🔌 **MCP Compatible**: Native support for Model Context Protocol envelopes

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