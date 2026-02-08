# Tasks: ASAP Protocol v1.1.0 Roadmap

> **High-level task overview** for v1.1.0 milestone (Identity + Discovery)
>
> **Parent PRD**: [roadmap-to-marketplace.md](../../product-specs/roadmap-to-marketplace.md)
> **Prerequisite**: v1.0.0 released ✅
> **Target Version**: v1.1.0
> **Focus**: Identity (OAuth2), Discovery (Well-known URI), Real-time (WebSocket)
>
> 💡 **For detailed step-by-step instructions**, see sprint files:
> - [S1: OAuth2 Foundation](./sprint-S1-oauth2-foundation.md)
> - [S2: Well-Known Discovery + Liveness](./sprint-S2-wellknown-discovery.md)
> - [S2.5: State Storage Interface](./sprint-S2.5-state-storage.md)
> - [S3: WebSocket Binding](./sprint-S3-websocket-binding.md)
> - [S4: Webhooks & Release](./sprint-S4-webhooks-release.md)

---

## Strategic Context

v1.1.0 lays the foundation for the Agent Marketplace by enabling:
- **Identity**: OAuth2/OIDC for enterprise agent authentication
- **Discovery**: Well-known URI for agents to find each other (before Registry)
- **Real-time**: WebSocket for low-latency agent-to-agent communication

See [SD-3 (WebSocket)](../../product-specs/roadmap-to-marketplace.md) and [SD-7 (Discovery)](../../product-specs/roadmap-to-marketplace.md) for rationale.

---

## Sprint S1: OAuth2 Foundation

**Goal**: Implement OAuth2 client and server support

### Tasks

