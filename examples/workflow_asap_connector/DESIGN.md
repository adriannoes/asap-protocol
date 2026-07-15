# Workflow → ASAP connector spike notes (S1 / LAB2-001)

## Target

**Local mock workflow OpenAPI** that mimics an n8n / Activepieces-style HTTP
workflow webhook/API — **not** a live n8n Cloud or Activepieces SaaS instance.

Happy path uses `httpx.MockTransport` against `servers[0].url`
(`http://workflow.mock/api/v1`). Optional `--live-base-url` /
`ASAP_WORKFLOW_BASE_URL` can point at a real host later; credentials stay out of
the example (placeholders only in `.env.example`).

## Skill mapping (OpenAPI `operationId` → ASAP skill id)

| Workflow action | HTTP | `operationId` / skill id |
|-----------------|------|--------------------------|
| List workflows | `GET /workflows` | `listWorkflows` |
| Get one workflow | `GET /workflows/{workflowId}` | `getWorkflow` |
| Trigger / execute a run | `POST /workflows/{workflowId}/trigger` | `triggerWorkflow` |

The OpenAPI adapter maps each `operationId` to a manifest skill id unchanged
(see `map_openapi_to_capabilities` in `asap.adapters.openapi`).

## Why OpenAPI reuse satisfies LAB2-001

- **No new adapter package** under `src/asap/adapters/`.
- Compose existing `create_from_openapi` + `create_app` + Compliance Harness v2,
  same pattern as `examples/openapi_petstore/`.
- No public methods added to `transport/server.py` or `transport/client.py`.
- Workflow HTTP APIs that already expose (or can expose) OpenAPI become ASAP
  capabilities without a protocol fork.

## What a remote agent sees

After `create_from_openapi`, the ASAP manifest advertises skills
`listWorkflows`, `getWorkflow`, and `triggerWorkflow`. A remote agent discovers
them via `/.well-known/asap/manifest.json` and invokes them with
`task.request` / `skill_id` like any other ASAP capability; the handler proxies
to the upstream workflow HTTP API.
