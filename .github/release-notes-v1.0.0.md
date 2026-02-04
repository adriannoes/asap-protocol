# ASAP Protocol v1.0.0 - Production-Ready Release

**Release Date**: 2026-02-03  
**Status**: Stable  
**Previous Version**: v0.5.0 (2026-01-28)

This release marks the **production-ready** milestone of the ASAP Protocol Python implementation. All features from v0.5.0 are preserved with backward compatibility.

---

## Major Features

### Security & Validation

- **Log sanitization**: Credential and token patterns redacted from logs; `ASAP_DEBUG` env var for controlled verbose output in development
- **Handler security**: `FilePart` URI validation, path traversal detection; updated `docs/security.md`
- **Thread safety**: Thread-safe `HandlerRegistry` for concurrent handler registration and execution
- **URN validation**: Max 256-character URNs, task depth limits, enhanced input validation
- **ManifestCache LRU eviction**: `max_size` limit with LRU eviction to prevent unbounded cache growth in long-running processes

### Performance

- **Connection pooling**: Configurable `ASAPClient` connection pooling; supports 1000+ concurrent connections
- **Manifest caching**: TTL-based manifest cache; `manifest_cache_size` parameter for LRU-bounded cache
- **Batch operations**: `send_batch` with HTTP/2 multiplexing for higher throughput
- **Compression**: Gzip and Brotli support; `Accept-Encoding` negotiation; ~70% bandwidth reduction for JSON payloads (>1 KB)

### Developer Experience

- **Examples**: 10+ real-world examples (auth patterns, rate limiting, state migration, streaming, multi-step workflow, MCP integration, error recovery, long-running, orchestration)
- **Testing utilities**: `asap.testing` fixtures, factories, and helpers; reduced test boilerplate
- **Trace visualization**: `asap trace` CLI command; optional Web UI for trace parsing
- **Dev server**: Hot reload, debug logging, REPL mode for local development
- **CLI**: `trace`, `repl`, `export-schemas`, `list-schemas`, `show-schema`, `validate-schema` commands

### Observability

- **OpenTelemetry**: Tracing integration with OTLP export; zero-config for development
- **Metrics**: Structured metrics (counters, histograms); Prometheus export; `asap_handler_errors_total` and transport client metrics
- **Dashboards**: Grafana dashboards (RED, detailed) for ASAP agents
- **Jaeger**: Integration test and trace export to Jaeger

### MCP (Model Context Protocol)

- **Full MCP implementation**: MCP server/client; `serve_stdio`; tool call/result, resource fetch/data payloads
- **Validation**: Parse error handling, tool args validation, sanitized error responses
- **Interop**: Default `request_id_type=str` for interoperability with MCP clients

---

## Performance Improvements

### Benchmarks (from `benchmarks/RESULTS.md`)

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| **RPS** | 1,532 | ≥ 800 | ✅ |
| **p95 Latency (50 users)** | 21 ms | < 50 ms | ✅ |
| **p95 Latency (10 users)** | ~5 ms | < 5 ms | ✅ |
| **Error Rate** | 0% | < 0.1% | ✅ |
| **Memory Leaks** | None | None | ✅ |

### Throughput & Scaling

- **Load test**: 50 concurrent users, 30s run → 1,532 RPS sustained
- **Stress test**: Linear scaling up to 50+ users; no breaking point observed
- **Compression**: ~70% size reduction for 1 MB JSON; Brotli 10–20% better than gzip
- **Connection pooling**: 1000+ concurrent connections supported
- **Manifest caching**: High hit rate with configurable TTL and LRU eviction

### Recommendations for Production

1. **Horizontal scaling**: Deploy multiple instances for >1,500 RPS
2. **Connection pooling**: Use default client pooling for better throughput
3. **Compression**: Enabled by default for payloads >1 KB; install `brotli` for better ratio
4. **Monitoring**: Use `/asap/metrics` endpoint for Prometheus scraping

---

## Breaking Changes

**None.** v1.0.0 is backward compatible with v0.5.0 and v0.1.0.

### Minor Behavioral Changes

- **MCP `request_id_type`**: Default changed to `str` for better interoperability with MCP clients. If you rely on numeric IDs, pass `request_id_type=int` explicitly.

---

## Migration Guide

### From v0.5.0

No code changes required. All v0.5.0 code runs unchanged on v1.0.0. Contract tests validate the upgrade path.

### From v0.1.0

- **Nonce**: If using nonce validation, ensure `require_nonce=True` is set as in v0.5.0.
- **Auth**: Bearer token authentication and manifest auth schemes are validated.
- **Extensions**: Envelope extensions and timestamps are supported.
- **Contract tests**: Run `uv run pytest tests/contract/` to verify your payloads and envelopes.

### From A2A / MCP

See [docs/migration.md](../docs/migration.md) for detailed mapping from A2A and MCP to ASAP envelope and payload structures.

---

## Contributors

- **Adrianno Esnarriaga Sereno** – Lead development, architecture, testing, documentation

---

## Links

- **Changelog**: [CHANGELOG.md](../CHANGELOG.md)
- **Documentation**: [docs/](https://asap-protocol.readthedocs.io/)
- **Benchmarks**: [benchmarks/RESULTS.md](../benchmarks/RESULTS.md)
- **Troubleshooting**: [docs/troubleshooting.md](../docs/troubleshooting.md)
- **Security**: [SECURITY.md](../SECURITY.md)
