# Sprint E2: Consumer SDK Core

> **Goal**: MarketClient, ResolvedAgent, cache, 429/Bearer, Raw Fetch doc
> **Prerequisite**: Sprint E1 (trust, revocation)
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)
> **Estimated Duration**: 4–5 days

---

## Relevant Files

- `src/asap/client/__init__.py` — Public API
- `src/asap/client/market.py` — MarketClient, ResolvedAgent
- `src/asap/client/cache.py` — Registry cache
- `docs/raw-fetch.md` — Raw Fetch documentation
- `tests/client/test_market.py`, `tests/client/test_cache.py`

---

## Trigger / Enables / Depends on

**Trigger:** Developer calls `MarketClient().resolve(urn)` (Sprint E3 integrations depend on this).

**Enables:** Sprint E3 (Framework Integrations) uses MarketClient; Sprint E5 (PyPI) ships SDK.

**Depends on:** Sprint E1 (trust, revocation); `asap.discovery.registry`, `asap.transport.client.ASAPClient`, `asap.transport.websocket`.

---

## Acceptance Criteria

- [ ] `MarketClient.resolve(urn)` returns ResolvedAgent; fetches registry (cached 5 min), manifest, validates trust, checks revocation
- [ ] `agent.run(payload)` orchestrates HTTP/WebSocket handshake; returns result dict
- [ ] Registry cache TTL configurable via `ASAP_REGISTRY_CACHE_TTL` (default 300)
- [ ] HTTP 429 handled with exponential backoff; honors `Retry-After`
- [ ] Bearer token passthrough via `MarketClient(auth_token=...)` or `agent.run(..., auth_token=...)`
- [ ] DOC-001: Raw Fetch path documented for non-Python consumers

---

## Task 2.1: Create client cache module

- [ ] **2.1.1** Implement registry cache with TTL
  - **File**: `src/asap/client/cache.py` (create new)
  - **What**: Implement registry cache. Read `ASAP_REGISTRY_CACHE_TTL` (default 300). Use `asap.discovery.registry.discover_from_registry` with custom ttl_seconds. Expose `get_registry(registry_url)`, `invalidate()` for tests.
  - **Why**: SDK-003, ADR-25 — registry.json cached 5 min.
  - **Pattern**: Wrap `discover_from_registry`; existing cache in `discovery/registry.py` uses 900s — client-specific config override.
  - **Verify**: `pytest tests/client/test_cache.py` — second call within TTL returns cached; after TTL refetches.

- [ ] **2.1.2** Write tests for cache
  - **File**: `tests/client/test_cache.py` (create new)
  - **What**: Test cache hit within TTL; cache miss after TTL; invalidate clears cache; TTL from env.
  - **Verify**: `pytest tests/client/test_cache.py -v` passes.

---

## Task 2.2: Create MarketClient and ResolvedAgent

- [ ] **2.2.1** Implement MarketClient.resolve flow
  - **File**: `src/asap/client/market.py` (create new)
  - **What**: `MarketClient(registry_url=..., revoked_url=..., auth_token=...)`. `async resolve(urn: str) -> ResolvedAgent`. Flow: (1) get registry from cache, (2) `find_by_id(registry, urn)` — raise if not found, (3) fetch manifest from `entry.endpoints["manifest"]` or `entry.endpoints["http"]` + well-known, (4) parse `SignedManifest.model_validate_json()`, (5) `verify_agent_trust(signed_manifest)`, (6) `await is_revoked(urn)`, (7) if revoked raise `AgentRevokedException`, (8) return `ResolvedAgent(manifest, entry, self)`.
  - **Why**: SDK-001 — resolve URN to ResolvedAgent.
  - **Pattern**: `asap.discovery.registry.find_by_id`; `asap.transport.client.ASAPClient` for manifest fetch.
  - **Verify**: `pytest tests/client/test_market.py -k "resolve"` — resolve returns ResolvedAgent; invalid URN raises; not found raises.

