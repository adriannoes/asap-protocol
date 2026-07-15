# Research note: NVIDIA NeMo Agent Toolkit ↔ ASAP

> **Status**: Living technical map for Adapter Lab II S1c  
> **Created**: 2026-07-11  
> **Last refreshed**: 2026-07-13 (S1c 2c.4–2c.6 public guide + Path C out-of-ship)  
> **Upstream pin**: [NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) @ tag **`v1.8.0`** (GitHub release published 2026-06-16; latest *release* unchanged); default branch **`develop`** HEAD `e8692d0050d03706bcd33d5b059937d59d4eed7d` (2026-07-10T05:21:32Z)  
> **PyPI**: `nvidia-nat` **1.8.0** (`requires-python >=3.11,<3.14`) — confirmed latest on PyPI 2026-07-13; tags include `v1.9.0-dev` but no newer stable release  
> **Install pin**: `nvidia-nat[mcp,a2a]==1.8.0`  
> **License**: Apache-2.0  
> **Docs**: https://docs.nvidia.com/nemo/agent-toolkit/latest/  
> **PRD**: [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md) D7  
> **Sprint**: [sprint-S1c-nemo-agent-toolkit.md](./sprint-S1c-nemo-agent-toolkit.md)

Re-verify tags/paths against `develop` before coding. This note is evidence from the public repo; spike refresh 2026-07-13 confirmed pin and auth/transport facts below.

---

## 1. What NAT is (and is not)

NeMo Agent Toolkit (formerly AgentIQ / AIQ) is a **framework-agnostic conductor**: YAML workflows, `nat` CLI, profiling/eval/optimize, plus **first-class MCP and A2A plugins**. It wraps LangChain, LlamaIndex, CrewAI, Semantic Kernel, Google ADK, Autogen, Agno, Strands, etc.

It is **not** a replacement for ASAP. It already speaks Google/Linux Foundation **A2A** and Anthropic **MCP**. ASAP’s wedge is **agent identity, capability grants, compliance, metering/discovery** — especially when NAT workflows must call *external* agents/tools under policy.

| Layer | NAT today | ASAP today |
|-------|-----------|------------|
| Tool protocol | MCP client + MCP/FastMCP server | MCP Auth Bridge (`protect_server`) + envelope MCP payloads |
| Agent protocol | A2A client + `nat a2a serve` (official `a2a-sdk`) | ASAP envelope / task FSM / well-known manifest |
| Auth on MCP/A2A examples | OAuth2 + Keycloak (user JWT, scopes, JWKS) | Host/Agent JWT + `CapabilityRegistry` grants |
| Discovery | A2A Agent Card `/.well-known/agent-card.json` | ASAP manifest / Lite Registry / well-known |
| LLM runtime | NIM (`_type: nim`) and others | Out of band (edge CUDA via ShellClaw story) |

---

## 2. Repo layout (integration-relevant)

Monorepo under `packages/` (install via extras on `nvidia-nat`):

| Package / extra | Role |
|-----------------|------|
| `nvidia-nat-core` | Core runtime, entry points, workflows |
| `nvidia-nat[a2a]` → `nvidia-nat-a2a` | A2A client + server front-end; depends on `a2a-sdk[http-server]>=0.3.20,<1.0.0` |
| `nvidia-nat[mcp]` → `nvidia-nat-mcp` | MCP client + MCP server front-end; depends on `mcp~=1.25` |
| `nvidia-nat[fastmcp]` → `nvidia-nat-fastmcp` | FastMCP server runtime + `token_verifier` |
| `nvidia-nat-security` | Security-related helpers (inspect at spike) |
| Framework extras | `langchain`, `crewai`, `llama-index`, `semantic_kernel`, `adk`, `agno`, … |

**Entry points (A2A)** — from `packages/nvidia_nat_a2a/pyproject.toml`:

- `nat.components` → `nat_a2a_client = nat.plugins.a2a.client.client_impl`
- `nat.front_ends` → `nat_a2a_server = nat.plugins.a2a.server.register_frontend`
- `nat.cli` → `a2a` → `nat a2a …`

