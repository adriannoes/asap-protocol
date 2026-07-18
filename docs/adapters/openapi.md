# OpenAPI adapter (Python)

The `asap.adapters.openapi` package derives ASAP **skills**, JSON Schemas, and a **`task.request` handler** from an **OpenAPI 3.0 or 3.1** document, then proxies each invocation to the upstream HTTP API described by the spec.

**Requires** the optional extra:

```bash
uv add 'asap-protocol[openapi]'
# or
pip install 'asap-protocol[openapi]'
```

This pulls in `openapi-pydantic` for validation and parsing.

## Architecture

```text
OpenAPI document (URL or local .json)
        │
        ▼
  load_spec()  ──► openapi-pydantic root model (3.0 / 3.1)
        │
        ▼
  map_openapi_to_capabilities()
        │  operationId → skill id; parameters + JSON body → input schema;
        │  200/201 application/json → output schema; OA-010 execution kind
        ▼
  OpenAPIUpstreamHandler  ◄── httpx.AsyncClient (spec fetch + upstream calls)
        │
        ▼
  create_openapi_task_handler()  ──► HandlerRegistry["task.request"]
        │
        ▼
  OpenAPIAdapterBundle.manifest + .registry  ──► create_app()
```

- **One async entrypoint**: `create_from_openapi` builds an `OpenAPIAdapterBundle` with a ready-to-use `Manifest`, `HandlerRegistry`, and metadata (`require_webauthn_for`, `upstream_base_url`).
- **Upstream base URL**: Taken from `servers[0].url` when it is absolute (`https://…`). If the spec uses a **relative** server URL (e.g. `/api/v3`), the adapter resolves it with `urllib.parse.urljoin` against the document URL used to load the spec. Loading from a **local file only** with a relative server requires `upstream_base_url=`.
- **Execution modes (OA-010)**: The mapper classifies each operation as `sync` or `streaming` (response advertises `text/event-stream`). The manifest’s `Capability.streaming` flag is set if any operation is streaming; the current **`task.request` path** still performs a single HTTP round-trip and returns JSON (or wrapped non-object JSON). Treat streaming as **metadata for future wiring**, not a full ASAP streaming handler yet. (The former `async_polling` variant for `202` + `Location` was pruned in v2.5.1 Sprint S3 as dead metadata — no production path consumed it; such operations now classify as `sync`.)
- **Identity & capability grants**: `create_app` still provisions identity and capability HTTP routes. Use [`FreshSessionConfig`](../security/self-authorization-prevention.md) and `bundle.require_webauthn_for` (from `approval_strength`) for approval/WebAuthn policy; registering `CapabilityDefinition` rows in `app.state.capability_registry` is separate from OpenAPI mapping.

## Quick usage

Always pass a shared **`httpx.AsyncClient`** (timeout, proxies, mock transports, MTLS as you configure it):

```python
import asyncio
import httpx

from asap.adapters.openapi import create_from_openapi
from asap.transport.server import create_app


async def main() -> None:
    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http:
        bundle = await create_from_openapi(
            spec_url="https://api.example.com/openapi.json",
            http_client=http,
            default_capabilities=["GET", "HEAD"],
            upstream_base_url="https://api.example.com",  # optional override
            manifest_id="urn:asap:agent:my-openapi-bridge",
            asap_endpoint="https://my-host.example/asap",
        )

    app = create_app(bundle.manifest, bundle.registry)


if __name__ == "__main__":
    asyncio.run(main())
```

### Approval strength (OA-008) and registration

Map HTTP methods or `operationId` values to `session` vs `webauthn`, then feed the derived list into `FreshSessionConfig`:

```python
from asap.auth.self_auth import FreshSessionConfig
from asap.transport.server import create_app

bundle = await create_from_openapi(
    spec_url="https://api.example.com/openapi.json",
    http_client=http,
    approval_strength={"GET": "session", "POST": "webauthn", "DELETE": "webauthn"},
)

app = create_app(
    bundle.manifest,
    bundle.registry,
    identity_fresh_session_config=FreshSessionConfig(
        require_webauthn_for=bundle.require_webauthn_for,
    ),
)
```

Details: [Self-authorization prevention](../security/self-authorization-prevention.md).

### Upstream auth (OA-009)

Pass a callable `(session) -> dict[str, str]` to inject headers (for example `Authorization`); operation-defined header parameters still merge and may override callback keys:

```python
def resolve_headers(session: object | None) -> dict[str, str]:
    _ = session
    return {"Authorization": "Bearer <token>"}


bundle = await create_from_openapi(
    spec_url="https://api.example.com/openapi.json",
    http_client=http,
    resolve_headers=resolve_headers,
)
```

## Configuration reference

