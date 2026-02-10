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

📦 **Available on [PyPI](https://pypi.org/project/asap-protocol/)**

## Quick Start

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

## CLI

ASAP provides a CLI for schema management:

```bash
# Show version
asap --version

# Export all JSON schemas
asap export-schemas --output-dir ./schemas

# List available schemas
asap list-schemas

# Show a specific schema
asap show-schema agent
```

## Documentation

- [API Reference](api-reference.md)
- [Observability](observability.md)
- [Error Handling](error-handling.md)
- [Testing](testing.md)
- [v1.1 Security Model](security/v1.1-security-model.md) — OAuth2 trust limitations, Custom Claims, allowlist (ADR-17)

### v1.1 features (API reference & guides)

| Feature | Description | Where |
|:--------|:-------------|:------|
| **OAuth2 / Custom Claims** | Server and client auth; identity binding via JWT claims | [Transport](transport.md), [Security](security.md), examples: `auth_patterns` |
| **WebSocket** | Real-time transport; MessageAck for reliability (ADR-16) | [Transport](transport.md), `asap.transport.websocket`, examples: `websocket_concept` |
| **Webhooks** | Signed POST callbacks to URLs; SSRF checks, retry, DLQ | [API Reference](api-reference.md) (`asap.transport`), `WebhookDelivery`, `WebhookRetryManager` |
| **Discovery** | Well-known manifest, Lite Registry, health endpoint | [Transport](transport.md), `asap.discovery` |
| **State Storage** | SQLite backend, env-based backend selection | [State Management](state-management.md), [Best Practices: Failover](best-practices/agent-failover-migration.md), examples: `storage_backends`, `state_migration` |
| **Health** | `GET /.well-known/asap/health` for liveness | [Transport](transport.md), `asap.discovery.health` |
