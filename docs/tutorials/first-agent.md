# Building Your First Agent

**Time:** ~15 minutes | **Level:** Beginner

This tutorial walks you through building and running your first ASAP agent: an echo agent that receives task requests and echoes the input back. You will set up the server, send a request from a client, and verify it works.

## Prerequisites

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Step 1: Install ASAP

From your project directory:

```bash
# Using uv (recommended)
uv add asap-protocol

# Using pip
pip install asap-protocol
```

## Step 2: Run the Echo Agent Server

ASAP includes a minimal echo agent. Start it on port 8001:

```bash
uv run python -m asap.examples.echo_agent --host 127.0.0.1 --port 8001
```

Keep this terminal open. You should see the server start and listen on `http://127.0.0.1:8001`.

## Step 3: Write Your First Client

In a new terminal, create a file `my_client.py`:

```python
import asyncio
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.transport.client import ASAPClient


async def main() -> None:
    # 1. Build the task request
    request = TaskRequest(
        conversation_id=generate_id(),
        skill_id="echo",
        input={"message": "Hello from my first ASAP client!"},
    )

    # 2. Wrap it in an envelope
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:my-client",
        recipient="urn:asap:agent:echo-agent",
        payload_type="task.request",
        payload=request.model_dump(),
        trace_id=generate_id(),
    )

    # 3. Send and get the response
    async with ASAPClient("http://127.0.0.1:8001") as client:
        response = await client.send(envelope)

    print("Response:", response.payload)


if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run python my_client.py
```

You should see the echoed payload printed.

## Step 4: Understand the Server

The echo agent has three main pieces:

### Manifest

The manifest describes the agent and its capabilities. The echo agent exposes:

- **ID:** `urn:asap:agent:echo-agent`
- **Skill:** `echo` — echoes the input
- **Endpoint:** `http://127.0.0.1:8001/asap` — where it receives messages

### Handler Registry

The server registers a handler for `task.request` messages:

```python
from asap.transport.handlers import HandlerRegistry, create_echo_handler

registry = HandlerRegistry()
registry.register("task.request", create_echo_handler())
```

### FastAPI App

The server uses `create_app(manifest, registry)` to build a FastAPI app with:

- `POST /asap` — receives ASAP envelopes (JSON-RPC 2.0)
- `GET /.well-known/asap/manifest.json` — agent manifest for discovery

## Step 5: Build Your Own Echo Agent (Optional)

Create `my_echo_agent.py`:

```python
from fastapi import FastAPI
import uvicorn

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

manifest = Manifest(
    id="urn:asap:agent:my-echo",
    name="My Echo Agent",
    version="0.1.0",
    description="Echoes task input",
    capabilities=Capability(
        asap_version="0.1",
        skills=[Skill(id="echo", description="Echo back the input")],
        state_persistence=False,
    ),
    endpoints=Endpoint(asap="http://127.0.0.1:8002/asap"),
)

registry = HandlerRegistry()
registry.register("task.request", create_echo_handler())

app = create_app(manifest, registry)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
```

Run it and point your client at `http://127.0.0.1:8002` to use your custom agent.

## Step 6: Test With the Full Demo

ASAP includes a full demo that starts the echo agent and sends a task:

```bash
uv run python -m asap.examples.run_demo
```

This runs the agent in a subprocess, sends a task, and prints the response. Use it to validate your setup.

## Next Steps

- [Stateful Workflows](stateful-workflows.md) — Long-running tasks with snapshots
- [Multi-Agent Orchestration](multi-agent.md) — Multiple agents working together
- [API Reference](../api-reference.md) — Full protocol and types