| Parameter | Description |
|:----------|:-------------|
| `spec_url` | HTTP(S) URL of the OpenAPI document (exactly one of `spec_url` or `spec_path`). |
| `spec_path` | Local path to a UTF-8 **JSON** document (`.json`). YAML is not supported yet. |
| `http_client` | `httpx.AsyncClient` used to fetch the spec (if URL) and for all upstream API calls. |
| `upstream_base_url` | Overrides inferred base URL from `servers`. |
| `default_capabilities` | `"all"`, a single method string (`"GET"`), a sequence of methods, or a callable `(OpenAPIOperationContext) -> bool`. See `map_openapi_to_capabilities`. |
| `approval_strength` | Optional `dict[str, str]` mapping HTTP verbs and/or `operationId` to `session` or `webauthn`; populates `bundle.require_webauthn_for` for WebAuthn-gated capability names. |
| `resolve_headers` | Optional callback for extra request headers to the upstream. |
| `manifest_id` | ASAP manifest id (default `urn:asap:agent:openapi-adapter`). |
| `manifest_name` | Overrides manifest name (default: `info.title`). |
| `asap_endpoint` | Value stored on `Manifest.endpoints.asap` (advertised to clients). |

**Bundle fields**

| Field | Meaning |
|:------|:--------|
| `manifest` | `Manifest` with skills mirroring the selected operations. |
| `registry` | `HandlerRegistry` with `task.request` → OpenAPI proxy handler. |
| `capabilities` | List of `OpenAPICapability` (HTTP method, path template, `operation_id`, execution kind, etc.). |
| `require_webauthn_for` | Capability names requiring WebAuthn when `approval_strength` is set. |
| `upstream_base_url` | Resolved base URL used by the handler. |

## Runnable example and compliance

The repo includes `examples/openapi_petstore/`: bundled PetStore-shaped fragment, **Compliance Harness v2** in-process, and a call to `findPetsByStatus`. By default the upstream is **mocked** for reliability; use `--live` for the public PetStore URL (network; remote service may error).

```bash
uv sync --extra openapi
uv run python examples/openapi_petstore/main.py
```

See also [Compliance testing](../guides/compliance-testing.md), [CI compliance gate](../ci-compliance.md), and the thin [OpenAPI provider starter](../../examples/starters/openapi-provider/) (`examples/starters/openapi-provider/`).

## Common pitfalls

### Authentication and secrets

- The adapter does not read OpenAPI `securitySchemes` automatically. Use **`resolve_headers`** (Bearer, API keys, custom headers) or a dedicated gateway in front of the upstream.
- Never embed tokens in source; load from environment or a secret store and build headers at runtime.

### Relative `servers` and local specs

If the spec only declares `servers: [{ url: "/api/v3" }]` and you load from disk, the adapter cannot infer an absolute origin. Pass **`upstream_base_url`** explicitly.

### Polymorphism and complex schemas

- Input/output mapping focuses on `application/json` and inlines internal `#/components/schemas/` refs where possible. **`oneOf` / `anyOf`** at the top level of request or response bodies may not round-trip cleanly into strict JSON Schema validation everywhere; review generated `Skill` schemas before exposing them to untrusted callers.
- Non-JSON success bodies are returned as a small wrapper dict (e.g. `_text`, `_json`) depending on `Content-Type`.

### Large specifications

- Every operation can become a **skill**; large APIs (hundreds of paths) produce large manifests and handler indexes. Use **`default_capabilities`** (e.g. only `GET`) or a **callable filter** to trim surface area. Consider a curated spec or a gateway that exposes a subset.

### Public demo APIs

Third-party OpenAPI hosts may return **4xx/5xx** or change without notice. Prefer contract tests with **mocked `httpx`** transports for CI; use live URLs for manual exploration only.

### Streaming (SSE) vs ASAP streaming

Upstream **`text/event-stream`** is detected for metadata, but the default **`task.request`** handler does not bridge SSE into ASAP `TaskStream` envelopes. Document behavior if you expose streaming operations; a dedicated streaming handler may be required for full parity.

## Related documentation

- [Workflow connectors](../integrations/workflow-connectors.md) — reuse this adapter for n8n / Activepieces-style workflow HTTP APIs
- [Automation connector security](../guides/automation-connector-security.md) — production baseline for OpenAPI-backed connectors
- [Transport](../transport.md) — HTTP JSON-RPC, `create_app`
- [Security](../security.md) — auth schemes at the ASAP layer
- [Self-authorization prevention](../security/self-authorization-prevention.md) — `FreshSessionConfig`, WebAuthn
- [Error handling](../error-handling.md) — `FatalError`, `RecoverableError` from upstream proxying
- [PRD v2.3 OpenAPI adapter](https://github.com/adriannoes/asap-protocol/blob/main/product/prd/prd-v2.3-scale.md) — OA-* requirements (source of truth for scope)