**Entry points (MCP)** — from `packages/nvidia_nat_mcp/pyproject.toml`:

- `nat.components` → `nat_mcp`, `nat_mcp_auth`
- `nat.front_ends` → `nat_mcp_server`
- `nat.cli` → `mcp`

**Source hotspots:**

- `packages/nvidia_nat_a2a/src/nat/plugins/a2a/{client,server,auth,cli}/`
- `packages/nvidia_nat_mcp/src/nat/plugins/mcp/{auth,server,…}/`
- `packages/nvidia_nat_fastmcp/src/nat/plugins/fastmcp/server/{token_verifier,tool_converter,…}.py`

---

## 3. Upstream examples to study first

| Example | Why it matters for ASAP |
|---------|-------------------------|
| `examples/MCP/simple_calculator_mcp/` | Unprotected MCP server/client baseline |
| `examples/MCP/simple_calculator_mcp_protected/` | OAuth2-protected MCP (Keycloak, Bearer JWT, JWKS) — **contrast with ASAP Auth Bridge** |
| `examples/MCP/simple_calculator_fastmcp(_protected)/` | FastMCP publish path |
| `examples/MCP/simple_auth_mcp/` | `mcp_oauth2` provider / corporate MCP |
| `examples/A2A/math_assistant_a2a/` | Hybrid A2A + MCP + local tools |
| `examples/A2A/math_assistant_a2a_protected/` | OAuth2-protected A2A client/server |

Docs index:

- A2A overview: `docs/source/components/integrations/a2a.md`
- A2A client/server: `docs/source/build-workflows/a2a-client.md`, `docs/source/run-workflows/a2a-server.md`
- A2A auth: `docs/source/components/auth/a2a-auth.md`
- MCP client/server: `docs/source/build-workflows/mcp-client.md`, `docs/source/run-workflows/mcp-server.md`
- MCP auth: `docs/source/components/auth/mcp-auth/`
- **Third-party plugins**: `docs/source/extend/third-party-plugins.md` (+ Public Plugin API)

---

## 4. Auth reality check (do not hand-wave)

### NAT protected MCP / A2A

- User-facing OAuth2 (Authorization Code), Keycloak in examples
- JWT validated with JWKS; scopes + audience checks
- MCP auth: **streamable-http only**; upstream warns **SSE has no authentication**
- Patterns: `per_user_mcp_client`, `mcp_oauth2` auth provider, service-account auth examples

### ASAP MCP Auth Bridge (v2.5.0)

- Agent JWT in `_meta.asap_agent_jwt` (stdio path) + `CapabilityRegistry.check_grant`
- Opt-in `protect_server`; codes `asap:auth_required`, `asap:invalid_token`, `asap:capability_denied`, …
- HTTP/SSE ASAP MCP middleware still deferred (`@asap-protocol/mcp-auth`)

**Implication for S1c:** the cleanest near-term demo is **NAT as MCP client → ASAP-protected MCP server** only where transports align, **or** document a dual-hop (NAT OAuth user session ≠ ASAP agent grant) explicitly. Do not claim drop-in replacement for Keycloak examples.

---

## 5. Recommended ASAP integration paths (priority order)

### Path A — MCP bridge (Lab II primary technical goal for S1c)

1. Run ASAP example MCP server with `protect_server` (reuse `examples/mcp_auth_bridge/`).
2. Configure a NAT workflow with `nvidia-nat[mcp]` to call that server.
3. Document token carriage: what NAT sends today (OAuth Bearer) vs what ASAP expects (Agent JWT / grants).
4. If gap is transport-only (stdio vs streamable-http), either:
   - ship a **documented workaround** (local stdio bridge process), or
   - file a follow-up for ASAP HTTP MCP auth (ties to mcp-auth backlog) — **do not** expand protocol in Lab II.

**Success:** a maintainer can reproduce “NAT workflow invokes ASAP-gated tool” with clear security notes.

### Path B — Discovery mapping (docs + seed for v2.5.5)

