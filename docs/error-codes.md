# ASAP JSON-RPC error codes

ASAP uses the JSON-RPC 2.0 reserved application error band **-32000** through **-32059** (PRD §4.7). Standard JSON-RPC codes (e.g. `-32602` Invalid params) remain valid for transport-level issues that are not ASAP-specific.

Each native `ASAPError` carries:

- **Taxonomy URI** (`code` field), e.g. `asap:protocol/invalid_timestamp`
- **Numeric** `rpc_code` in the band below
- Optional recovery hints: `retry_after_ms`, `alternative_agents`, `fallback_action`

JSON-RPC error responses from ASAP servers include the numeric `rpc_code` as the top-level `error.code`. The `error.data` object repeats taxonomy, structured `details`, `recoverable`, and recovery hints. Clients map these to `RecoverableError` / `FatalError` (and remote-specific subclasses) via `asap.errors.remote_rpc_error_from_json`.

## Ranges

| Range | Category |
|-------|----------|
| -32000 .. -32009 | Protocol |
| -32010 .. -32019 | Routing |
| -32020 .. -32029 | Capability |
| -32030 .. -32039 | Execution / transport |
| -32040 .. -32049 | Resource |
| -32050 .. -32059 | Security |

## Registry (constants in `asap.errors`)

| rpc_code | Constant | Taxonomy (typical) |
|----------|----------|-------------------|
| -32000 | `RPC_INVALID_STATE` | `asap:protocol/invalid_state` |
| -32001 | `RPC_MALFORMED_ENVELOPE` | `asap:protocol/malformed_envelope` |
| -32002 | `RPC_INVALID_TIMESTAMP` | `asap:protocol/invalid_timestamp` |
| -32003 | `RPC_INVALID_NONCE` | `asap:protocol/invalid_nonce` |
| -32010 | `RPC_TASK_NOT_FOUND` | `asap:task/not_found` |
| -32011 | `RPC_CIRCUIT_OPEN` | `asap:transport/circuit_open` |
| -32012 | `RPC_HANDLER_NOT_FOUND` | `asap:transport/handler_not_found` |
| -32020 | `RPC_UNSUPPORTED_AUTH_SCHEME` | `asap:auth/unsupported_scheme` |
| -32030 | `RPC_TASK_ALREADY_COMPLETED` | `asap:task/already_completed` |
| -32031 | `RPC_THREAD_POOL_EXHAUSTED` | `asap:transport/thread_pool_exhausted` |
| -32032 | `RPC_CONNECTION_ERROR` | `asap:transport/connection_error` |
| -32033 | `RPC_TIMEOUT` | `asap:transport/timeout` |
| -32034 | `RPC_REMOTE_GENERIC` | `asap:rpc/remote_error` (client-side mapping for non-ASAP JSON-RPC codes) |
| -32040 | `RPC_RESOURCE_EXHAUSTED` | (reserved) |
| -32050 | `RPC_WEBHOOK_URL_REJECTED` | `asap:transport/webhook_url_rejected` |
| -32051 | `RPC_AGENT_REVOKED` | `asap:agent/revoked` |
| -32052 | `RPC_SIGNATURE_VERIFICATION` | `asap:error/signature-verification` |

## References

- PRD: `.cursor/product-specs/prd/prd-v2.2-protocol-hardening.md` §4.7
- ADR-012: `docs/adr/ADR-012-error-taxonomy.md`
