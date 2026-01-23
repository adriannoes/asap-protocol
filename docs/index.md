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
from asap.models import Envelope, TaskRequest
from asap.transport import ASAPClient

async def main():
    async with ASAPClient("http://localhost:8000") as client:
        task_request = TaskRequest(
            conversation_id="conv_01HX5K3MQVN8",
            skill_id="echo",
            input={"text": "Hello, ASAP"},
        )

        envelope = Envelope(
            asap_version="0.1",
            sender="urn:asap:agent:client",
            recipient="urn:asap:agent:server",
            payload_type="task.request",
            payload=task_request.model_dump(),
        )

        response = await client.send(envelope)
        print(response.payload_type)

if __name__ == "__main__":
    asyncio.run(main())
```

## Documentation

- [API Reference](api-reference.md)
- [Contributing](contributing.md)
