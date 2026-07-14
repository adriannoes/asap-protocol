# Automation connector security

Security baseline for **OpenAPI-backed workflow / automation connectors** that expose upstream HTTP APIs as ASAP skills (n8n-, Activepieces-, and similar workflow hosts).

**Status:** Maintained guide for Adapter Lab II (v2.5.3) and later. Applies to production-shaped connectors that reuse `asap.adapters.openapi` — not an experimental spike note. Listed under MkDocs **Guides** (near Security) and on the [docs home](../index.md).

## Scope

| In scope | Out of scope |
|----------|--------------|
| Secrets handling, TLS, webhooks, rate limits, manifests | Protocol or transport changes |
| Capability grants for connector skills | Replacing [Security Guide](../security.md) (Agent JWT, envelopes, nonce) |
| MCP Auth Bridge **when** a connector exposes MCP | Inventing HTTP/SSE MCP Auth Bridge |

**Primary example (OpenAPI only):** [`examples/workflow_asap_connector/`](https://github.com/adriannoes/asap-protocol/tree/main/examples/workflow_asap_connector) — see [Workflow connectors](../integrations/workflow-connectors.md).

**MCP Path A demo (separate):** [`examples/nemo_agent_toolkit_asap/`](https://github.com/adriannoes/asap-protocol/tree/main/examples/nemo_agent_toolkit_asap) — see [NeMo Agent Toolkit interop](../integrations/nemo-agent-toolkit.md).

## 1. Secrets: environment only

Never commit tokens, API keys, JWTs, or shared webhook secrets to the repository.

| Do | Do not |
|----|--------|
| Keep placeholders in `.env.example` | Commit `.env` or real credential values |
| Load secrets from the process environment (or a secrets manager) | Hard-code Bearer tokens in OpenAPI fragments, READMEs, or manifests |
| Document required variable names in the example README | Paste production tokens into issue trackers or CI logs |

Workflow connector placeholders (illustrative):

```bash
# From examples/workflow_asap_connector/.env.example
# ASAP_WORKFLOW_BASE_URL=https://your-host.example/api/v1
# ASAP_WORKFLOW_BEARER_TOKEN=replace-me
# ASAP_WORKFLOW_WEBHOOK_SECRET=replace-me
```

The happy-path demo uses a **mocked** upstream and does not require secrets. For live upstreams, inject auth via `resolve_headers` reading env vars — see [OpenAPI adapter — upstream auth](../adapters/openapi.md#upstream-auth-oa-009).

## 2. Least-privilege capability grants

Treat each OpenAPI `operationId` / ASAP skill as a separate capability. Grant only what callers need.

| Practice | Guidance |
|----------|----------|
| Narrow grants | Prefer `listWorkflows` / `getWorkflow` without `triggerWorkflow` for read-only agents |
| Constraints | Use capability constraints (resource ids, methods) where the grant model supports them — [Capabilities](../capabilities/index.md) |
| Approval strength | Map mutating verbs (`POST` / `DELETE`) to stronger approval (`webauthn` where appropriate) via OpenAPI `approval_strength` — [OpenAPI adapter](../adapters/openapi.md) |
| Public tools | Keep `public_tools` / unauthenticated skills to non-sensitive read paths only |

Do not ship a connector with a single “admin” grant that covers every workflow action.

## 3. HTTPS/TLS for callbacks and live upstreams

| Surface | Production expectation |
|---------|------------------------|
| Upstream workflow base URL | **HTTPS** (`https://…`). Prefer `require_https=True` on ASAP HTTP clients ([Security Guide — TLS](../security.md)) |
| ASAP endpoint in the manifest | Advertise `https://` origins, not plain `http://` |
| Webhook / callback URLs | Terminate TLS at a public HTTPS endpoint; do not expose internal HTTP-only hosts |

Local mock transports and loopback HTTP are fine for offline demos. Live `--live-base-url` / `ASAP_WORKFLOW_BASE_URL` runs should use HTTPS.

## 4. Webhook authenticity

If the connector receives workflow platform webhooks (run completed, status updates), verify authenticity before acting on the payload.

| Mechanism | Guidance |
|-----------|----------|
| Shared secret / HMAC signature | Store the secret in env (for example `ASAP_WORKFLOW_WEBHOOK_SECRET`); verify the platform’s signature header on every request |
| Timestamp / replay window | Reject stale signatures; align with envelope age limits where ASAP envelopes are involved ([Security Guide](../security.md)) |
| TLS alone | **Not** sufficient — anyone who can POST to a public URL can forge events without a shared secret |

Do not put webhook secrets in the OpenAPI fragment or the agent manifest.

## 5. Rate limits and abuse

Connectors amplify risk: a single ASAP skill can trigger expensive upstream workflow runs.

| Layer | Guidance |
|-------|----------|
| ASAP transport | Keep default per-sender rate limits (`ASAP_RATE_LIMIT` / `create_app(rate_limit=…)`) — [Security Guide — rate limiting](../security.md#rate-limiting) |
| Mutating skills | Prefer stricter limits or approval gates on `triggerWorkflow`-class operations |
| Upstream quotas | Respect workflow-host rate limits; map `429` / retry headers to recoverable errors where appropriate |
| Abuse signals | Monitor repeated grant denials, oversized bodies (`ASAP_MAX_REQUEST_SIZE`), and burst traffic on webhook endpoints |

## 6. What not to put in manifests

The well-known manifest is often **publicly readable**. Never advertise secrets or privileged internals.

| Forbidden in manifests / OpenAPI fragments committed to git | Prefer |
|-------------------------------------------------------------|--------|
| API keys, Bearer tokens, passwords, webhook secrets | Env + `resolve_headers` |
| Internal URLs with embedded credentials (`https://user:pass@…`) | Separate base URL + auth headers from env |
| Private VPC hostnames that should stay undiscoverable | Public HTTPS gateway or private deployment without public well-known |
| Full production customer identifiers as default skill examples | Synthetic ids in docs and offline mocks |

Skill descriptions and JSON Schemas should describe **shape**, not credentials.

## 7. MCP Auth Bridge (when applicable)

### Workflow primary example — N/A

[`examples/workflow_asap_connector/`](https://github.com/adriannoes/asap-protocol/tree/main/examples/workflow_asap_connector) is **OpenAPI-only**. It does **not** expose an MCP server or MCP tools. MCP Auth Bridge guidance does **not** apply to that example.

### Mode A vs Mode B

| Mode | What it is | Docs |
|------|------------|------|
| **Mode A** | Native stdio MCP server wrapped with `protect_server` (Agent JWT + capability grants on `tools/call`) | [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) |
| **Mode B** | MCP payloads carried inside ASAP envelopes | [MCP integration](../mcp-integration.md) |

### NeMo Path A (uses Mode A)

[`examples/nemo_agent_toolkit_asap/`](https://github.com/adriannoes/asap-protocol/tree/main/examples/nemo_agent_toolkit_asap) demonstrates Mode A: NAT `mcp_client` stdio → ASAP `protect_server`.

!!! warning "Env JWT fallback is dev-only"

    Path A may set `allow_env_jwt_fallback=True` and read `ASAP_AGENT_JWT` because NAT does not pass `_meta.asap_agent_jwt`. That fallback is **unsafe for multi-tenant production**. Prefer in-band `_meta.asap_agent_jwt` (or a future HTTP Auth Bridge). Details: [MCP Auth Bridge — dev-only environment fallback](../adapters/mcp-auth-bridge.md#dev-only-environment-fallback) and [NeMo Agent Toolkit interop](../integrations/nemo-agent-toolkit.md).

## 8. Checklist (production-shaped connector)

- [ ] Secrets only in env / secret store; `.env.example` uses placeholders
- [ ] Live upstream and callback URLs use **HTTPS**
- [ ] Webhooks verified with a shared secret or signature from env
- [ ] Capability grants least-privilege; mutating skills gated
- [ ] Rate limits enabled; request size limits left on
- [ ] Manifest and committed OpenAPI fragments contain **no** credentials or credential-bearing URLs
- [ ] If MCP tools are exposed: Mode A via [MCP Auth Bridge](../adapters/mcp-auth-bridge.md); no production env JWT fallback

## Related

- Runnable OpenAPI example: [`examples/workflow_asap_connector/`](https://github.com/adriannoes/asap-protocol/tree/main/examples/workflow_asap_connector)
- [Workflow connectors](../integrations/workflow-connectors.md)
- [OpenAPI adapter](../adapters/openapi.md)
- [Security Guide](../security.md) — transport TLS, rate limits, Agent JWT
- [MCP Auth Bridge](../adapters/mcp-auth-bridge.md) · [MCP integration](../mcp-integration.md)
- [NeMo Agent Toolkit interop](../integrations/nemo-agent-toolkit.md) (Path A Mode A demo)