Map A2A Agent Card fields → ASAP Manifest / skills (feeds COMPAT-005). No full runtime A2A↔ASAP bridge required in v2.5.3.

### Path C — Third-party NAT plugin (explicitly out of Lab II ship)

Upstream now encourages provider-owned packages:

| Surface | Convention |
|---------|------------|
| Repo | `NeMo-Agent-Toolkit-<provider>` |
| Dist | `nemo-agent-toolkit-<provider>` |
| Import | `nat.plugins.<provider>` |
| Entry | `nat_<provider>` |

A future `nemo-agent-toolkit-asap` / `nat.plugins.asap` could register ASAP client/server functions. S1c may **spike feasibility** only; publishing the plugin is a follow-up release decision.

### Non-goals for S1c

- Replacing NAT’s A2A stack with ASAP
- NIM-as-adapter (NIM is LLM backend; optional in hello-world only)
- NeMo Framework training stack
- Forking `nvidia-nat-*` into our monorepo

---

## 6. Third-party plugin feasibility checklist (spike)

From upstream `third-party-plugins.md`. **Public write-up:** [docs/integrations/nemo-agent-toolkit.md](../../../docs/integrations/nemo-agent-toolkit.md) appendix (Path C). **Explicit out of ship for v2.5.3** — do not publish the plugin in this release.

| Item | Status (2026-07-13) |
|------|---------------------|
| Public Plugin API stability for NAT 1.8.x | Documented as **unconfirmed until Path A promoted** — re-read upstream before any package start |
| Sketch `nat.plugins.asap` / `asap__discover`, `asap__task_request` | **Sketched** in public guide appendix |
| Naming: import `nat.plugins.asap`, dist `nemo-agent-toolkit-asap` | **Recorded** |
| Ownership: ASAP monorepo vs `NeMo-Agent-Toolkit-asap` | **Options listed**; decision deferred |
| CI matrix: Python 3.11–3.13 × `nvidia-nat==1.8.0` | **Sketched**; joint Path A examples stay on **3.13** only; NAT must remain optional |
| Start the package | **Blocked** until Path A is promoted + ownership decided |

---


## 7. Version & environment constraints

| Constraint | Value |
|------------|--------|
| Python | 3.11–3.13 (NAT); ASAP is 3.13+ — use **3.13** intersection for joint examples |
| Install | `pip install "nvidia-nat[mcp,a2a]==1.8.0"` (pin at spike start; bump only intentionally) |
| CLI | `nat run`, `nat a2a serve`, `nat mcp …` |
| Secrets | `NVIDIA_API_KEY` for NIM demos; never commit; Keycloak only if reproducing protected OAuth examples |

---

## 8. Risks

| Risk | Mitigation |
|------|------------|
| Dual auth models (OAuth user vs Agent JWT) confuse docs | Side-by-side sequence diagrams; never claim equivalence |
| Transport mismatch (ASAP stdio Auth Bridge vs NAT streamable-http) | Spike transport first; document gap; optional bridge process |
| Scope creep into full A2A runtime bridge | Keep Path B docs-only; point to v2.5.5 |
| Upstream moves fast (`develop`) | Pin 1.8.0; re-read CHANGELOG at S1c start |
| Appearing to compete with A2A-in-NAT | Position ASAP as **policy/identity complement**, not A2A substitute |

---

## 9. Refresh procedure (before S1c coding)

```bash
gh api repos/NVIDIA/NeMo-Agent-Toolkit/releases/latest --jq '.tag_name'
gh api repos/NVIDIA/NeMo-Agent-Toolkit/commits/develop --jq '.sha,.commit.committer.date'
# skim CHANGELOG.md + docs/source/components/integrations/a2a.md + mcp-auth/
```

Update this file’s pin line when the spike starts.

---

## 10. Spike gap analysis (2026-07-13)

Evidence sources for this section:

