# Sprint S1c: NeMo Agent Toolkit ↔ ASAP (v2.5.3)

**PRD**: D7, §3 (NeMo Agent Toolkit)  
**Branch**: `feat/v2.5.3-s1b-s1c-spikes` → **`release/2.5.3`**  
**Depends on**: [S0](./sprint-S0-candidate-lock.md) records S1c = **go** (default for Lab II)  
**Research map**: [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md)

**Trigger:** Lab II kickoff; S1c is a **planned technical spike** (not demand-gated like S1b).  
**Enables:** Public NVIDIA-stack guide; optional MCP bridge demo; feed for v2.5.5 A2A mapping.  
**Depends on:** v2.5.0 `protect_server`; research note pin (`nvidia-nat` 1.8.x).  
**Does not block:** S1 / S2 / S3 / S4. If incomplete at freeze, ship guide as **research / experimental** or defer demo to patch.

---

## Goal

Prove a **careful, honest** integration story: NeMo Agent Toolkit already speaks A2A + MCP; ASAP adds **agent identity and capability policy**. Prefer a reproducible MCP path (Path A) over claiming an A2A replacement.

---

## Design constraints

- Pin `nvidia-nat[mcp,a2a]==1.8.0` (or newer pin documented in research note) at spike start
- Joint examples: **Python 3.13** only (intersection with ASAP)
- No protocol fork; no new methods on `transport/server.py` / `client.py`
- Do **not** publish `nemo-agent-toolkit-asap` in this sprint (Path C = feasibility note only)
- Distinguish NAT OAuth2/Keycloak examples from ASAP Agent JWT + grants in every doc diagram
- Re-read upstream CHANGELOG + [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) §9 before coding

---

## Tasks

- [x] **2c.1 Refresh upstream pin**
  - [x] Run refresh commands in research note §9; update pin line if needed
  - [x] Skim protected MCP/A2A example READMEs for auth/transport changes

- [x] **2c.2 Transport & auth gap analysis (write first)**
  - [x] Table: NAT MCP transports (stdio / streamable-http / SSE) vs ASAP Auth Bridge carriage
  - [x] Table: OAuth2 user JWT (NAT protected examples) vs Host/Agent JWT + capability grants
  - [x] Decide Path A demo shape: stdio bridge **or** document blocker + HTTP follow-up (mcp-auth backlog)
  - [x] Append conclusions to research note (do not invent compatibility)

- [x] **2c.3 Path A spike (if transport allows)**
  - [x] ASAP side: minimal protected MCP server (reuse `examples/mcp_auth_bridge/` patterns)
  - [x] NAT side: workflow YAML using `nvidia-nat[mcp]` client against that server
  - [x] Example folder: `examples/nemo_agent_toolkit_asap/` with README, `.env.example`, pin versions
  - [x] Happy path without committing secrets; `NVIDIA_API_KEY` only if NIM is used (optional)

- [x] **2c.4 Path B docs (always)**
  - [x] `docs/integrations/nemo-agent-toolkit.md`
  - [x] Sections: what NAT is; A2A vs MCP vs ASAP; Agent Card → Manifest sketch; auth contrast; link ShellClaw/CUDA only as adjacent edge story
  - [x] Status banner: **experimental** — Path A demo under `examples/nemo_agent_toolkit_asap/`; still experimental until maintained promotion
  - [x] Leave MkDocs nav + home index to **S3**

- [x] **2c.5 Path C feasibility (short)**
  - [x] Appendix in public guide: third-party plugin naming (`nat.plugins.asap`, `nemo-agent-toolkit-asap`), ownership, CI matrix
  - [x] Explicit **out of ship** for v2.5.3 (research note §6 updated)

- [x] **2c.6 Tests / smoke**
  - [x] Exact commands documented in public guide + example README
  - [x] ASAP-side pytest always runs; optional NAT import skips when `nvidia-nat` absent (main CI does not require NAT)
  - [x] Smoke: `smoke_asap_side.py` / `run_demo.sh`; NAT path optional via `run_demo.sh nat`

---

## Acceptance criteria

- [x] Research note updated with spike-time pin + gap tables
- [x] Public guide published (`docs/integrations/nemo-agent-toolkit.md`) with honest auth/transport limits
- [x] Either: Path A runnable example **or** written blocker + follow-up issue/backlog pointer (no fake “native support” claim)
- [x] Path C deferred explicitly
- [x] Does not block S4 if only the guide ships

## Relevant files

### New / shipped

| Path | Role |
|------|------|
| [`docs/integrations/nemo-agent-toolkit.md`](../../../docs/integrations/nemo-agent-toolkit.md) | Public interop guide (2c.4) + Path C appendix (2c.5) |
| [`examples/nemo_agent_toolkit_asap/`](../../../examples/nemo_agent_toolkit_asap/) | Path A stdio demo (2c.3) |
| [`tests/examples/test_nemo_agent_toolkit_asap.py`](../../../tests/examples/test_nemo_agent_toolkit_asap.py) | ASAP-side smoke; NAT optional skip (2c.6) |
| [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md) | Pin, §10 gap analysis, §6 Path C |

### Reference

- `examples/mcp_auth_bridge/`
- `docs/adapters/mcp-auth-bridge.md`
- [backlog-mcp-auth-typescript.md](../v2.5.0/backlog-mcp-auth-typescript.md) — HTTP/streamable-http follow-up
- Upstream: `examples/MCP/simple_calculator_mcp_protected/`, `examples/A2A/math_assistant_a2a_protected/`

## Reviews

| Date | Tier | Verdict | Report |
|------|------|---------|--------|
| 2026-07-13 | T3 | Approved with caveats | [review-v2.5.3-S1b-S1c-spikes-20260713.md](../../code-review/private/review-v2.5.3-S1b-S1c-spikes-20260713.md) |
