# ASAP Protocol

**ASAP (Async Simple Agent Protocol)** is a streamlined protocol for agent-to-agent communication, designed to be simpler than existing alternatives while maintaining modern standards functionality.

**Latest reference implementation:** **v2.4.0** on PyPI ([CHANGELOG](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md), [PyPI](https://pypi.org/project/asap-protocol/)). **TypeScript npm line: v2.4.0** — [`@asap-protocol/client`](https://www.npmjs.com/package/@asap-protocol/client), [`@asap-protocol/mastra`](integrations/mastra.md), [`@asap-protocol/openai-agents`](integrations/openai-agents.md). v2.4.0 **Edge-AI discovery**: optional hardware/inference manifest fields, registry mirror, marketplace filters. v2.3.x **Adoption Multiplier**: OpenAPI Adapter, Auto-Registration, capability escalation, ASAP challenges. Upgrade: [v2.3.x → v2.4.0](migration.md#upgrading-from-v23x-to-v240) · [v2.2.x → v2.3.0](migration.md#upgrading-from-v22x-to-v230) · [v2.3.0 → v2.3.1](migration.md#upgrading-from-v230-to-v231).

## Features

- **Typed Messages**: Full Pydantic type safety for all protocol messages
- **Async-First**: Built on `asyncio` for high-performance agent communication
- **State Management**: Built-in task state machine with persistence support (`AsyncSnapshotStore` / `AsyncMeteringStore` in v2.2+)
- **Transport Agnostic**: Clean separation between protocol logic and transport capability (HTTP JSON-RPC, WebSocket, SSE)
- **Observability**: First-class tracking with correlation IDs and trace IDs
- **Security & authorization (v2.2+, WebAuthn real in v2.2.1)**: Per-runtime Host/Agent JWTs, capability grants with constraints, approval flows, opt-in WebAuthn (`asap-protocol[webauthn]`) for browser-controlled and high-risk capability registration — see [Security](security.md) and [Migration](migration.md)
- **Edge-AI discovery (v2.4.0+)**: Optional `capabilities.hardware` / `inference` on manifests; [Transport](transport.md#hardware-and-inference-capabilities-v24), [ShellClaw registry guide](guides/shellclaw-registry.md), [registry examples](examples/registry-shellclaw.md)
- **Adoption tools (v2.3.0+)**: [OpenAPI adapter](adapters/openapi.md), [TypeScript client](sdks/typescript.md) (`@asap-protocol/client@2.4.0`), [Mastra adapter](integrations/mastra.md) (`@asap-protocol/mastra@2.4.0`), [OpenAI Agents SDK adapter](integrations/openai-agents.md) (`@asap-protocol/openai-agents@2.4.0`), [Auto-registration](registry/auto-registration.md), [Capability escalation](capabilities/escalation.md), [ASAP HTTP challenge](transport/asap-challenge.md)

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
        asap_version="0.1",  # envelope schema version (see asap.models.constants.ASAP_PROTOCOL_VERSION)
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

`ASAPClient` sends the **`ASAP-Version`** header for wire-level negotiation (`2.1` / `2.2`); that is separate from the envelope `asap_version` string above. See [Migration (v2.1.x → v2.2.0)](migration.md) and [ADR-019](adr/ADR-019-unified-versioning.md).

## CLI

ASAP provides a CLI for schema management and (v1.2) key/manifest operations:

```bash
# Show version
asap --version

# Export all JSON schemas
asap export-schemas --output-dir ./schemas

# List available schemas
asap list-schemas

# Show a specific schema
asap show-schema agent

# v1.2: Ed25519 keys and signed manifests
asap keys generate -o key.pem
asap manifest sign -k key.pem manifest.json
asap manifest verify signed.json
asap manifest info signed.json

# Compliance Harness v2 against a deployed agent (HTTP(S))
asap compliance-check --url https://your-agent.example.com --exit-on-fail

# Tamper-evident audit export (SQLite store)
asap audit export --store sqlite --db ./asap_state.db --format json --verify-chain
```

See [CLI reference](cli.md) (all commands, exit codes, `compliance-check`, `audit export`), [Audit log](audit.md), [CI: compliance gate](ci-compliance.md), and [Identity Signing](guides/identity-signing.md) for key and manifest workflows.

## Documentation

- [OpenAPI adapter](adapters/openapi.md) — derive ASAP skills and an upstream proxy from OpenAPI 3.x (`asap.adapters.openapi`)
- [TypeScript client SDK](sdks/typescript.md) — `@asap-protocol/client@2.4.0` on npm (browser + Node; optional LLM adapters; edge-AI registry fields)
- [Mastra adapter](integrations/mastra.md) — `@asap-protocol/mastra@2.4.0`: ASAP capabilities as `@mastra/core` tools + streaming bridge
- [OpenAI Agents SDK adapter](integrations/openai-agents.md) — `@asap-protocol/openai-agents@2.4.0`: ASAP capabilities as `@openai/agents` tools + handoff-oriented remote agent helper (`@openai/agents`, distinct from `@asap-protocol/client/adapters/openai`)
- [CLI reference](cli.md) — all `asap` commands, including `compliance-check`, `audit export`, and exit codes
- [Audit log](audit.md) — hash chain model, export formats, tamper checks
- [API Reference](api-reference.md)
- [Observability](observability.md)
- [Error Handling](error-handling.md)
- [Testing](testing.md)
- [Raw Fetch (non-Python)](raw-fetch.md) — Fetch registry.json and revoked_agents.json directly (curl, fetch); implement your own client in any language
- [v1.1 Security Model](security/v1.1-security-model.md) — OAuth2 trust limitations, Custom Claims, allowlist (see also [decision record § security](https://github.com/adriannoes/asap-protocol/blob/main/product/decision-records/03-security.md))
- [Registry verification review (admin)](guides/registry-verification-review.md) — How to vet and approve Verified badge requests for the Lite Registry
- [ShellClaw static manifest registration](guides/shellclaw-registry.md) — `online_check: false`, GitHub Pages manifest URLs, IssueOps vs auto-registration
- [Lite Registry auto-registration](registry/auto-registration.md) — Bot PR flow, OAuth2, payloads, rejections, and upgrading to Verified

### v1.1 features (API reference & guides)

| Feature | Description | Where |
|:--------|:-------------|:------|
| **OAuth2 / Custom Claims** | Server and client auth; identity binding via JWT claims | [Transport](transport.md), [Security](security.md), examples: `auth_patterns` |
| **WebSocket** | Real-time transport; MessageAck for reliability (see [Q16 — WebSocket Message Ack](https://github.com/adriannoes/asap-protocol/blob/main/product/decision-records/02-protocol.md#question-16-websocket-message-acknowledgment)) | [Transport](transport.md), `asap.transport.websocket`, examples: `websocket_concept` |
| **Webhooks** | Signed POST callbacks to URLs; SSRF checks, retry, DLQ | [API Reference](api-reference.md) (`asap.transport`), `WebhookDelivery`, `WebhookRetryManager` |
| **Discovery** | Well-known manifest, Lite Registry, health endpoint | [Transport](transport.md), `asap.discovery` |
| **State Storage** | SQLite backend, env-based backend selection | [State Management](state-management.md), [Best Practices: Failover](best-practices/agent-failover-migration.md), examples: `storage_backends`, `state_migration` |
| **Health** | `GET /.well-known/asap/health` for liveness | [Transport](transport.md), `asap.discovery.health` |

## Contact

**General inquiries** about the protocol or project: [info@asap-protocol.com](mailto:info@asap-protocol.com).

For vulnerability reports, use **[SECURITY.md](../SECURITY.md)** (GitHub Private Vulnerability Reporting), not email. Technical questions work well via [GitHub Discussions](https://github.com/adriannoes/asap-protocol/discussions) or [Issues](https://github.com/adriannoes/asap-protocol/issues).
