# Mastra · ASAP example (`example-mastra`)

Minimal **Next.js 16 (App Router)** app that chats through a Mastra **`Agent`** with ASAP capability tools from **`@asap-protocol/mastra`**, streamed to the browser with the **Vercel AI SDK** (`createUIMessageStreamResponse`).

## Prerequisites

- **Node 20** (same major as CI) or newer — `package.json` still permits **≥ 18**, but this example is exercised on Node **20**.
- **pnpm** at the monorepo root.
- **`uv`** plus this repository’s Python deps (Compliance Harness CLI).
- A reachable **ASAP gateway** exposing your capabilities (`POST /asap/agent/register`, tool execution endpoints, **HTTPS** recommended for real tokens).
- An **OpenAI API key** (used by **`@ai-sdk/openai`** for the Mastra model).

## Quickstart

**1.** From the repository root, install JavaScript workspaces (includes **`example-mastra`**, **`@asap-protocol/client`**, **`@asap-protocol/mastra`**):

```bash
pnpm install
```

**Purpose:** links workspace packages and pulls Next.js/Mastra/OpenAI deps.

**2.** Start a **Compliance Harness–clean** ASAP HTTP gateway reachable from both the browser (`NEXT_PUBLIC_*`) and this workstation (`pnpm run compliance`).

Most teams iterate with a local ASAP transport app on **`127.0.0.1:8080`**.

**3.** Configure and run Next:

```bash
cp apps/example-mastra/.env.example apps/example-mastra/.env.local
# Set OPENAI_API_KEY, NEXT_PUBLIC_APP_ORIGIN, ASAP_PROVIDER_ALLOWLIST, and align provider URLs.

pnpm --filter example-mastra dev
```

Open **`http://localhost:3000`**, click **Connect agent**, send a prompt that invokes a capability exposed on the gateway.

**Purpose:** runs the demo shell and wires **`/api/chat`** to Mastra + ASAP tools (with origin, body size, provider allowlist, and rate limits — see `.env.example`).

### PetStore-backed URL (alternate)

PetStore integrations are scripted under **`examples/openapi_petstore/`** (`uv run python examples/openapi_petstore/main.py`).

- Expose an HTTP ASAP gateway separately if you prefer that topology.
- Copy its base URL into `NEXT_PUBLIC_ASAP_PROVIDER_URL` and `NEXT_PUBLIC_ASAP_CAPABILITIES`.

### Port collision with `example-nextjs`

Both examples default to **port 3000**. Run one of them on another port, for example:

```bash
pnpm --filter example-mastra dev -- --port 3001
```

**Purpose:** avoids `EADDRINUSE` when both dev servers run on the same machine.

## Compliance

With **`uv`** installed and **`ASAP_PROVIDER_URL`** set (**HTTPS** recommended for staged endpoints):

```bash
pnpm --filter example-mastra run compliance
```

**Purpose:** invokes `asap compliance-check --exit-on-fail --url …` via `tsx scripts/compliance.ts` against the gateway you configured — same harness as **`docs/guides/compliance-testing.md`**.
