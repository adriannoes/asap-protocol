# TypeScript client SDK (`@asap-protocol/client`)

Official browser- and Node-compatible client for ASAP **discovery**, **capabilities**, **Host/Agent JWT identity**, **SSE streaming**, and **LLM adapter shims** (Vercel AI SDK, OpenAI, Anthropic).

**Requirements:** Node.js **≥ 18** (Web Crypto `Ed25519` where available; [`@noble/ed25519`](https://www.npmjs.com/package/@noble/ed25519) fallback in older runtimes — see package tests).

## Installation

From npm (after release):

```bash
npm install @asap-protocol/client
```

In this monorepo, depend on the workspace package:

```json
{
  "dependencies": {
    "@asap-protocol/client": "workspace:*"
  }
}
```

Optional peer dependencies (install only what you use):

| Peer | Purpose |
|------|---------|
| `ai` | Vercel AI SDK adapter (`@asap-protocol/client/adapters/vercel-ai`) |
| `zod` | Required by the Vercel adapter’s schema helpers |
| `keytar` | macOS/Windows/Linux keychain storage (Node/desktop only) |

Tree-shake adapters by importing **subpaths** (see [Adapters](#adapters)) so unused providers stay out of your bundle.

## Identity and storage

Hosts and agents use **Ed25519** keys and short-lived **JWTs** (`jose`). Keys must be persisted with a [`Storage`](https://github.com/asap-protocol/asap-protocol/blob/main/packages/typescript/client/src/storage-local.ts)-compatible backend.

```ts
import {
  createHost,
  createAgent,
  MemoryStorage,
  LocalStorage,
} from "@asap-protocol/client";

const storage = typeof localStorage !== "undefined"
  ? new LocalStorage("asap:")
  : new MemoryStorage();

const host = await createHost({ storage });
const agent = await createAgent(host, { mode: "delegated" });
// Use host.agentJwt / agent metadata as required by your gateway.
```

- **`createHost` / `createAgent`** — generate keys, persist, issue Host and Agent JWTs.
- **`resumeHost` / `resumeAgent`** — reload identity from storage after restart.

### Storage selection

| Backend | Import | When to use |
|---------|--------|-------------|
| In-memory | `MemoryStorage` | Tests, ephemeral demos |
| Browser `localStorage` | `LocalStorage` | Default for web apps |
| Node filesystem | `FileStorage` from `@asap-protocol/client/storage-node` | Servers, CLI |
| OS keychain | `KeychainStorage` from `@asap-protocol/client/storage-node` | Desktop apps; requires optional `keytar` |

Always import `@asap-protocol/client/storage-node` **only in Node/desktop** builds so bundlers do not pull `node:fs` or native addons into browser chunks.

## Discovery and capabilities

```ts
import {
  discoverProvider,
  listCapabilities,
  describeCapability,
  executeCapability,
} from "@asap-protocol/client";

const manifest = await discoverProvider("https://agent.example.com");
const provider = new URL(manifest.endpoints.asap);

const { capabilities } = await listCapabilities(provider, { agentJwt, fetch });
const detail = await describeCapability(provider, "my.skill", { agentJwt });
const result = await executeCapability(provider, "my.skill", { foo: "bar" }, {
  agentJwt,
});
```

Use [`connectAgent`](https://github.com/asap-protocol/asap-protocol/blob/main/packages/typescript/client/src/connection.ts) for registration, approval, disconnect, and capability requests against a live provider.

## Streaming (SSE)

```ts
import { createAsapStreamClient } from "@asap-protocol/client";

const client = createAsapStreamClient({
  baseUrl: provider,
  agentJwt,
  fetch,
});

// Build your task envelope (e.g. TaskRequest) then:
for await (const chunk of client.stream(taskEnvelope)) {
  // Typed Envelope<TaskStream> until payload.final === true
}
```

Streaming uses `fetch` + `ReadableStream` and parses **SSE** into typed **`Envelope<TaskStream>`** payloads. Lower-level access: **`streamTaskStreamEnvelopes`** when you already have a full `/asap/stream` URL.

## Adapters

Import from **subpaths** to keep bundles small:

### Vercel AI SDK (`ai`)

```ts
import { asapToolsForVercel } from "@asap-protocol/client/adapters/vercel-ai";
import { streamText } from "ai";

const tools = asapToolsForVercel({
  provider,
  capabilities: ["echo"],
  agentJwt,
  fetch,
});

await streamText({ model, tools, prompt });
```

Peer deps: **`ai`**, **`zod`** (supported majors per `package.json`).

### OpenAI (`ChatCompletionTool`)

```ts
import { asapToolsForOpenAI } from "@asap-protocol/client/adapters/openai";

const tools = asapToolsForOpenAI({
  provider,
  capabilities,
  agentJwt,
  fetch,
});
```

### Anthropic (Messages API tools)

```ts
import { asapToolsForAnthropic } from "@asap-protocol/client/adapters/anthropic";

const tools = asapToolsForAnthropic({
  provider,
  capabilities,
  agentJwt,
  fetch,
});
```

## Error handling and retries

The SDK maps JSON-RPC errors into typed classes (aligned with [ADR-012](../adr/ADR-012-error-taxonomy.md) concepts):

- **`RecoverableError`** / **`RemoteRecoverableRPCError`** — may include `retryAfterMs`; safe to retry with backoff.
- **`FatalError`** / **`RemoteFatalRPCError`** — do not blindly retry.

Use **`callWithRecoverableRetry`** for call sites that should automatically retry recoverable failures using `retry_after_ms` when present (Python client parity). Optionally pass **`fallbackBackoffMs`** so recoverable errors **without** `retryAfterMs` still retry using bounded exponential backoff (capped at 60 seconds per wait).

```ts
import { callWithRecoverableRetry } from "@asap-protocol/client";

await callWithRecoverableRetry(() => doRpcCall(), { maxRetries: 3 });
await callWithRecoverableRetry(() => doRpcCall(), { fallbackBackoffMs: 500 });
```

For wire-level JSON helpers, see **`remoteRpcErrorFromJson`** and related exports in [`errors.ts`](https://github.com/asap-protocol/asap-protocol/blob/main/packages/typescript/client/src/errors.ts).

## Security

- JS heaps cannot reliably wipe key material; the SDK clears the JWK `d` field after `importKey` as minor hardening.
- If you use `fallbackBackoffMs`, size retries to your gateway limits.

## Reference app

The **[`apps/example-nextjs`](https://github.com/asap-protocol/asap-protocol/tree/main/apps/example-nextjs)** App Router demo registers a host in **`LocalStorage`**, connects an agent, and wires **`asapToolsForVercel`** into a chat UI. Copy patterns from `.env.example` for provider URL and API keys.

## See also

- [TypeScript consumer starter](../../examples/starters/typescript-consumer/) — thin Node identity smoke (`examples/starters/typescript-consumer/`)
- [Transport overview](../transport.md) — HTTP/SSE endpoints and versioning
- [Error handling (Python-centric)](../error-handling.md) — taxonomy and JSON-RPC mapping
- [Vercel AI SDK (Python gateway)](../guides/vercel-ai-sdk.md) — complementary server-side tools router
- [Build for agents](../guides/build-for-agents.md) — Dist Loop onboarding guide
