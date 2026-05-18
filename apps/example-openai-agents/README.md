# OpenAI Agents SDK · ASAP example (`example-openai-agents`)

Minimal **Node** demo that runs an OpenAI **`Agent`** from **`@openai/agents`** with ASAP capability **`tool()`** instances from **`@asap-protocol/openai-agents`**.

## Prerequisites

- **pnpm** at the repository root (workspace install).
- **`OPENAI_API_KEY`** with access to **`gpt-4o-mini`** (or edit `src/index.ts`).
- **`uv`** plus Python deps when running **`pnpm run compliance`**.
- An ASAP HTTP gateway exposing **`GET /asap/capability/describe`** and **`POST /asap/capability/execute`** for your capability ids.

## Quickstart

**1.** Install workspaces from the repo root:

```bash
pnpm install
```

**Purpose:** links `@asap-protocol/client`, `@asap-protocol/openai-agents`, and pulls **`@openai/agents`**.

**2.** Start an ASAP gateway reachable at **`127.0.0.1:8080`** (same convention as **`apps/example-mastra`** — often your Python transport demo).

**3.** Configure and run:

```bash
cp apps/example-openai-agents/.env.example apps/example-openai-agents/.env
# Fill OPENAI_API_KEY (and optionally ASAP_PROVIDER_URL / ASAP_CAPABILITIES).

pnpm --filter example-openai-agents start
```

**Purpose:** prints assistant output after the model resolves capability tools against your gateway.

### Alternative PetStore-backed gateway

PetStore integrations live under **`examples/openapi_petstore/`**. Point **`ASAP_PROVIDER_URL`** at whichever HTTPS gateway fronts those capabilities.

### Custom prompt (optional)

```bash
pnpm --filter example-openai-agents exec tsx src/index.ts Ask the ASAP provider to echo "ping".
```

## Compliance

```bash
pnpm --filter example-openai-agents run compliance
```

**Purpose:** runs **`asap compliance-check --exit-on-fail --url …`** from the repo root against **`ASAP_PROVIDER_URL`**.
