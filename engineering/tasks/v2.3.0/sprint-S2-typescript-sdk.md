# Sprint S2: TypeScript Client SDK

**PRD**: [v2.3 §4.2](../../../product/prd/prd-v2.3-scale.md) — TS-001..011 (P0)
**Branch**: `feat/typescript-sdk`
**PR Scope**: Official `@asap-protocol/client` npm package with Vercel AI SDK / OpenAI / Anthropic adapters, streaming, type-safe envelopes.
**Depends on**: v2.2 transport (Host/Agent JWT, capabilities, SSE, error taxonomy, version negotiation)

## Relevant Files

### New Files
- `packages/typescript/client/` — new workspace package
  - `package.json` — name `@asap-protocol/client`, dual ESM/CJS via `tshy`; runtime deps `jose`, `ulid`, `@noble/ed25519`; dev `ai`, `zod`, Vitest; optional peers `ai`, `zod`, `keytar`
  - `tsconfig.json` — strict `ES2022`; omits `verbatimModuleSyntax` (incompatible with tshy dual ESM/CJS)
  - `tsconfig.build.json` — emit config for `tshy` (`project` in `package.json`)
  - `vitest.config.ts` — Vitest; `passWithNoTests` avoids empty-suite flakes during incremental work
  - `.npmrc` — `access=public` for scoped package publish
  - `src/index.ts` — public API surface
  - `src/identity.ts` — `createHost`, `createAgent`, `resumeHost`, `resumeAgent`, EdDSA JWTs; delegates keygen to `ed25519-keypair.ts`
  - `src/ed25519-keypair.ts` — Web Crypto `generateKey` with `@noble/ed25519` `keygenAsync` fallback + probe cache (tests reset via `resetEd25519KeygenProbeForTests`)
  - `src/discovery.ts` — `listProviders`, `searchProviders`, `discoverProvider`
  - `src/capabilities.ts` — `listCapabilities`, `describeCapability`, `executeCapability`
  - `src/connection.ts` — `connectAgent`, `disconnectAgent`, `agentStatus`, `reactivateAgent`, `requestCapability`
  - `src/transport.ts` — `callWithRecoverableRetry` (recoverable / remote-recoverable + `retryAfterMs`); future: `fetch` JSON-RPC client, batch, version negotiation
  - `src/streaming.ts` — `createAsapStreamClient`, SSE over `fetch` + `ReadableStream`
  - `src/errors.ts` — RPC taxonomy, `remoteRpcErrorFromJson`, remote/fatal error classes
  - `src/storage-local.ts` — browser-safe `Storage`, `MemoryStorage`, `LocalStorage`
  - `src/storage-file.ts` — Node `FileStorage` (`node:fs`)
  - `src/storage-keychain.ts` — optional `keytar` `KeychainStorage`
  - `src/storage-node.ts` — subpath `@asap-protocol/client/storage-node` re-exporting Node/desktop backends (avoids bundling `fs`/`keytar` in browser apps)
  - `keytar.d.ts` — ambient module types for optional `keytar` peer
  - `src/types/envelope.ts` — `Envelope<T>`, `EnvelopeFor<K>`, payload types, `narrowEnvelope`
  - `src/adapters/shared.ts` — `AsapExecuteClient`, `AsapCapabilityList`, `capabilityToolKey`, `jsonSchemaForCapabilityInput`
  - `src/adapters/vercel-ai.ts` — `asapToolsForVercel(client)` (`ai` `tool` + `executeCapability`)
  - `src/adapters/openai.ts` — `asapToolsForOpenAI(source)` → OpenAI function tools + JSON Schema
  - `src/adapters/anthropic.ts` — `asapToolsForAnthropic(source)` → Anthropic `input_schema` tools
- `packages/typescript/client/test/` — Vitest tests (task 1.2: five failing TDD specs)
  - `identity.test.ts`, `ed25519-fallback.test.ts`, `discovery.test.ts`, `capabilities.test.ts`, `connection.test.ts`, `envelope.test.ts`, `test-d/envelope.test-d.ts` (tsd), `streaming.test.ts`, `errors-rpc.test.ts`, `transport-retry.test.ts`, `storage-contract.test.ts`, `adapters-vercel-ai.test.ts`, `adapters-openai.test.ts`, `adapters-anthropic.test.ts`
- `apps/example-nextjs/` — Reference Next.js 16 App Router app (`ExampleHome`, `AsapDemo`, `/api/chat`) using workspace `@asap-protocol/client`, LocalStorage identity + `connectAgent`, Vercel AI SDK chat with ASAP tools; `.env.example` for provider URL / capabilities / `OPENAI_API_KEY`

