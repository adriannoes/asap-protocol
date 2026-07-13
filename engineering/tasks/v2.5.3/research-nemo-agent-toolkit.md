# Research note: NVIDIA NeMo Agent Toolkit ↔ ASAP

> **Status**: Living technical map for Adapter Lab II S1c  
> **Created**: 2026-07-11  
> **Upstream pin**: [NVIDIA/NeMo-Agent-Toolkit](https://github.com/NVIDIA/NeMo-Agent-Toolkit) @ tag **`v1.8.0`** (2026-06-16); default branch **`develop`** (last push observed 2026-07-10)  
> **PyPI**: `nvidia-nat` **1.8.0** (`requires-python >=3.11,<3.14`)  
> **License**: Apache-2.0  
> **Docs**: https://docs.nvidia.com/nemo/agent-toolkit/latest/  
> **PRD**: [prd-v2.5.3-adapter-lab-ii.md](../../../product/prd/prd-v2.5.3-adapter-lab-ii.md) D7  
> **Sprint**: [sprint-S1c-nemo-agent-toolkit.md](./sprint-S1c-nemo-agent-toolkit.md)

Re-verify tags/paths against `develop` before coding. This note is evidence from the public repo as of 2026-07-11, not a substitute for reading upstream CHANGELOG at spike start.

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

From upstream `third-party-plugins.md`:

- [ ] Confirm Public Plugin API stability for our target NAT minor (1.8.x)
- [ ] Sketch `nat.plugins.asap` function group: e.g. `asap__discover`, `asap__task_request`
- [ ] Decide ownership: live in ASAP repo vs separate `NeMo-Agent-Toolkit-asap`
- [ ] CI matrix: Python 3.11–3.13 × `nvidia-nat==1.8.0`
- [ ] Do **not** start the package until Path A demo works

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

## Change log

| Date | Change |
|------|--------|
| 2026-07-11 | Initial map from public GitHub + PyPI (v1.8.0 / develop) |
