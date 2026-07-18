# TypeScript consumer starter

Thin **Node CLI** smoke for [`@asap-protocol/client`](../../../packages/typescript/client/). It proves Host/Agent identity offline (same APIs as the Next demo) without scaffolding a second web app.

The full browser demo stays at [`apps/example-nextjs/`](../../../apps/example-nextjs/). SDK reference: [`docs/sdks/typescript.md`](../../../docs/sdks/typescript.md).

## Prerequisites

- Node.js **≥ 18**
- **pnpm** at the repository root (this starter is a workspace package)
- Built client package (`packages/typescript/client` → `dist/`)

## Smoke (offline, default)

From the **repository root** (headless, ≤60s, no API keys, no live gateway):

```bash
pnpm install
pnpm --filter @asap-protocol/client run build
pnpm --filter @asap-protocol/starter-typescript-consumer run smoke
```

Installs workspace deps (required on a fresh clone), builds `@asap-protocol/client`, then runs the identity smoke via the starter package boundary. Expect `typescript-consumer smoke: PASS`.

## Optional live path

Set `ASAP_PROVIDER_URL` to a provider base URL to also call `discoverProvider` and `listCapabilities`. See [`.env.example`](./.env.example).

```bash
pnpm install
pnpm --filter @asap-protocol/client run build
ASAP_PROVIDER_URL=https://provider.example.com \
  pnpm --filter @asap-protocol/starter-typescript-consumer run smoke
```

**HTTPS is required** for non-loopback hosts on both `ASAP_PROVIDER_URL` and the discovered `manifest.endpoints.asap`. Plain `http://` is allowed only for loopback (`127.0.0.1`, `localhost`, `::1`).

## Storage note

This CLI uses **`MemoryStorage`** (ephemeral). The Next.js demo uses **`LocalStorage`** so identity survives page reloads. For durable Node/CLI storage, see `FileStorage` / `KeychainStorage` under `@asap-protocol/client/storage-node` in the SDK docs.

## Dependency

`package.json` pins `@asap-protocol/client` via `workspace:*` (member of the root pnpm workspace). `smoke.mjs` imports the client through the package boundary (not a direct `dist/` path).