### Modified Files
- `package.json` (repo root) — `scripts.test` / `typecheck` / `lint` (SDK + example-nextjs)
- `.github/workflows/typescript-sdk.yml` — CI: ESLint, typecheck, Vitest+coverage, agadoo treeshake for `packages/typescript/**`
- `packages/typescript/client/package.json` — optional peers `ai`, `zod`, `keytar`; `tshy` subpath exports `./adapters/*`
- `.gitignore` — ignore `.tshy/` (tshy-generated tsconfig fragments)
- `apps/web/package.json` — Optionally consume `@asap-protocol/client` workspace ref
- `docs/sdks/typescript.md` — TS SDK guide (install, identity, capabilities, streaming, adapters, storage, errors); linked from root README and MkDocs nav
- `README.md` — Documentation section: link to TypeScript client SDK guide
- `mkdocs.yml` — Nav entry `SDKs` → `sdks/typescript.md`

## Tasks

### 1.0 Workspace Setup (TDD-first)

- [x] 1.1 Create `packages/typescript/client` workspace
  - **What**: `package.json` (ESM+CJS via `tshy`), `tsconfig.json` (strict, ES2022), Vitest config, `.npmrc` for publish
  - **Verify**: `pnpm install` succeeds; `pnpm --filter @asap-protocol/client test` runs (empty)

- [x] 1.2 Write failing tests (TDD)
  - **What**: One representative test per public API: identity creation, capability execution, streaming consumption, error retry, adapter registration
  - **Verify**: All red

### 2.0 Identity & Crypto (TS-001)

- [x] 2.1 `createHost`, `createAgent` with Web Crypto Ed25519
  - **File**: `src/identity.ts`
  - **What**: `await createHost({storage})` generates Ed25519 keypair, persists via storage. `await createAgent(host, {mode})` generates agent keypair under host. Sign Host JWT and Agent JWT with `EdDSA` algorithm.
  - **Verify**: JWT verification round-trip via `jose` package

- [x] 2.2 Web Crypto fallback for non-supporting runtimes
  - **What**: Detect `crypto.subtle.generateKey({name: "Ed25519"})` support; fallback to `@noble/ed25519` for Node <19 / older browsers
  - **Verify**: Both code paths covered by tests with feature-flag mock

### 3.0 Discovery, Capabilities, Connection (TS-002..005)

- [x] 3.1 Discovery functions
  - **File**: `src/discovery.ts`
  - **What**: `listProviders(registry)`, `searchProviders(intent)`, `discoverProvider(url)` — fetch `/.well-known/asap/manifest.json`
  - **Verify**: Mock fetch tests + integration test against test server

- [x] 3.2 Capability functions
  - **File**: `src/capabilities.ts`
  - **What**: `listCapabilities(provider)`, `describeCapability(provider, name)`, `executeCapability(provider, name, args)` — gateway `POST /asap/capability/execute` with Agent JWT
  - **Verify**: Constraint violations return `RecoverableError` with `violations[]`

- [x] 3.3 Connection lifecycle
  - **File**: `src/connection.ts`
  - **What**: `connectAgent(provider, capabilities, mode)` runs registration + approval flow; `disconnectAgent`; `agentStatus`; `reactivateAgent`; `requestCapability` (TS-005, ESC-004)
  - **Verify**: Full lifecycle integration test against test ASAP server

### 4.0 Streaming & Error Handling (TS-010, TS-011)

- [x] 4.1 Type-safe envelopes
  - **File**: `src/types/envelope.ts`
  - **What**: `Envelope<TPayload>` generics covering `TaskRequest`, `TaskResponse`, `TaskStream`, etc.
  - **Verify**: Type-level tests via `tsd`

- [x] 4.2 Streaming consumer
  - **File**: `src/streaming.ts`
  - **What**: `client.stream(envelope)` returns `AsyncIterable<Envelope<TaskStream>>`. Use `fetch` with `ReadableStream` (browser/Node 18+). Parse SSE events into typed envelopes. Terminate on `final: true`.
  - **Verify**: Stream emits expected chunks; cancellation works

- [x] 4.3 Error taxonomy port
  - **File**: `src/errors.ts`
  - **What**: TS classes `RecoverableError`/`FatalError`/`RemoteFatalRPCError`/`RemoteRecoverableRPCError`. Map JSON-RPC code (-32000..-32059) to category. Auto-retry on `RecoverableError` with `retry_after_ms`.
  - **Verify**: Three retry scenarios

### 5.0 Storage Backends (TS-009)

- [x] 5.1 Pluggable `Storage` interface
  - **File**: `src/storage-local.ts`, `src/storage-file.ts`, `src/storage-keychain.ts`, `src/storage-node.ts`
  - **What**: `interface Storage { get(key); set(key, value); delete(key); }`. Implementations: `MemoryStorage`, `FileStorage` (Node), `LocalStorage` (browser). `KeychainStorage` via optional `keytar` peer dep.
  - **Verify**: Each implementation passes the same fixture suite

