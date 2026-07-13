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
Compliance Harness v2: ...
listWorkflows: 1 workflow(s) via 'workflows'
```

Exact harness summary text may vary; score must be **1.0** (non-zero exit if not).

## Optional live upstream

Point the fragment’s operations at a real workflow HTTP base URL (requires
connectivity; auth is your responsibility — use env placeholders, never commit
secrets):

```bash
uv run python examples/workflow_asap_connector/main.py --live-base-url https://your-host.example/api/v1
```

Equivalent: `ASAP_WORKFLOW_BASE_URL=https://your-host.example/api/v1`.

`.env.example` may show `ASAP_WORKFLOW_BEARER_TOKEN` as an **illustrative** placeholder only —
this demo does **not** read it. Live auth via `resolve_headers` is deferred to the S2
security guide; setting the env var alone will not avoid upstream 401s.

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