- [ ] **2.2.2** Implement ResolvedAgent.run flow
  - **File**: `src/asap/client/market.py`
  - **What**: `ResolvedAgent` holds `manifest`, `entry`, `client: MarketClient`. `async run(payload: dict, auth_token: str | None = None) -> dict`. Build envelope from payload; use `ASAPClient` (or WebSocket) with `entry.endpoints["http"]` or `entry.endpoints["ws"]`; send; return result.

  - **Why**: SDK-002 — run orchestrates handshake.
  - **Pattern**: `asap.transport.client.ASAPClient.send()`; `asap.models.envelope.Envelope`; payload → TaskRequest or equivalent.
  - **Integration**: Consumed by Sprint E3 (LangChain, CrewAI, MCP).
  - **Verify**: `pytest tests/client/test_market.py -k "run"` — run returns result; mock agent returns expected payload.

- [ ] **2.2.3** Write tests for MarketClient (resolve + run + signature + revoked)
  - **File**: `tests/client/test_market.py` (create new)
  - **What**: Test resolve success; resolve URN not found; resolve invalid signature raises; resolve revoked raises; run success; run with auth_token.
  - **Verify**: `pytest tests/client/test_market.py -v` passes.

---

## Task 2.3: Add HTTP 429 handling with exponential backoff

- [ ] **2.3.1** Retry logic for 429
  - **File**: `src/asap/client/market.py` or `src/asap/client/http_client.py` (create if needed)
  - **What**: Wrap httpx calls with retry: on 429, read `Retry-After` header (or exponential backoff 1s, 2s, 4s), retry up to 3 times. Apply to registry fetch, manifest fetch, run() HTTP.
  - **Why**: ECO-001 — SDK handles rate limits.
  - **Pattern**: `tenacity` or custom loop; honor `Retry-After`.
  - **Verify**: `pytest tests/client/test_market.py -k "429"` — mock 429, assert retries.

- [ ] **2.3.2** Write test for 429 retry
  - **File**: `tests/client/test_market.py`
  - **What**: Mock 429 then 200; assert eventual success. Mock 429 x4; assert raises after retries.
  - **Verify**: Test passes.

---

## Task 2.4: Add Bearer token passthrough

- [ ] **2.4.1** Auth token support
  - **File**: `src/asap/client/market.py`
  - **What**: `MarketClient(auth_token: str | None = None)`. Pass `Authorization: Bearer <token>` to ASAPClient when calling agent endpoints. `ResolvedAgent.run(payload, auth_token=...)` overrides instance token.
  - **Why**: ECO-002 — agents with proprietary auth.
  - **Verify**: Unit test: mock HTTP; assert request includes `Authorization: Bearer <token>` when auth_token set.

---

## Task 2.5: Document Raw Fetch path

- [ ] **2.5.1** Create raw-fetch.md
  - **File**: `docs/raw-fetch.md` (create new)
  - **What**: Document how to fetch `registry.json` and `revoked_agents.json` directly (curl, fetch). Include URLs (GitHub raw), schema, example payloads. Non-Python consumers can implement their own client.
  - **Why**: DOC-001 — non-Python languages.
  - **Verify**: Doc exists; `curl` examples work.

- [ ] **2.5.2** Add link from README or docs index
  - **File**: `README.md` or `docs/README.md` (modify)
  - **What**: Add link to `docs/raw-fetch.md` in "Documentation" or "For non-Python" section.
  - **Verify**: Link resolves.

---

## Task 2.6: Create client package __init__ and public API

- [ ] **2.6.1** Exports and public API
  - **File**: `src/asap/client/__init__.py` (modify — already created in E1.5)
  - **What**: Export `MarketClient`, `ResolvedAgent`, `verify_agent_trust`, `AgentRevokedException`, `SignatureVerificationError`. Add `asap.client` to `asap/__init__.py` exports if not present.
  - **Why**: Clean public API for `from asap.client import MarketClient`.
  - **Verify**: `from asap.client import MarketClient` works; `uv run python -c "from asap.client import MarketClient; print('ok')"` succeeds.

---

## Definition of Done

- [ ] `from asap.client import MarketClient` works
- [ ] resolve + run in &lt;5 lines; tests pass
- [ ] Raw Fetch doc exists
- [ ] `PYTHONPATH=src uv run pytest tests/client/ -v` passes