- [x] 1.1 Implement OAuth2 client
  - Goal: Support `client_credentials` and `authorization_code` flows
  - Deliverable: `src/asap/auth/oauth2.py`
  - Details: [Auth Detailed - Task 1.1](./sprint-S1-oauth2-foundation.md#task-11-oauth2-client)

- [x] 1.2 Implement OAuth2 server integration
  - Goal: Protect ASAP endpoints with OAuth2 tokens
  - Deliverable: Middleware for token validation
  - Details: [Auth Detailed - Task 1.2](./sprint-S1-oauth2-foundation.md#task-12-oauth2-server)

- [x] 1.3 Add OIDC discovery
  - Goal: Auto-discover OAuth2 endpoints from `.well-known/openid-configuration`
  - Deliverable: `src/asap/auth/oidc.py`
  - Details: [Auth Detailed - Task 1.3](./sprint-S1-oauth2-foundation.md#task-13-oidc-discovery)

- [x] 1.4 Custom Claims identity binding (ADR-17)
  - Goal: Map IdP `sub` to ASAP `agent_id` via JWT Custom Claims + allowlist fallback
  - Deliverable: Middleware update + `ASAP_AUTH_SUBJECT_MAP` config
  - Details: [Auth Detailed - Task 1.4](./sprint-S1-oauth2-foundation.md#task-14-custom-claims-identity-binding)

### Definition of Done
- [x] OAuth2 client credentials flow working
- [x] Token validation middleware functional
- [x] OIDC discovery auto-configures endpoints
- [x] Custom Claims identity binding functional (ADR-17)
- [ ] Test coverage >95%

---

## Sprint S2: Well-Known Discovery

**Goal**: Implement basic discovery before Registry (per SD-7)

### Tasks

- [x] 2.1 Implement well-known endpoint
  - Goal: Serve `/.well-known/asap/manifest.json`
  - Deliverable: `src/asap/discovery/wellknown.py`
  - Details: [Auth Detailed - Task 2.1](./sprint-S2-wellknown-discovery.md#task-21-well-known-endpoint)

- [ ] 2.2 Implement manifest fetching
  - Goal: Client-side discovery from well-known URI
  - Deliverable: `ASAPClient.discover(base_url)` method
  - Details: [Auth Detailed - Task 2.2](./sprint-S2-wellknown-discovery.md#task-22-manifest-discovery)

- [ ] 2.3 Add DNS-SD support (optional)
  - Goal: Local network discovery via mDNS
  - Priority: P3 (defer to v1.1.1+)
  - Details: [Auth Detailed - Task 2.3](./sprint-S2-wellknown-discovery.md#task-23-dns-sd-support)

- [x] 2.4 Lite Registry client (SD-11, ADR-15)
  - Goal: SDK method to discover agents from static Lite Registry on GitHub Pages
  - Deliverable: `src/asap/discovery/registry.py` + `discover_from_registry()` method
  - Details: [Discovery Detailed - Task 2.4](./sprint-S2-wellknown-discovery.md#task-24-lite-registry-client-sd-11)

- [ ] 2.5 Implement Agent Liveness/Health endpoint
  - Goal: `GET /.well-known/asap/health` + `ttl_seconds` in Manifest (per SD-10, ADR-14)
  - Deliverable: `src/asap/discovery/health.py`
  - Details: [Discovery Detailed - Task 2.5](./sprint-S2-wellknown-discovery.md#task-25-agent-liveness--health)

### Definition of Done
- [ ] Well-known endpoint serves manifest
- [ ] Client can discover agents from URL
- [x] Lite Registry client discovers agents from GitHub Pages
- [ ] Health endpoint returns agent status
- [ ] Manifest includes `ttl_seconds` field
- [ ] Integration tests validate flow
- [ ] Docs updated

---

## Sprint S2.5: State Storage Interface

**Goal**: Implement persistent state storage with SQLite reference implementation (per SD-9, ADR-13)

### Context

The v0 spec listed "First-class persistent state" as a key design goal. Currently only `InMemorySnapshotStore` exists — state is lost on restart. This sprint defines the `MeteringStore` interface (for v1.3 Economics) and provides a production-ready SQLite implementation.

### Tasks

- [ ] 2.5.1 Define MeteringStore Protocol
  - Goal: Abstract interface for usage metering data (foundation for v1.3)
  - Deliverable: `src/asap/state/metering.py`
  - Details: [State Storage Detailed - Task 2.5.1](./sprint-S2.5-state-storage.md#task-251-meteringstoremeteringstore-protocol)

- [ ] 2.5.2 Implement SQLiteSnapshotStore
  - Goal: Persistent `SnapshotStore` using SQLite via `aiosqlite`
  - Deliverable: `src/asap/state/stores/sqlite.py`
  - Details: [State Storage Detailed - Task 2.5.2](./sprint-S2.5-state-storage.md#task-252-sqlitesnapshotstore)

- [ ] 2.5.3 Refactor InMemorySnapshotStore
  - Goal: Move to `src/asap/state/stores/memory.py`, maintain backward compat
  - Details: [State Storage Detailed - Task 2.5.3](./sprint-S2.5-state-storage.md#task-253-refactor-inmemorysnapshotstore)

- [ ] 2.5.4 Storage configuration and auto-detection
  - Goal: Environment-based storage backend selection
  - Details: [State Storage Detailed - Task 2.5.4](./sprint-S2.5-state-storage.md#task-254-storage-configuration)

- [ ] 2.5.5 Best Practices: Agent Failover & Migration
  - Goal: Formal documentation for state handover and failover patterns
  - Deliverable: `docs/best-practices/agent-failover-migration.md` + failover example
  - Details: [State Storage Detailed - Task 2.5.5](./sprint-S2.5-state-storage.md#task-255-best-practices--agent-failover--migration)

### Definition of Done
- [ ] SQLite store passes all existing SnapshotStore tests
- [ ] MeteringStore Protocol defined with in-memory + SQLite impls
- [ ] Backward compatibility maintained (InMemorySnapshotStore still importable)
- [ ] Best Practices: Failover & Migration documented
- [ ] Test coverage >95%
- [ ] Storage example added to examples/

---

## Sprint S3: WebSocket Binding

**Goal**: Implement WebSocket transport for real-time communication (per SD-3)

### Tasks

- [ ] 3.1 Implement WebSocket server
  - Goal: Accept WebSocket connections for ASAP messages
  - Deliverable: `src/asap/transport/websocket.py`
  - Details: [Transport Detailed - Task 3.1](./sprint-S3-websocket-binding.md#task-31-websocket-server)

- [ ] 3.2 Implement WebSocket client
  - Goal: Connect to agents via WebSocket
  - Deliverable: `ASAPClient.connect_ws()` method
  - Details: [Transport Detailed - Task 3.2](./sprint-S3-websocket-binding.md#task-32-websocket-client)

- [ ] 3.3 Add connection management
  - Goal: Heartbeat, reconnection, connection pooling
  - Details: [Transport Detailed - Task 3.3](./sprint-S3-websocket-binding.md#task-33-connection-management)

- [ ] 3.4 MessageAck for WebSocket reliability (ADR-16)
  - Goal: Selective ack for state-changing messages + `requires_ack` field on Envelope
  - Deliverable: `MessageAck` payload, auto-ack for critical payloads
  - Details: [Transport Detailed - Task 3.4](./sprint-S3-websocket-binding.md#task-34-message-acknowledgment-adr-16)

- [ ] 3.5 AckAwareClient with timeout/retry (ADR-16)
  - Goal: Client-side ack tracking, retransmission, circuit breaker integration
  - Deliverable: Pending ack tracker, timeout detection, retry with idempotency
  - Details: [Transport Detailed - Task 3.5](./sprint-S3-websocket-binding.md#task-35-ackAwareclient-adr-16)

### Definition of Done
- [ ] WebSocket server accepts connections
- [ ] Client can send/receive via WebSocket
- [ ] Heartbeat keeps connections alive
- [ ] Graceful reconnection on disconnect
- [ ] MessageAck for state-changing messages (ADR-16)
- [ ] AckAwareClient with timeout/retry/circuit breaker (ADR-16)
- [ ] Test coverage >95%

---

## Sprint S4: Webhooks & Release

**Goal**: Implement webhook callbacks and release v1.1.0

### Tasks

- [ ] 4.1 Implement webhook delivery
  - Goal: POST callbacks to registered URLs
  - Security: Validate callback URLs (prevent SSRF per backlog)
  - Deliverable: `src/asap/transport/webhook.py`
  - Details: [Transport Detailed - Task 4.1](./sprint-S4-webhooks-release.md#task-41-webhook-delivery)

- [ ] 4.2 Add callback retry logic
  - Goal: Retry failed deliveries with exponential backoff
  - Details: [Transport Detailed - Task 4.2](./sprint-S4-webhooks-release.md#task-42-callback-retry-logic)

- [ ] 4.3 Migrate from slowapi (Tech Debt)
  - Goal: Replace slowapi with custom rate limiter to fix deprecation warnings
  - Deliverable: `src/asap/transport/rate_limit.py`
  - Details: [Transport Detailed - Task 4.3](./sprint-S4-webhooks-release.md#task-43-migrate-from-slowapi-tech-debt)

- [ ] 4.4 Run comprehensive testing
  - Goal: All tests pass, benchmarks meet targets
  - Details: [Transport Detailed - Task 4.4](./sprint-S4-webhooks-release.md#task-44-comprehensive-testing)

- [ ] 4.5 Security Model documentation (ADR-17)
  - Goal: Document v1.1 trust model limitations + Custom Claims setup guide
  - Deliverable: `docs/security/v1.1-security-model.md`
  - Details: [Release Detailed - Task 4.5](./sprint-S4-webhooks-release.md#task-45-security-model-documentation-adr-17)

- [ ] 4.6 Prepare release materials
  - Goal: CHANGELOG, docs, version bump
  - Details: [Transport Detailed - Task 4.6](./sprint-S4-webhooks-release.md#task-46-release-preparation)

- [ ] 4.7 Build and publish
  - Goal: PyPI, GitHub release, Docker
  - Details: [Transport Detailed - Task 4.7](./sprint-S4-webhooks-release.md#task-47-build-and-publish)

### Definition of Done
- [ ] Webhooks deliver reliably
- [ ] SSRF protection working
- [ ] Security Model document published (ADR-17)
- [ ] All tests pass
- [ ] v1.1.0 on PyPI

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| S1 | 4 | OAuth2/OIDC + Custom Claims (ADR-17) | 6-8 |
| S2 | 5 | Well-known Discovery + Lite Registry (SD-11) + Liveness | 6-8 |
| S2.5 | 5 | State Storage + Best Practices Failover | 6-8 |
| S3 | 5 | WebSocket + MessageAck + AckAwareClient (ADR-16) | 7-9 |
| S4 | 7 | Webhooks + slowapi migration + Security Docs + Release | 6-8 |

**Total**: 26 high-level tasks across 5 sprints

---

## Progress Tracking

**Overall Progress**: 6/26 tasks completed (23%)

**Sprint Status**:
- ⬜ S1: 4/4 tasks (100%) — includes Custom Claims (ADR-17)
- ⬜ S2: 2/5 tasks (40%) — includes Lite Registry (SD-11, ADR-15)
- ⬜ S2.5: 0/5 tasks (0%) — includes Best Practices Failover
- ⬜ S3: 0/5 tasks (0%) — includes MessageAck + AckAwareClient (ADR-16)
- ⬜ S4: 0/7 tasks (0%) — includes slowapi migration + Security Model docs (ADR-17)

**Last Updated**: 2026-02-08

---

## Related Documents

- **Detailed Tasks**: See sprint files listed at top
- **Parent Roadmap**: [roadmap-to-marketplace.md](../../product-specs/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../product-specs/vision-agent-marketplace.md)
- **Legacy Backlog**: [backlog-v1.1.md](./backlog-v1.1.md) (incorporated into this roadmap)
