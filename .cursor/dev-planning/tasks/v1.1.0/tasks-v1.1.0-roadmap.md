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
> - [S2: Well-Known Discovery](./sprint-S2-wellknown-discovery.md)
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

- [ ] 1.1 Implement OAuth2 client
  - Goal: Support `client_credentials` and `authorization_code` flows
  - Deliverable: `src/asap/auth/oauth2.py`
  - Details: [Auth Detailed - Task 1.1](./sprint-S1-oauth2-foundation.md#task-11-oauth2-client)

- [ ] 1.2 Implement OAuth2 server integration
  - Goal: Protect ASAP endpoints with OAuth2 tokens
  - Deliverable: Middleware for token validation
  - Details: [Auth Detailed - Task 1.2](./sprint-S1-oauth2-foundation.md#task-12-oauth2-server)

- [ ] 1.3 Add OIDC discovery
  - Goal: Auto-discover OAuth2 endpoints from `.well-known/openid-configuration`
  - Deliverable: `src/asap/auth/oidc.py`
  - Details: [Auth Detailed - Task 1.3](./sprint-S1-oauth2-foundation.md#task-13-oidc-discovery)

### Definition of Done
- [ ] OAuth2 client credentials flow working
- [ ] Token validation middleware functional
- [ ] OIDC discovery auto-configures endpoints
- [ ] Test coverage >95%

---

## Sprint S2: Well-Known Discovery

**Goal**: Implement basic discovery before Registry (per SD-7)

### Tasks

- [ ] 2.1 Implement well-known endpoint
  - Goal: Serve `/.well-known/asap/manifest.json`
  - Deliverable: `src/asap/discovery/wellknown.py`
  - Details: [Auth Detailed - Task 2.1](./sprint-S2-wellknown-discovery.md#task-21-well-known-endpoint)

- [ ] 2.2 Implement manifest fetching
  - Goal: Client-side discovery from well-known URI
  - Deliverable: `ASAPClient.discover(base_url)` method
  - Details: [Auth Detailed - Task 2.2](./sprint-S2-wellknown-discovery.md#task-22-manifest-discovery)

- [ ] 2.3 Add DNS-SD support (optional)
  - Goal: Local network discovery via mDNS
  - Priority: P3 (nice-to-have)
  - Details: [Auth Detailed - Task 2.3](./sprint-S2-wellknown-discovery.md#task-23-dns-sd-support)

### Definition of Done
- [ ] Well-known endpoint serves manifest
- [ ] Client can discover agents from URL
- [ ] Integration tests validate flow
- [ ] Docs updated

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

### Definition of Done
- [ ] WebSocket server accepts connections
- [ ] Client can send/receive via WebSocket
- [ ] Heartbeat keeps connections alive
- [ ] Graceful reconnection on disconnect
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
  - Details: [Transport Detailed - Task 4.2](./sprint-S4-webhooks-release.md#task-42-callback-retry)

- [ ] 4.3 Run comprehensive testing
  - Goal: All tests pass, benchmarks meet targets
  - Details: [Transport Detailed - Task 4.3](./sprint-S4-webhooks-release.md#task-43-comprehensive-testing)

- [ ] 4.4 Prepare release materials
  - Goal: CHANGELOG, docs, version bump
  - Details: [Transport Detailed - Task 4.4](./sprint-S4-webhooks-release.md#task-44-release-preparation)

- [ ] 4.5 Build and publish
  - Goal: PyPI, GitHub release, Docker
  - Details: [Transport Detailed - Task 4.5](./sprint-S4-webhooks-release.md#task-45-build-and-publish)

### Definition of Done
- [ ] Webhooks deliver reliably
- [ ] SSRF protection working
- [ ] All tests pass
- [ ] v1.1.0 on PyPI

---

## Summary

| Sprint | Tasks | Focus | Estimated Days |
|--------|-------|-------|----------------|
| S1 | 3 | OAuth2/OIDC | 5-7 |
| S2 | 3 | Well-known Discovery | 4-5 |
| S3 | 3 | WebSocket Binding | 6-8 |
| S4 | 5 | Webhooks + Release | 5-7 |

**Total**: 14 high-level tasks across 4 sprints

---

## Progress Tracking

**Overall Progress**: 0/14 tasks completed (0%)

**Sprint Status**:
- ⬜ S1: 0/3 tasks (0%)
- ⬜ S2: 0/3 tasks (0%)
- ⬜ S3: 0/3 tasks (0%)
- ⬜ S4: 0/5 tasks (0%)

**Last Updated**: 2026-02-05

---

## Related Documents

- **Detailed Tasks**: See sprint files listed at top
- **Parent Roadmap**: [roadmap-to-marketplace.md](../../product-specs/roadmap-to-marketplace.md)
- **Vision**: [vision-agent-marketplace.md](../../product-specs/vision-agent-marketplace.md)
- **Legacy Backlog**: [backlog-v1.1.md](./backlog-v1.1.md) (incorporated into this roadmap)
