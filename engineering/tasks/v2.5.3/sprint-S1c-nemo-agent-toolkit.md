# Sprint S1c: NeMo Agent Toolkit ↔ ASAP (v2.5.3)

**PRD**: D7, §3 (NeMo Agent Toolkit)  
**Branch**: `feat/v2.5.3-s1c-nemo-agent-toolkit` → **`release/2.5.3`**  
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

- [ ] **2c.1 Refresh upstream pin**
  - [ ] Run refresh commands in research note §9; update pin line if needed
  - [ ] Skim protected MCP/A2A example READMEs for auth/transport changes

- [ ] **2c.2 Transport & auth gap analysis (write first)**
  - [ ] Table: NAT MCP transports (stdio / streamable-http / SSE) vs ASAP Auth Bridge carriage
  - [ ] Table: OAuth2 user JWT (NAT protected examples) vs Host/Agent JWT + capability grants
  - [ ] Decide Path A demo shape: stdio bridge **or** document blocker + HTTP follow-up (mcp-auth backlog)
  - [ ] Append conclusions to research note (do not invent compatibility)

- [ ] **2c.3 Path A spike (if transport allows)**
  - [ ] ASAP side: minimal protected MCP server (reuse `examples/mcp_auth_bridge/` patterns)
  - [ ] NAT side: workflow YAML using `nvidia-nat[mcp]` client against that server
  - [ ] Example folder: `examples/nemo_agent_toolkit_asap/` with README, `.env.example`, pin versions
  - [ ] Happy path without committing secrets; `NVIDIA_API_KEY` only if NIM is used (optional)

- [ ] **2c.4 Path B docs (always)**
  - [ ] `docs/integrations/nemo-agent-toolkit.md`
  - [ ] Sections: what NAT is; A2A vs MCP vs ASAP; Agent Card → Manifest sketch; auth contrast; link ShellClaw/CUDA only as adjacent edge story
  - [ ] Status banner: **experimental** until Path A demo is green
  - [ ] Leave MkDocs nav + home index to **S3**

- [ ] **2c.5 Path C feasibility (optional, short)**
  - [ ] One page in research note or guide appendix: third-party plugin naming (`nat.plugins.asap`), ownership, CI matrix
  - [ ] Explicit **out of ship** for v2.5.3

- [ ] **2c.6 Tests / smoke**
  - [ ] Document exact commands; if demo exists, add smoke test or CI-skippable script with clear deps
  - [ ] Do not fail main CI if `nvidia-nat` is optional extra — keep NAT as optional/dev path

---

## Acceptance criteria

- [ ] Research note updated with spike-time pin + gap tables
- [ ] Public guide published (`docs/integrations/nemo-agent-toolkit.md`) with honest auth/transport limits
- [ ] Either: Path A runnable example **or** written blocker + follow-up issue/backlog pointer (no fake “native support” claim)
- [ ] Path C deferred explicitly
- [ ] Does not block S4 if only the guide ships

## Relevant files

### New

- `docs/integrations/nemo-agent-toolkit.md`
- `examples/nemo_agent_toolkit_asap/` (if Path A proceeds)
- Updates to [research-nemo-agent-toolkit.md](./research-nemo-agent-toolkit.md)

### Reference

- `examples/mcp_auth_bridge/`
- `docs/adapters/mcp-auth-bridge.md`
- Upstream: `examples/MCP/simple_calculator_mcp_protected/`, `examples/A2A/math_assistant_a2a_protected/`
