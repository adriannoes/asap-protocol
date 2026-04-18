# Sprint S2: TypeScript Client SDK

**PRD**: [v2.3 §4.2](../../../product-specs/prd/prd-v2.3-scale.md) — TS-001..011 (P0)
**Branch**: `feat/typescript-sdk`
**PR Scope**: Official `@asap-protocol/client` npm package with Vercel AI SDK / OpenAI / Anthropic adapters, streaming, type-safe envelopes.
**Depends on**: v2.2 transport (Host/Agent JWT, capabilities, SSE, error taxonomy, version negotiation)

## Relevant Files

### New Files
- `packages/typescript/client/` — new workspace package
  - `package.json` — name `@asap-protocol/client`, dual ESM/CJS via `tshy`
  - `tsconfig.json`
  - `src/index.ts` — public API surface
  - `src/identity.ts` — `createHost`, `createAgent`, JWT helpers (Web Crypto + `@noble/ed25519` fallback)
  - `src/discovery.ts` — `listProviders`, `searchProviders`, `discoverProvider`
  - `src/capabilities.ts` — `listCapabilities`, `describeCapability`, `executeCapability`
  - `src/connection.ts` — `connectAgent`, `disconnectAgent`, `agentStatus`, `reactivateAgent`, `requestCapability`
  - `src/transport.ts` — `fetch`-based JSON-RPC client, batch, version negotiation, retry-on-RecoverableError
  - `src/streaming.ts` — `EventSource`/`ReadableStream` SSE consumer
  - `src/storage.ts` — `MemoryStorage`, `FileStorage`, `LocalStorage`, `KeychainStorage` (Keytar; optional)
  - `src/errors.ts` — TS port of `RecoverableError`/`FatalError` with code constants
  - `src/types/envelope.ts` — Type-safe `Envelope<T>` generics
  - `src/adapters/vercel-ai.ts` — `asapToolsForVercel(client)`
  - `src/adapters/openai.ts` — `asapToolsForOpenAI(client)`
  - `src/adapters/anthropic.ts` — `asapToolsForAnthropic(client)`
- `packages/typescript/client/test/` — Vitest tests
- `apps/example-nextjs/` — Reference Next.js app using SDK + Vercel AI SDK adapter

### Modified Files
- `pnpm-workspace.yaml` — Register `packages/typescript/*`
- `apps/web/package.json` — Optionally consume `@asap-protocol/client` workspace ref
- `docs/sdks/typescript.md` — TS SDK guide

## Tasks

### 1.0 Workspace Setup (TDD-first)

- [ ] 1.1 Create `packages/typescript/client` workspace
  - **What**: `package.json` (ESM+CJS via `tshy`), `tsconfig.json` (strict, ES2022), Vitest config, `.npmrc` for publish
  - **Verify**: `pnpm install` succeeds; `pnpm --filter @asap-protocol/client test` runs (empty)

- [ ] 1.2 Write failing tests (TDD)
  - **What**: One representative test per public API: identity creation, capability execution, streaming consumption, error retry, adapter registration
  - **Verify**: All red

### 2.0 Identity & Crypto (TS-001)

- [ ] 2.1 `createHost`, `createAgent` with Web Crypto Ed25519
  - **File**: `src/identity.ts`
  - **What**: `await createHost({storage})` generates Ed25519 keypair, persists via storage. `await createAgent(host, {mode})` generates agent keypair under host. Sign Host JWT and Agent JWT with `EdDSA` algorithm.
  - **Verify**: JWT verification round-trip via `jose` package

- [ ] 2.2 Web Crypto fallback for non-supporting runtimes
  - **What**: Detect `crypto.subtle.generateKey({name: "Ed25519"})` support; fallback to `@noble/ed25519` for Node <19 / older browsers
  - **Verify**: Both code paths covered by tests with feature-flag mock

### 3.0 Discovery, Capabilities, Connection (TS-002..005)

- [ ] 3.1 Discovery functions
  - **File**: `src/discovery.ts`
  - **What**: `listProviders(registry)`, `searchProviders(intent)`, `discoverProvider(url)` — fetch `/.well-known/asap/manifest.json`
  - **Verify**: Mock fetch tests + integration test against test server

- [ ] 3.2 Capability functions
  - **File**: `src/capabilities.ts`
  - **What**: `listCapabilities(provider)`, `describeCapability(provider, name)`, `executeCapability(provider, name, args)` — gateway `POST /asap/capability/execute` with Agent JWT
  - **Verify**: Constraint violations return `RecoverableError` with `violations[]`

- [ ] 3.3 Connection lifecycle
  - **File**: `src/connection.ts`
  - **What**: `connectAgent(provider, capabilities, mode)` runs registration + approval flow; `disconnectAgent`; `agentStatus`; `reactivateAgent`; `requestCapability` (TS-005, ESC-004)
  - **Verify**: Full lifecycle integration test against test ASAP server

