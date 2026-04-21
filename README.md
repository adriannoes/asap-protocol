# ASAP: Async Simple Agent Protocol

*✨ From **agents**, for **agents**. Delivering reliability, **as soon as possible.***

![ASAP Protocol Banner](https://raw.githubusercontent.com/adriannoes/asap-protocol/main/.github/assets/asap-protocol-banner.png)


> A production-ready protocol for agent-to-agent communication and task coordination.

**Quick Info**: `v2.2.0` | `Apache 2.0` | `Python 3.13+` | [Documentation](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md) | [PyPI](https://pypi.org/project/asap-protocol/) | [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)

> 🚀 **Live now** our [**agentic marketplace**](https://asap-protocol.vercel.app/) — browse agents, register yours, request verification.

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges that existing protocols like A2A don't fully address:
1. **$N^2$ Connection Complexity**: Most protocols assume static point-to-point HTTP connections that don't scale.
2. **State Drift**: Lack of native persistence makes it impossible to reliably resume long-running agentic workflows.
3. **Fragmentation**: No unified way to handle task delegation, artifact exchange and tool execution (MCP) in a single envelope.

**ASAP** provides a production-ready communication layer that simplifies these complexities. It's ideal for **multi-agent orchestration**, **stateful workflows** (persistence, resumability), **MCP support** and **production systems** requiring high-performance, type-safe agent communication. 

For simple point-to-point communication, a basic HTTP API might suffice; ASAP shines when you need orchestration, state management and multi-agent coordination. See the [spec](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/product-specs/strategy/v0-original-specs.md) for details.

### Key Features

- **Stateful orchestration** — Task state machine with snapshotting for resumable workflows.
- **Schema-first** — Pydantic v2 + JSON Schema for cross-agent interoperability.
- **Async-native** — `asyncio` + `httpx`; sync and async handlers supported.
- **MCP integration** — Tool execution and coordination in a single envelope.
- **Observable** — `trace_id` and `correlation_id` for debugging.
- **Security** — Bearer auth, OAuth2/JWT, Ed25519 signed manifests, optional mTLS, replay prevention, HTTPS, rate limiting. [Security Model](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/v1.1-security-model.md) (trust limits, Custom Claims).
- **Identity & capabilities (v2.2)** — Per-runtime Host/Agent JWTs, capability grants with constraints (`max`, `min`, `in`, `not_in`), approval flows (device authorization / CIBA-style), optional WebAuthn for high-risk registration.
- **Streaming & wire protocol (v2.2)** — `POST /asap/stream` (SSE / `TaskStream`), JSON-RPC 2.0 batch on `POST /asap`, `ASAP-Version` negotiation, tamper-evident audit logging, Compliance Harness v2.
- **Economics** — Usage metering, delegation tokens, SLA framework with breach alerts.

### 🆕 Framework Ecosystem
ASAP is built for interoperability. Seamlessly integrate your agents into **OpenClaw**, **LangChain**, **CrewAI** and **LlamaIndex** workflows using our growing library of native adapters and standardized tool-calling schemas.

## Installation

We recommend using [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv add asap-protocol
```

Or with pip:

```bash
pip install asap-protocol
```

📦 **Available on [PyPI](https://pypi.org/project/asap-protocol/)** — for reproducible environments, prefer `uv` when possible.

## Quick Start

**Run the demo** (echo agent + coordinator in one command):

```bash
uv run python -m asap.examples.run_demo
```

**Build your first agent** [here](docs/tutorials/first-agent.md) — server setup, client code, step-by-step (~15 min).

[19 examples](src/asap/examples/README.md): orchestration, state migration, MCP, OAuth2, WebSocket, resilience.

## Testing

```bash
uv run pytest -n auto --tb=short
```

With coverage:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

[Testing Guide](https://github.com/adriannoes/asap-protocol/blob/main/docs/testing.md) (structure, fixtures, property/load/chaos tests). [Contributing](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md) (dev setup, CI).

### Compliance Harness

Validate that your agent follows the ASAP protocol:

```bash
uv add asap-compliance
pytest --asap-agent-url https://your-agent.example.com -m asap_compliance
```

See [Compliance Testing Guide](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/compliance-testing.md) for handshake, schema and state machine validation.

## Documentation

**Learn**
- [Docs](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md) | [API Reference](https://github.com/adriannoes/asap-protocol/blob/main/docs/api-reference.md)
- [Tutorials](https://github.com/adriannoes/asap-protocol/tree/main/docs/tutorials) — First agent to production checklist
- [Migration from A2A/MCP](https://github.com/adriannoes/asap-protocol/blob/main/docs/migration.md)
- [Raw Fetch (non-Python)](https://github.com/adriannoes/asap-protocol/blob/main/docs/raw-fetch.md) — Fetch registry.json and revoked_agents.json with curl/fetch; implement your own client.

**Deep Dive**
- [State Management](https://github.com/adriannoes/asap-protocol/blob/main/docs/state-management.md) | [Best Practices: Failover & Migration](https://github.com/adriannoes/asap-protocol/blob/main/docs/best-practices/agent-failover-migration.md) | [Error Handling](https://github.com/adriannoes/asap-protocol/blob/main/docs/error-handling.md)
- [Transport](https://github.com/adriannoes/asap-protocol/blob/main/docs/transport.md) | [Security](https://github.com/adriannoes/asap-protocol/blob/main/docs/security.md) | [Security Model](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/v1.1-security-model.md) (OAuth2 trust, Custom Claims)
- [Identity Signing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/identity-signing.md) | [Compliance Testing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/compliance-testing.md) | [Migration v1.1 to v1.2](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/migration-v1.1-to-v1.2.md) | [mTLS](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/mtls.md)
- [Observability](https://github.com/adriannoes/asap-protocol/blob/main/docs/observability.md) | [Testing](https://github.com/adriannoes/asap-protocol/blob/main/docs/testing.md)

**Decisions & Operations**
- [ADRs](https://github.com/adriannoes/asap-protocol/tree/main/docs/adr) — 19 Architecture Decision Records
- [Tech Stack](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/dev-planning/architecture/tech-stack-decisions.md) — Rationale for Python, Pydantic, Next.js choices
- [Deployment](https://github.com/adriannoes/asap-protocol/blob/main/docs/deployment/kubernetes.md) | [Troubleshooting](https://github.com/adriannoes/asap-protocol/blob/main/docs/troubleshooting.md)

**Release**
- [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md) | [PyPI](https://pypi.org/project/asap-protocol/)

## CLI

- **v1.1** adds OAuth2, WebSocket, Discovery (well-known + Lite Registry), State Storage (SQLite) and Webhooks.
- **v1.2** adds Ed25519 signed manifests, trust levels, optional mTLS and the [Compliance Harness](https://github.com/adriannoes/asap-protocol/blob/main/asap-compliance/README.md).
- **v1.3** adds delegation commands (`asap delegation create`, `asap delegation revoke`).
- **v2.0** adds the Lean Marketplace Web App (Next.js), Lite Registry on GitHub Pages, IssueOps registration, OAuth sign-in for developers, and Verified Badge flow.
- **v2.1** adds the Consumer SDK (`MarketClient`), optional framework extras (LangChain, CrewAI, LlamaIndex, SmolAgents, OpenClaw, …), and registry UX improvements on PyPI.
- **v2.1.1** is a patch release: JWT algorithm allowlist, SQLite async bridging, optional Redis-backed rate limits, SSRF hardening in the web app, and related reliability fixes (see [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)).
- **v2.2** adds per-runtime agent identity, capability-based authorization, SSE streaming (`POST /asap/stream`), `ASAP-Version` negotiation, JSON-RPC batch requests, tamper-evident audit logging, async state stores, and Compliance Harness v2.
- **v2.2.1** adds optional WebAuthn attestation/assertion (`asap-protocol[webauthn]`), `asap compliance-check` and `asap audit export` CLIs, and related docs / CI gates (see [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)).

```bash
asap --version                                    # Show version
asap list-schemas                                 # List all available schemas
asap export-schemas                               # Export JSON schemas to file
asap compliance-check --url https://agent.example # Compliance Harness v2 (HTTP(S))
asap audit export --store memory --format json    # Export audit log (stdout)
asap keys generate -o key.pem                     # Generate Ed25519 keypair
asap manifest sign -k key.pem manifest.json       # Sign manifest
asap manifest verify signed.json                  # Verify signature
asap manifest info signed.json                    # Show trust level
```

See [CLI reference](docs/cli.md) (`compliance-check`, `audit export`), [CI compliance gate](docs/ci-compliance.md), [Audit export](docs/audit.md), [Identity Signing](docs/guides/identity-signing.md), or run `asap --help`.

See [docs index](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md#v11-features-api-reference--guides) and [Identity Signing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/identity-signing.md) for details.

## 🔭 What's Next?

ASAP is evolving toward an **Agent Marketplace** — an open ecosystem where AI agents discover, trust and collaborate autonomously. See our [vision document](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/product-specs/strategy/vision-agent-marketplace.md) for the full roadmap.

## Contributing

**Community feedback and contributions are essential** for ASAP Protocol's evolution. We're working on improvements and your input helps shape the future of the protocol. 

Every contribution, from bug reports to feature suggestions, documentation improvements and code contributions, makes a real difference.

Check out our [contributing guidelines](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md) to get started. It's easier than you think! 🚀

## License

This project is licensed under the Apache 2.0 License - see the [license](https://github.com/adriannoes/asap-protocol/blob/main/LICENSE) file for details.

---

**Built with [Cursor](https://cursor.com/)** using Composer 1.5, Claude Opus 4.6, Gemini 3.1 Pro and Kimi K2.5.
