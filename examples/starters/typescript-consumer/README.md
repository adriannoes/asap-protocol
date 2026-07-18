# TypeScript consumer starter

Thin **Node CLI** smoke for [`@asap-protocol/client`](../../../packages/typescript/client/). It proves Host/Agent identity offline (same APIs as the Next demo) without scaffolding a second web app.

The full browser demo stays at [`apps/example-nextjs/`](../../../apps/example-nextjs/). SDK reference: [`docs/sdks/typescript.md`](../../../docs/sdks/typescript.md).

## Prerequisites

- Node.js **≥ 18**
- Built client package (`packages/typescript/client` → `dist/`)

## Smoke (offline, default)

From the **repository root** (headless, ≤60s, no API keys, no live gateway):

```bash
pnpm --filter @asap-protocol/client run build
npm install --prefix examples/starters/typescript-consumer
node examples/starters/typescript-consumer/smoke.mjs
```

Builds `@asap-protocol/client`, installs the starter’s `file:` dependency, then runs the identity smoke. Expect `typescript-consumer smoke: PASS`.

Or from this directory after the client is built:

```bash
npm install && npm run smoke
```

Do **not** use bare `pnpm run smoke` here — this starter lives outside the pnpm workspace (`examples/` is not a workspace package).

## Optional live path

Set `ASAP_PROVIDER_URL` to a provider base URL to also call `discoverProvider` and `listCapabilities`. See [`.env.example`](./.env.example).

```bash
pnpm --filter @asap-protocol/client run build
npm install --prefix examples/starters/typescript-consumer
ASAP_PROVIDER_URL=https://provider.example.com \
  node examples/starters/typescript-consumer/smoke.mjs
```

**HTTPS is required** for non-loopback hosts on both `ASAP_PROVIDER_URL` and the discovered `manifest.endpoints.asap`. Plain `http://` is allowed only for loopback (`127.0.0.1`, `localhost`, `::1`).

## Storage note

This CLI uses **`MemoryStorage`** (ephemeral). The Next.js demo uses **`LocalStorage`** so identity survives page reloads. For durable Node/CLI storage, see `FileStorage` / `KeychainStorage` under `@asap-protocol/client/storage-node` in the SDK docs.

## Dependency

`package.json` pins the monorepo client via a relative `file:` path (`examples/` is outside the pnpm workspace). After `npm install`, `smoke.mjs` imports `@asap-protocol/client` through the package boundary (not a direct `dist/` path).
