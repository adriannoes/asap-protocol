# ASAP Protocol

**ASAP (Async Simple Agent Protocol)** is a streamlined protocol for agent-to-agent communication, designed to be simpler than existing alternatives while maintaining modern standards functionality.

## Features

- **Typed Messages**: Full Pydantic type safety for all protocol messages
- **Async-First**: Built on `asyncio` for high-performance agent communication
- **State Management**: Built-in task state machine with persistence support
- **Transport Agnostic**: Clean separation between protocol logic and transport capability (HTTP/JSON-RPC provided)
- **Observability**: First-class tracking with correlation IDs and trace IDs

## Installation

```bash
# Using uv (recommended)
uv add asap-protocol

# Using pip
pip install asap-protocol
```

## Quick Start

```python
import asyncio
from asap.models import TaskRequest, Agent
from asap.transport import ASAPClient

async def main():
    # Create a client
    async with ASAPClient("http://localhost:8000") as client:
        # Create a task
        task = TaskRequest(
            task="Optimize this Python code",
            input={"code": "def foo(): pass"}
        )
        
        # Send it
        response = await client.send(task)
        print(f"Result: {response.output}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

- [API Reference](api/models/entities.md)
- [Contributing](contributing.md)
