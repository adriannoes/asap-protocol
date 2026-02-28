# Sprint E5: OpenClaw Integration

> **Goal**: Integrate ASAP Protocol with OpenClaw framework (Python bridge, Node.js plugin, Registry UX)
> **Prerequisite**: Sprint E2 (MarketClient), Sprint E3 (Framework Integrations pattern)
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` — Optional dep `[openclaw]`
- `src/asap/integrations/openclaw.py` — OpenClawAsapBridge (created)
- `src/asap/integrations/__init__.py` — Lazy export (modified)
- `tests/integrations/test_openclaw.py` — OpenClaw integration tests (created)
- `packages/asap-openclaw-skill/` — Node.js plugin for OpenClaw (created)
- `packages/asap-openclaw-skill/src/index.test.ts` — Node skill unit tests (created)
- `apps/web/src/app/agents/[id]/usage-snippets.tsx` — OpenClaw tab (modified)
- `docs/guides/openclaw-integration.md` — Integration guide (created)

---

## Trigger / Enables / Depends on

**Trigger:** Developer uses OpenClaw agents and wants to invoke ASAP agents; or browses agent detail and sees OpenClaw usage snippet.

**Enables:** OpenClaw agents can invoke ASAP agents via plugin; Python pipelines can combine OpenClawClient with MarketClient.

**Depends on:** Sprint E2 (MarketClient), Sprint E3 (integration patterns).

---

## Acceptance Criteria

- [x] `[openclaw]` optional dependency works (`uv sync --extra openclaw`)
- [x] `OpenClawAsapBridge` or helper enables hybrid pipelines (OpenClaw + ASAP)
- [x] `asap-openclaw-skill` plugin registers `asap_invoke` tool; resolves URN and sends JSON-RPC
- [x] Agent detail page shows OpenClaw usage snippet
- [x] `docs/guides/openclaw-integration.md` documents installation and usage

---

## Task 5.1: Add optional dependency

- [x] **5.1.1** Add `[openclaw]` to pyproject.toml
  - **File**: `pyproject.toml`
  - **What**: `openclaw = ["openclaw-sdk>=2.0"]`
  - **Verify**: `uv sync --extra openclaw` succeeds

---

## Task 5.2: Create OpenClaw integration module

- [x] **5.2.1** Create OpenClawAsapBridge
  - **File**: `src/asap/integrations/openclaw.py`
  - **What**: Bridge using MarketClient; lazy-import openclaw_sdk; handle AgentRevokedException, SignatureVerificationError
- [x] **5.2.2** Add exports to `__init__.py`
- [x] **5.2.3** Write tests for OpenClaw integration

---

## Task 5.3: Create OpenClaw Skill (Node.js plugin)

- [x] **5.3.1** Create plugin structure in `packages/asap-openclaw-skill/`
- [x] **5.3.2** Implement `asap_invoke` tool (resolve URN, JSON-RPC)
- [x] **5.3.3** Document installation and `tools.allow` config

---

## Task 5.4: Registry UX — Usage Snippets

- [x] **5.4.1** Add OpenClaw tab to usage-snippets.tsx

---

## Task 5.5: Documentation

- [x] **5.5.1** Create `docs/guides/openclaw-integration.md`
- [x] **5.5.2** Update CHANGELOG and AGENTS.md

---

## Task 5.6: DX improvements

> **Done in this pass (pre-5.6)**: `is_error_result()` helper, `registry_url` on bridge, "Discover agents" and Troubleshooting in docs, copy-pasteable openclaw.json snippet, skill README registry link and troubleshooting.

- [x] **5.6.1** Node skill: unit tests
  - **File**: `packages/asap-openclaw-skill/package.json`, `packages/asap-openclaw-skill/src/index.test.ts`
  - **What**: Vitest (or Jest) with mocked fetch; tests for fetchRegistry, findEntryByUrn, getHttpEndpoint, invokeAsapAgent, tool execute (success, agent not found, 4xx/5xx)
- [x] **5.6.2** Python: list agents/skills from registry
  - **File**: `src/asap/client/market.py` or `src/asap/integrations/openclaw.py`
  - **What**: Method that calls get_registry(), maps entries to (urn, name, skill_ids); expose as bridge.list_agents()
- [x] **5.6.3** Plugin: env var for timeout
  - **File**: `packages/asap-openclaw-skill/src/index.ts`, README, docs/guides/openclaw-integration.md
  - **What**: ASAP_REQUEST_TIMEOUT_MS; AbortController + signal in fetch for registry and invoke
- [x] **5.6.4** Bridge: distinct error messages
  - **File**: `src/asap/integrations/openclaw.py`
  - **What**: Return specific strings per exception type (Agent revoked, Signature verification failed, Invalid request or URN)
- [x] **5.6.5** Registry UX: Copy button for OpenClaw snippet
  - **File**: `apps/web/src/app/agents/[id]/usage-snippets.tsx`
  - **What**: Copy button that copies snippet to clipboard; optional "Copied!" state
- [x] **5.6.6** Python (optional): AsapBridgeResult type
  - **File**: `src/asap/integrations/openclaw.py`
  - **What**: Success(result=dict) | Error(message=str) or get_result() that raises on error; keep is_error_result()
- [ ] **5.6.7** E2E: bridge + mock/ASAP server (backlog; deferred: requires signed manifest endpoint)
  - **File**: `tests/integrations/` or `tests/e2e/`
  - **What**: Integration test: start ASAP server (or mock), call bridge resolve+run, assert result
- [ ] **5.6.8** Plugin: structured tool result (backlog; deferred: evaluate breaking change)
  - **File**: `packages/asap-openclaw-skill/src/index.ts`
  - **What**: Return { success, result?, error? }; evaluate breaking change for prompts
- [x] **5.6.9** Docs: compatibility note
  - **File**: `docs/guides/openclaw-integration.md`, `packages/asap-openclaw-skill/README.md`
  - **What**: Subsection "Compatibility" with OpenClaw version, Node (>=18), ASAP protocol version

---

## Definition of Done

- [x] `pip install asap-protocol[openclaw]` works
- [x] OpenClaw plugin installable; `asap_invoke` callable by agents
- [x] Usage snippets show OpenClaw integration
- [x] Guide and CHANGELOG updated