### 6.0 Adapters (TS-006, TS-007, TS-008)

- [x] 6.1 Vercel AI SDK adapter (TS-006, MUST)
  - **File**: `src/adapters/vercel-ai.ts`
  - **What**: `asapToolsForVercel(client)` returns object compatible with `tools` argument of `streamText`. Each ASAP capability becomes a Vercel AI tool with JSON Schema input + executor.
  - **Verify**: E2E test using `ai` package and a mock LLM

- [x] 6.2 OpenAI SDK adapter (TS-007, SHOULD)
  - **File**: `src/adapters/openai.ts`
  - **What**: `asapToolsForOpenAI(client)` returns array of `ChatCompletionTool` with function definitions
  - **Verify**: Schema produced matches OpenAI tools spec

- [x] 6.3 Anthropic SDK adapter (TS-008, SHOULD)
  - **File**: `src/adapters/anthropic.ts`
  - **What**: `asapToolsForAnthropic(client)` returns array of `Tool` for Messages API
  - **Verify**: Schema matches Anthropic tool-use spec

### 7.0 Reference Next.js App

- [x] 7.1 `apps/example-nextjs`
  - **What**: Minimal Next.js 16 App Router app demonstrating: register host on first load (LocalStorage), connect agent to a sample provider, use Vercel AI SDK with ASAP tools in a chat UI
  - **Verify**: `pnpm --filter example-nextjs dev` works locally; deploys to Vercel preview

### 8.0 Publish Pipeline

- [x] 8.1 npm publish workflow
  - **File**: `.github/workflows/publish-typescript.yml`
  - **What**: Triggered on tag `v2.3.*`. Builds via `tshy`, publishes `@asap-protocol/client` with provenance
  - **Verify**: Dry-run on PR with `--dry-run`

- [x] 8.2 Docs
  - **File**: `docs/sdks/typescript.md`
  - **What**: Installation, identity, capabilities, streaming, adapter usage, storage selection, error handling
  - **Verify**: Cross-link from main README

## Acceptance Criteria

Verification: root `package.json` defines `pnpm test`, `pnpm typecheck`, and `pnpm lint` targeting `@asap-protocol/client` (and `lint` also runs `example-nextjs`). CI job `.github/workflows/typescript-sdk.yml` runs on changes under `packages/typescript/**`.

| Criterion | Met? | Evidence |
|-----------|------|----------|
| `pnpm test` green (Vitest + coverage) | Yes | `vitest run --coverage` with `@vitest/coverage-v8`; thresholds: **lines ≥90%**, **functions ≥90%**, statements ≥87%, branches ≥70% (see `vitest.config.ts`). |
| `pnpm typecheck` clean | Yes | Strict `tsc --noEmit`. |
| `pnpm lint` clean | Yes | ESLint flat config in `packages/typescript/client/eslint.config.js`; root `pnpm lint` runs SDK + `example-nextjs`. |
| Bundle core <50KB gzipped (excl. adapters) | Yes | Core ESM bundle gzip ≈ **14KB** (same methodology as prior audit). |
| Tree-shakeable adapters (`agadoo`) | Yes | `pnpm --filter @asap-protocol/client run check:treeshake` runs **agadoo** on main + adapter entrypoints after `tshy` build. |
| Reference Next.js app on **Vercel preview** | Pending ops | Deploy `apps/example-nextjs` from maintainer account / project settings. |
| **`@asap-protocol/client@2.3.0` on npm** | Pending release | Tag `v2.3.*` + `.github/workflows/publish-typescript.yml`; bump package version at release time (source may stay `0.0.0` until publish). |

Checklist:

- [x] `pnpm test` green (Vitest + coverage gates)
- [x] `pnpm typecheck` clean (strict TS)
- [x] `pnpm lint` clean (SDK + example app)
- [x] Bundle size: SDK core <50KB gzipped (excluding adapters)
- [x] Tree-shakeable adapters verified (`agadoo` script + CI)
- [ ] Reference Next.js app deployed to Vercel preview *(maintainer)*
- [ ] Package published to npm `@asap-protocol/client@2.3.0` *(release/tag)*

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Web Crypto Ed25519 not supported on older Node/browsers | `@noble/ed25519` fallback with feature detection; document minimum runtime versions |
| `keytar` is a native dep that fails in serverless | Make `KeychainStorage` opt-in; default to `LocalStorage`/`FileStorage` |
| Vercel AI SDK API changes between major versions | Pin to current major; CI matrix entry; document supported version range |
| Adapter bundle bloat | Tree-shake via per-adapter entry points (`@asap-protocol/client/adapters/vercel-ai`) |