| Source | What was checked |
|--------|------------------|
| PyPI `nvidia-nat` JSON | Latest version **1.8.0** |
| `gh api …/releases/latest` | Tag **`v1.8.0`** (published 2026-06-16) |
| `gh api …/commits/develop` | SHA `e8692d0…`, 2026-07-10 |
| `gh api …/tags` | `v1.9.0-dev` present; latest stable release still **v1.8.0** |
| `v1.8.0` READMEs | `examples/MCP/simple_calculator_mcp_protected/`, `examples/A2A/math_assistant_a2a_protected/` |
| `v1.8.0` docs/code | `docs/source/build-workflows/mcp-client.md`, `docs/source/components/auth/mcp-auth/index.md`, `packages/nvidia_nat_mcp/.../client_config.py`, `client_base.py` |
| `v1.8.0...develop` compare | Protected MCP/A2A example paths: only `uv.lock` churn — **no auth/transport semantic change** since the note was written |
| ASAP | `docs/adapters/mcp-auth-bridge.md`, `examples/mcp_auth_bridge/`, [backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) |

### 10.1 Transport matrix — NAT MCP client vs ASAP Auth Bridge

| Transport | NAT `mcp_client` / `per_user_mcp_client` | NAT OAuth / `auth_provider` | ASAP `protect_server` (v2.5.0) | Honest overlap for Path A? |
|-----------|------------------------------------------|-----------------------------|--------------------------------|----------------------------|
| **stdio** | Supported (`server.command` / `args` / `env`) | **Not supported** — config validator rejects `auth_provider` and `custom_headers` on stdio | **Supported** — Mode A is native stdio `MCPServer` + `_meta.asap_agent_jwt` (optional dev `ASAP_AGENT_JWT` env) | **Yes** — spawn ASAP example as stdio child; auth is *not* NAT OAuth |
| **streamable-http** | Supported (default; `server.url`) | **Supported** — Bearer via `mcp_oauth2` / service-account; protected examples use this | **Not shipped** — no Python HTTP MCP Auth Bridge; TS `@asap-protocol/mcp-auth` deferred | **No** — NAT’s happy path ≠ ASAP’s shipped protect surface |
| **SSE** | Supported (legacy) | **Explicitly unsupported** — upstream warns SSE has no authentication | **Not shipped** for Auth Bridge | **No** |

Notes (do not invent compatibility):

- NAT `session.call_tool(tool_name, tool_args)` does **not** pass MCP `_meta`. There is no first-class ASAP Agent JWT injection on NAT tool calls.
- ASAP protected `tools/call` expects `_meta.asap_agent_jwt`, or — only when `allow_env_jwt_fallback=True` — `ASAP_AGENT_JWT` in the **server** process environment (dev-only; already enabled in `examples/mcp_auth_bridge/`).
- ASAP also has registry/MCP serve helpers with `--transport` choices including `streamable-http` (`src/asap/mcp/serve.py`), but that path is **not** the Auth Bridge; `protect_server` remains the stdio Mode A adapter documented in [mcp-auth-bridge.md](../../../docs/adapters/mcp-auth-bridge.md).

### 10.2 Auth matrix — NAT OAuth2 user JWT vs ASAP Host/Agent JWT + grants

| Dimension | NAT protected MCP/A2A examples (`v1.8.0`) | ASAP MCP Auth Bridge (v2.5.0) |
|-----------|------------------------------------------|-------------------------------|
| Actor | End **user** (browser Authorization Code via Keycloak) | **Agent** identity (Host JWT → Agent JWT) |
| Token | OIDC/OAuth2 access JWT (JWKS, `iss` / `aud` / scopes) | ASAP Agent JWT (`verify_agent_jwt`) |
| Carriage | HTTP `Authorization: Bearer <jwt>` on streamable-http | MCP `_meta.asap_agent_jwt` per `tools/call` (stdio); optional env fallback |
| Authorization | Scope + audience checks on the resource server | `CapabilityRegistry.check_grant` (+ constraints) |
| Discovery | MCP OAuth discovery / A2A Agent Card `securitySchemes` | ASAP well-known manifest / skills (orthogonal) |
| Equivalence | — | **None** — complementary policy layer, not a Keycloak drop-in |