### 4.0 Streaming & Error Handling (TS-010, TS-011)

- [ ] 4.1 Type-safe envelopes
  - **File**: `src/types/envelope.ts`
  - **What**: `Envelope<TPayload>` generics covering `TaskRequest`, `TaskResponse`, `TaskStream`, etc.
  - **Verify**: Type-level tests via `tsd`

- [ ] 4.2 Streaming consumer
  - **File**: `src/streaming.ts`
  - **What**: `client.stream(envelope)` returns `AsyncIterable<Envelope<TaskStream>>`. Use `fetch` with `ReadableStream` (browser/Node 18+). Parse SSE events into typed envelopes. Terminate on `final: true`.
  - **Verify**: Stream emits expected chunks; cancellation works

- [ ] 4.3 Error taxonomy port
  - **File**: `src/errors.ts`
  - **What**: TS classes `RecoverableError`/`FatalError`/`RemoteFatalRPCError`/`RemoteRecoverableRPCError`. Map JSON-RPC code (-32000..-32059) to category. Auto-retry on `RecoverableError` with `retry_after_ms`.
  - **Verify**: Three retry scenarios

### 5.0 Storage Backends (TS-009)

- [ ] 5.1 Pluggable `Storage` interface
  - **File**: `src/storage.ts`
  - **What**: `interface Storage { get(key); set(key, value); delete(key); }`. Implementations: `MemoryStorage`, `FileStorage` (Node), `LocalStorage` (browser). `KeychainStorage` via optional `keytar` peer dep.
  - **Verify**: Each implementation passes the same fixture suite

### 6.0 Adapters (TS-006, TS-007, TS-008)

- [ ] 6.1 Vercel AI SDK adapter (TS-006, MUST)
  - **File**: `src/adapters/vercel-ai.ts`
  - **What**: `asapToolsForVercel(client)` returns object compatible with `tools` argument of `streamText`. Each ASAP capability becomes a Vercel AI tool with JSON Schema input + executor.
  - **Verify**: E2E test using `ai` package and a mock LLM

- [ ] 6.2 OpenAI SDK adapter (TS-007, SHOULD)
  - **File**: `src/adapters/openai.ts`
  - **What**: `asapToolsForOpenAI(client)` returns array of `ChatCompletionTool` with function definitions
  - **Verify**: Schema produced matches OpenAI tools spec

- [ ] 6.3 Anthropic SDK adapter (TS-008, SHOULD)
  - **File**: `src/adapters/anthropic.ts`
  - **What**: `asapToolsForAnthropic(client)` returns array of `Tool` for Messages API
  - **Verify**: Schema matches Anthropic tool-use spec

### 7.0 Reference Next.js App

- [ ] 7.1 `apps/example-nextjs`
  - **What**: Minimal Next.js 16 App Router app demonstrating: register host on first load (LocalStorage), connect agent to a sample provider, use Vercel AI SDK with ASAP tools in a chat UI
  - **Verify**: `pnpm --filter example-nextjs dev` works locally; deploys to Vercel preview

### 8.0 Publish Pipeline

- [ ] 8.1 npm publish workflow
  - **File**: `.github/workflows/publish-typescript.yml`
  - **What**: Triggered on tag `v2.3.*`. Builds via `tshy`, publishes `@asap-protocol/client` with provenance
  - **Verify**: Dry-run on PR with `--dry-run`

- [ ] 8.2 Docs
  - **File**: `docs/sdks/typescript.md`
  - **What**: Installation, identity, capabilities, streaming, adapter usage, storage selection, error handling
  - **Verify**: Cross-link from main README

## Acceptance Criteria

- [ ] `pnpm test` green (Vitest, ≥90% coverage)
- [ ] `pnpm typecheck` clean (strict TS)
- [ ] `pnpm lint` clean
- [ ] Bundle size: SDK core <50KB gzipped (excluding adapters)
- [ ] Tree-shakeable adapters (verified via `agadoo` or similar)
- [ ] Reference Next.js app deployed to Vercel preview
- [ ] Package published to npm under `@asap-protocol/client@2.3.0`

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Web Crypto Ed25519 not supported on older Node/browsers | `@noble/ed25519` fallback with feature detection; document minimum runtime versions |
| `keytar` is a native dep that fails in serverless | Make `KeychainStorage` opt-in; default to `LocalStorage`/`FileStorage` |
| Vercel AI SDK API changes between major versions | Pin to current major; CI matrix entry; document supported version range |
| Adapter bundle bloat | Tree-shake via per-adapter entry points (`@asap-protocol/client/adapters/vercel-ai`) |
