# Mastra · ASAP example (`example-mastra`)

Minimal **Next.js 16 (App Router)** app that chats through a Mastra **`Agent`** with ASAP capability tools from **`@asap-protocol/mastra`**, streamed to the browser with the **Vercel AI SDK** (`createUIMessageStreamResponse`).

## Prerequisites

- Node **≥ 18** and **pnpm** (monorepo root).
- **`uv`** plus this repository's Python deps (Compliance Harness CLI).
- A reachable **ASAP gateway** exposing your capabilities (`POST /asap/agent/register`, tool execution endpoints, HTTPS recommended for real tokens).
- An **OpenAI API key** (used by **`@ai-sdk/openai`** for the Mastra model).

Default integration target order (from the sprint): run **`apps/example-agent`** locally, otherwise any compliant ASAP URL including a PetStore-backed gateway you operate.

## Quickstart

**1.** From the repository root, install JavaScript workspaces (includes **`example-mastra`**, **`@asap-protocol/client`**, **`@asap-protocol/mastra`**):

```bash
pnpm install
```

**Purpose:** links workspace packages and pulls Next.js/Mastra/OpenAI deps.

**2.** Start a **Compliance Harness–clean** ASAP HTTP gateway reachable from both the browser (`NEXT_PUBLIC_*`) and this workstation (`pnpm run compliance`). Most teams iterate with a local ASAP transport app on **`127.0.0.1:8080`**; align `NEXT_PUBLIC_ASAP_PROVIDER_URL` with whatever port/host you expose. For OpenAPI-derived stacks, **`examples/openapi_petstore/`** documents generating a runnable ASAP surface from PetStore-shaped specs.

**3.** Configure and run Next:

```bash
cp apps/example-mastra/.env.example apps/example-mastra/.env.local
# Set OPENAI_API_KEY and ASAP_PROVIDER_URL (for compliance) plus NEXT_PUBLIC_ASAP_PROVIDER_URL to match.

pnpm --filter example-mastra dev
```

Open **`http://localhost:3000`**, click **Connect agent**, send a prompt that invokes a capability exposed on the gateway.

**Purpose:** runs the demo shell and wires **`/api/chat`** to Mastra + ASAP tools.

### PetStore-backed URL (alternate)

PetStore integrations are scripted under **`examples/openapi_petstore/`** (`uv run python examples/openapi_petstore/main.py`); expose an HTTP ASAP gateway separately if you prefer that topology, then copy its base URL into `NEXT_PUBLIC_ASAP_PROVIDER_URL` and `NEXT_PUBLIC_ASAP_CAPABILITIES`.

## Compliance (LAB1-004)

With **`uv`** installed and **`ASAP_PROVIDER_URL`** set (HTTPS recommended for staged endpoints):

```bash
pnpm --filter example-mastra run compliance
```

**Purpose:** invokes `asap compliance-check --exit-on-fail --url …` via `tsx scripts/compliance.ts` against the gateway you configured — same harness as **`docs/guides/compliance-testing.md`**.
