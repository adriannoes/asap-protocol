# Workflow → ASAP connector (OpenAPI reuse)

Runnable demo: builds an ASAP app from a **workflow-shaped** OpenAPI fragment
(`openapi-fragment.json`) that mimics an n8n/Activepieces-style HTTP workflow
API, runs **Compliance Harness v2** (expects score **1.0**), and invokes
`listWorkflows` in-process. By default the upstream API is **mocked** (offline,
no SaaS credentials).

Spike notes: [DESIGN.md](./DESIGN.md).

## Prerequisites

- Python 3.13+
- `uv`

Install the OpenAPI extra:

```bash
uv sync --extra openapi
```

Installs optional OpenAPI adapter dependencies used by this example.

## Run (default: bundled fragment + mock upstream)

From the repository root:

```bash
uv run python examples/workflow_asap_connector/main.py
```

Runs Compliance Harness v2 then invokes `listWorkflows` against the mock upstream.

### Manual smoke — expected output

You should see lines similar to:

```text
skills: ['getWorkflow', 'listWorkflows', 'triggerWorkflow']
12/12 checks passed (100%)
listWorkflows: 1 workflow(s) via 'workflows'
```

Harness summary must be **12/12 checks passed (100%)** (score **1.0**; non-zero exit if not).

## Optional live upstream

Point the fragment’s operations at a real workflow HTTP base URL (requires
connectivity). Use **HTTPS** for production upstreams and callbacks. Keep secrets
in the environment only — never commit tokens (see `.env.example` placeholders).

```bash
uv run python examples/workflow_asap_connector/main.py --live-base-url https://your-host.example/api/v1
```

Equivalent: `ASAP_WORKFLOW_BASE_URL=https://your-host.example/api/v1`.

`.env.example` shows `ASAP_WORKFLOW_BEARER_TOKEN` and `ASAP_WORKFLOW_WEBHOOK_SECRET`
as **illustrative** placeholders only — this demo does **not** read them. Setting
those env vars alone will not avoid upstream 401s. Wire live auth with
`resolve_headers` (Bearer / API key from env) as documented in
[automation connector security](../../docs/guides/automation-connector-security.md)
and [OpenAPI adapter — upstream auth](../../docs/adapters/openapi.md#upstream-auth-oa-009).

**MCP:** This example is OpenAPI-only and does **not** expose MCP. Auth Bridge
guidance is **N/A** here — see the security guide §7.

## What a remote agent sees

| Skill id | Upstream |
|----------|----------|
| `listWorkflows` | `GET /workflows` |
| `getWorkflow` | `GET /workflows/{workflowId}` |
| `triggerWorkflow` | `POST /workflows/{workflowId}/trigger` |

Manifest id: `urn:asap:agent:openapi-workflow-connector-example`. Discovery:
`/.well-known/asap/manifest.json` on the ASAP host.

## Compliance (2.5)

This example agent shape matches the PetStore OpenAPI demo: `create_app` +
manifest skills + `task.request` handler. **Compliance Harness v2** is invoked
in `main.py` and must score **1.0** on the happy path.

## Notes

- Reuses `asap.adapters.openapi` only (LAB2-001); no dedicated workflow adapter package.
- Identity / approval: this example does not configure `FreshSessionConfig`; see
  `docs/adapters/openapi.md` and `src/asap/adapters/openapi/approval.py` for production wiring.
- Security baseline (secrets, TLS, webhooks, rate limits, manifests):
  [docs/guides/automation-connector-security.md](../../docs/guides/automation-connector-security.md).
- Integration guide: [docs/integrations/workflow-connectors.md](../../docs/integrations/workflow-connectors.md).
