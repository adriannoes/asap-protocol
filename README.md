# ASAP: Async Simple Agent Protocol

*✨ From **agents**, for **agents**. Delivering reliability, **as soon as possible.***

![ASAP Protocol Banner](https://raw.githubusercontent.com/adriannoes/asap-protocol/main/.github/assets/asap-protocol-banner.png)


> A production-ready protocol for agent-to-agent communication and task coordination.

**Quick Info**: `v1.2.0` | `Apache 2.0` | `Python 3.13+` | [Documentation](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md) | [PyPI](https://pypi.org/project/asap-protocol/) | [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md)

## Why ASAP?

Building multi-agent systems today suffers from three core technical challenges that existing protocols like A2A don't fully address:
1. **$N^2$ Connection Complexity**: Most protocols assume static point-to-point HTTP connections that don't scale.
2. **State Drift**: Lack of native persistence makes it impossible to reliably resume long-running agentic workflows.
3. **Fragmentation**: No unified way to handle task delegation, artifact exchange and tool execution (MCP) in a single envelope.

**ASAP** provides a production-ready communication layer that simplifies these complexities. It's ideal for **multi-agent orchestration**, **stateful workflows** (persistence, resumability), **MCP integration**, and **production systems** requiring high-performance, type-safe agent communication. 

For simple point-to-point communication, a basic HTTP API might suffice; ASAP shines when you need orchestration, state management and multi-agent coordination. See the [spec](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/product-specs/strategy/v0-original-specs.md) for details.

### Key Features

- **Stateful orchestration** — Task state machine with snapshotting for resumable workflows.
- **Schema-first** — Pydantic v2 + JSON Schema for cross-agent interoperability.
- **Async-native** — `asyncio` + `httpx`; sync and async handlers supported.
- **MCP integration** — Tool execution and coordination in a single envelope.
- **Observable** — `trace_id` and `correlation_id` for debugging.
- **Security** — Bearer auth, OAuth2/JWT (v1.1), Ed25519 signed manifests (v1.2), optional mTLS, replay prevention, HTTPS, rate limiting. [v1.1 Security Model](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/v1.1-security-model.md) (trust limits, Custom Claims).

## Installation

We recommend using [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv add asap-protocol
```

Or with pip:

```bash
pip install asap-protocol
```

📦 **Available on [PyPI](https://pypi.org/project/asap-protocol/)**. For reproducible environments, prefer `uv` when possible.

## Quick Start

**Run the demo** (echo agent + coordinator in one command):

```bash
uv run python -m asap.examples.run_demo
```

**Build your first agent**: [Building Your First Agent](docs/tutorials/first-agent.md) — server setup, client code, step-by-step (~15 min).

[15+ examples](src/asap/examples/README.md): orchestration, state migration, MCP, OAuth2, WebSocket, resilience.

## Testing

```bash
uv run pytest -n auto --tb=short
```

With coverage:

```bash
uv run pytest --cov=src --cov-report=term-missing
```

[Testing Guide](https://github.com/adriannoes/asap-protocol/blob/main/docs/testing.md) (structure, fixtures, property/load/chaos tests). [Contributing](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md) (dev setup, CI).

### Compliance Harness (v1.2)

Validate that your agent follows the ASAP protocol:

```bash
uv add asap-compliance
pytest --asap-agent-url https://your-agent.example.com -m asap_compliance
```

See [Compliance Testing Guide](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/compliance-testing.md) for handshake, schema and state machine validation.

## Benchmarks

[Benchmark Results](https://github.com/adriannoes/asap-protocol/blob/main/benchmarks/RESULTS.md): load (1,500+ RPS), stress, memory.

## Documentation

**Learn**
- [Docs](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md) | [API Reference](https://github.com/adriannoes/asap-protocol/blob/main/docs/api-reference.md)
- [Tutorials](https://github.com/adriannoes/asap-protocol/tree/main/docs/tutorials) — First agent to production checklist
- [Migration from A2A/MCP](https://github.com/adriannoes/asap-protocol/blob/main/docs/migration.md)

**Deep Dive**
- [State Management](https://github.com/adriannoes/asap-protocol/blob/main/docs/state-management.md) | [Best Practices: Failover & Migration](https://github.com/adriannoes/asap-protocol/blob/main/docs/best-practices/agent-failover-migration.md) | [Error Handling](https://github.com/adriannoes/asap-protocol/blob/main/docs/error-handling.md)
- [Transport](https://github.com/adriannoes/asap-protocol/blob/main/docs/transport.md) | [Security](https://github.com/adriannoes/asap-protocol/blob/main/docs/security.md) | [v1.1 Security Model](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/v1.1-security-model.md) (OAuth2 trust, Custom Claims, ADR-17)
- **v1.2**: [Identity Signing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/identity-signing.md) | [Compliance Testing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/compliance-testing.md) | [Migration v1.1→v1.2](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/migration-v1.1-to-v1.2.md) | [mTLS](https://github.com/adriannoes/asap-protocol/blob/main/docs/security/mtls.md)
- [Observability](https://github.com/adriannoes/asap-protocol/blob/main/docs/observability.md) | [Testing](https://github.com/adriannoes/asap-protocol/blob/main/docs/testing.md)

**Decisions & Operations**
- [ADRs](https://github.com/adriannoes/asap-protocol/tree/main/docs/adr) — 17 Architecture Decision Records
- [Tech Stack](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/dev-planning/architecture/tech-stack-decisions.md) — Rationale for Python, Pydantic, Next.js choices
- [Deployment](https://github.com/adriannoes/asap-protocol/blob/main/docs/deployment/kubernetes.md) | [Troubleshooting](https://github.com/adriannoes/asap-protocol/blob/main/docs/troubleshooting.md)

**Release**
- [Changelog](https://github.com/adriannoes/asap-protocol/blob/main/CHANGELOG.md) | [PyPI](https://pypi.org/project/asap-protocol/)

## CLI

**v1.1** adds OAuth2, WebSocket, Discovery (well-known + Lite Registry), State Storage (SQLite), and Webhooks. **v1.2** adds Ed25519 signed manifests, trust levels, optional mTLS, and the [Compliance Harness](https://github.com/adriannoes/asap-protocol/blob/main/asap-compliance/README.md).

```bash
asap --version                                    # Show version
asap list-schemas                                 # List all available schemas
asap export-schemas                               # Export JSON schemas to file
asap keys generate -o key.pem                     # Generate Ed25519 keypair (v1.2)
asap manifest sign -k key.pem manifest.json       # Sign manifest (v1.2)
asap manifest verify signed.json                  # Verify signature (v1.2)
asap manifest info signed.json                    # Show trust level (v1.2)
```

See [CLI reference](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/identity-signing.md) or run `asap --help`.

See [docs index](https://github.com/adriannoes/asap-protocol/blob/main/docs/index.md#v11-features-api-reference--guides) and [Identity Signing](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/identity-signing.md) for details.

## What's Next? 🔭

ASAP is evolving toward an **Agent Marketplace** — an open ecosystem where AI agents discover, trust and collaborate autonomously:

- **v1.1**: Identity Layer (OAuth2, WebSocket, Discovery) ✅
- **v1.2**: Trust Layer (Signed Manifests, Compliance Harness, mTLS) ✅
- **v1.3**: Economics Layer (Metering, SLAs, Delegation)
- **v2.0**: Agent Marketplace with Web App

See our [vision document](https://github.com/adriannoes/asap-protocol/blob/main/.cursor/product-specs/strategy/vision-agent-marketplace.md) for the full roadmap.

## Contributing

**Community feedback and contributions are essential** for ASAP Protocol's evolution. 

We're working on improvements and your input helps shape the future of the protocol. Every contribution, from bug reports to feature suggestions, documentation improvements and code contributions, makes a real difference.

Check out our [contributing guidelines](https://github.com/adriannoes/asap-protocol/blob/main/CONTRIBUTING.md) to get started. It's easier than you think! 🚀

## License

This project is licensed under the Apache 2.0 License - see the [license](https://github.com/adriannoes/asap-protocol/blob/main/LICENSE) file for details.

---

**Built with [Cursor](https://cursor.com/)** using Composer 1.5, Claude Sonnet/Opus 4.5/4.6, Gemini 3.0 Pro and Kimi K2.5.