Upstream protected MCP README (`simple_calculator_mcp_protected`, tag `v1.8.0`): server at `http://localhost:9902`, client `per_user_mcp_client` + `mcp_oauth2`, Keycloak scopes such as `calculator_mcp_execute`. Protected A2A README mirrors the same OAuth2/Keycloak pattern over A2A JSON-RPC Bearer — irrelevant to ASAP Auth Bridge carriage, useful only for Path B discovery contrast.

### 10.3 Path A demo shape decision

**Recommendation: proceed Path A this sprint — YES (stdio).**

| Option | Verdict | Why |
|--------|---------|-----|
| **A1 — NAT stdio → ASAP `protect_server` stdio** | **Choose for 2c.3** | Transport aligns. NAT already documents stdio clients (`simple_calculator_mcp` mixes stdio + streamable-http). Reuse `examples/mcp_auth_bridge/` patterns. |
| A2 — NAT streamable-http → ASAP HTTP MCP auth | **Blocked this sprint** | ASAP has no Python HTTP/SSE Auth Bridge. Follow-up: [backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) (HTTP/SSE middleware) and any future **Python** HTTP MCP auth work — do **not** invent a bridge in Lab II (PRD D5/D6). |
| A3 — Pretend NAT OAuth ≡ ASAP grants | **Forbidden** | Dual auth models; docs must show side-by-side, not equivalence. |

**Demo shape for 2c.3 (when implemented):**

1. ASAP side: protected stdio server (reuse / thin wrap of `examples/mcp_auth_bridge/` — `echo` public, `secure_action` granted).
2. NAT side: YAML `function_groups` with `_type: mcp_client`, `server.transport: stdio`, `command`/`args` pointing at that server (Python 3.13).
3. Auth carriage honesty:
   - NAT will **not** send `_meta.asap_agent_jwt`.
   - Use the existing **dev-only** `allow_env_jwt_fallback` path so the ASAP child process authenticates protected calls without in-band `_meta` (e.g. mint demo JWT into the server process env at startup, or a documented mint → `server.env.ASAP_AGENT_JWT` flow with **deterministic demo keys** so parent and child share material).
   - Label clearly: single-agent local demo; not multi-tenant; not production.
4. Negative control: without grant / without JWT env → `asap:auth_required` or `asap:capability_denied` as applicable.
5. Do **not** wire Keycloak or claim NAT `mcp_oauth2` talks to ASAP.

**HTTP follow-up pointer (explicit blocker for streamable-http Path A):**

- TypeScript: [engineering/tasks/v2.5.0/backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) (`@asap-protocol/mcp-auth` HTTP/SSE).
- Python: no shipped HTTP MCP Auth Bridge equivalent to `protect_server`; Lab II must not expand protocol or transport servers (`src/asap/transport/{server,client}.py` untouched).

### 10.4 Upstream skim — auth/transport changes since 2026-07-11 note

| Area | Finding (2026-07-13) |
|------|----------------------|
| Release pin | Still **v1.8.0** on GitHub + PyPI |
| Protected MCP example | Still streamable-http + Keycloak OAuth2 + `per_user_mcp_client`; no stdio auth story |
| Protected A2A example | Still Agent Card discovery + Bearer JWT; unchanged for ASAP Auth Bridge |
| MCP client docs | Still three transports; auth **only** on streamable-http; stdio for local process spawn |
| `develop` vs `v1.8.0` | No meaningful protected-example README/config auth changes (lockfile-only in compare filter) |

---

## Change log

| Date | Change |
|------|--------|
| 2026-07-13 | S1c 2c.4–2c.6: public guide `docs/integrations/nemo-agent-toolkit.md`; §6 Path C feasibility marked out-of-ship; commands + CI-optional NAT documented |
| 2026-07-13 | S1c Wave 1–2: reconfirmed pin `nvidia-nat[mcp,a2a]==1.8.0`; skimmed protected MCP/A2A READMEs + MCP client/auth docs; appended §10 transport/auth gap analysis; Path A = YES stdio |
| 2026-07-11 | Initial map from public GitHub + PyPI (v1.8.0 / develop) |
