# Sprint E3: Framework Integrations

> **Goal**: LangChain, CrewAI, PydanticAI tools; asap-mcp-server
> **Prerequisite**: Sprint E2 (MarketClient)
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` — Optional deps [mcp], [langchain], [crewai]
- `src/asap/integrations/langchain.py` — LangChainAsapTool
- `src/asap/integrations/crewai.py` — CrewAIAsapTool
- `src/asap/integrations/pydanticai.py` — PydanticAI binding
- `src/asap/integrations/__init__.py` — Exports
- `src/asap/mcp/serve.py` — asap-mcp-server entry point
- `tests/integrations/test_langchain.py`, `test_crewai.py`

---

## Trigger / Enables / Depends on

**Trigger:** Developer imports `LangChainAsapTool`, `CrewAIAsapTool`, or runs `uvx asap-mcp-server`.

**Enables:** LangChain/CrewAI/PydanticAI users invoke ASAP agents as tools; Claude Desktop/Cursor users use MCP.

**Depends on:** Sprint E2 (MarketClient, ResolvedAgent).

---

## Acceptance Criteria

- [ ] `LangChainAsapTool(urn)` inherits BaseTool; maps agent schema to args_schema; execute runs ASAP handshake
- [ ] `CrewAIAsapTool(urn)` compatible with CrewAI BaseTool
- [ ] `asap-mcp-server` installable via `uvx asap-mcp-server`; exposes agents as MCP Tools
- [ ] PydanticAI integration (SHOULD) — native binding

---

## Task 3.1: Add optional dependencies to pyproject.toml

- [ ] **3.1.1** Optional dependency groups
  - **File**: `pyproject.toml` (modify)
  - **What**: Add `[project.optional-dependencies]` entries: `mcp = ["mcp>=1.0"]`, `langchain = ["langchain-core>=0.2"]`, `crewai = ["crewai>=0.80"]`. Ensure base package has no hard dependency on these.
  - **Why**: PKG-003 — optional groups for framework integrations.
  - **Verify**: `uv sync` and `uv sync --extra mcp` install without error.

---

## Task 3.2: Create LangChain integration

- [ ] **3.2.1** Create LangChainAsapTool class
  - **File**: `src/asap/integrations/langchain.py` (create new)
  - **What**: `LangChainAsapTool(urn: str, client: MarketClient | None = None)` inherits `BaseTool` from langchain-core. Lazy-import langchain_core (try/except or `importlib`); skip if not installed. Default client = `MarketClient()`.
  - **Why**: INT-001 — LangChain native Tool.
  - **Pattern**: langchain-core `BaseTool`; `name`, `description` from urn or generic.
  - **Verify**: `from asap.integrations.langchain import LangChainAsapTool` works when langchain-core installed.

- [ ] **3.2.2** Implement _run and _arun
  - **File**: `src/asap/integrations/langchain.py`
  - **What**: In `_run`/`_arun`, call `client.resolve(urn)` then `agent.run(payload)`. Map tool input to payload dict. Return result as string or dict. Handle `AgentRevokedException`, `SignatureVerificationError`.
  - **Why**: INT-006 — execute ASAP handshake.
  - **Verify**: `pytest tests/integrations/test_langchain.py` — tool invokes agent; mock MarketClient returns result.

- [ ] **3.2.3** Write tests for LangChain integration
  - **File**: `tests/integrations/test_langchain.py` (create new)
  - **What**: Test tool invoke with mock MarketClient; skip if langchain-core not installed. Test args_schema if mapped.
  - **Verify**: `pytest tests/integrations/test_langchain.py -v` passes (or skips).

---

## Task 3.3: Create CrewAI integration

- [ ] **3.3.1** Create CrewAIAsapTool class
  - **File**: `src/asap/integrations/crewai.py` (create new)
  - **What**: `CrewAIAsapTool(urn: str, client: MarketClient | None = None)` compatible with CrewAI BaseTool. Lazy-import crewai; resolve, run, return pattern. Check CrewAI Tool interface (may differ from LangChain).
  - **Why**: INT-002 — CrewAI native Tool.
  - **Verify**: `from asap.integrations.crewai import CrewAIAsapTool` works when crewai installed.

- [ ] **3.3.2** Write tests for CrewAI integration
  - **File**: `tests/integrations/test_crewai.py` (create new)
  - **What**: Test tool with mock MarketClient; skip if crewai not installed.
  - **Verify**: `pytest tests/integrations/test_crewai.py -v` passes (or skips).

---

## Task 3.4: Create PydanticAI integration (SHOULD)

- [ ] **3.4.1** PydanticAI binding
  - **File**: `src/asap/integrations/pydanticai.py` (create new)
  - **What**: Native integration leveraging ASAP Pydantic schema. Provide Tool or ToolDef wrapping MarketClient.run. Use Pydantic models for input/output. Lazy-import pydantic-ai.
  - **Why**: INT-003 — PydanticAI typed integration.
  - **Verify**: Test with pydantic-ai if available; skip if not.

---

## Task 3.5: Create asap-mcp-server entry point

- [ ] **3.5.1** Create serve.py scaffold
  - **File**: `src/asap/mcp/serve.py` (create new)
  - **What**: Create `main()` that parses args (optional: `--registry-url`). Use `asap.discovery.registry.discover_from_registry` (or sync equivalent) to load registry. Use existing `asap.mcp.server.MCPServer` or FastMCP if mcp package provides it.
  - **Why**: INT-007 — MCP server entry.
  - **Pattern**: `asap.mcp.server.MCPServer`; `tests/mcp/test_asap_integration.py`.
  - **Verify**: `uv run python -m asap.mcp.serve` runs (stdio); exits cleanly.

- [ ] **3.5.2** Register MCP Tools for ASAP agents
  - **File**: `src/asap/mcp/serve.py`
  - **What**: For each agent in registry (or generic "asap_invoke" with urn param), register tool with MCPServer. Tool handler: resolve(urn), run(payload). Map MCP tool call to ASAP payload.
  - **Why**: Expose agents as MCP Tools.
  - **Verify**: List tools returns ASAP agents or asap_invoke; tools/call returns result.

- [ ] **3.5.3** Add pyproject scripts entry
  - **File**: `pyproject.toml` (modify)
  - **What**: Add `asap-mcp-server = "asap.mcp.serve:main"` under `[project.scripts]`. Ensure mcp extra is required for this script (or document `pip install asap-protocol[mcp]`).
  - **Why**: `uvx asap-mcp-server` runs the server.
  - **Verify**: `uvx asap-mcp-server` runs; `uv run asap-mcp-server` works with [mcp] installed.

- [ ] **3.5.4** Write test for MCP serve (optional)
  - **File**: `tests/mcp/test_serve.py` (create new) or extend existing
  - **What**: Test serve loads registry; tools registered; tools/call returns mock result.
  - **Verify**: Test passes.

---

## Task 3.6: Create integrations package __init__

- [ ] **3.6.1** Exports with lazy imports
  - **File**: `src/asap/integrations/__init__.py` (create new)
  - **What**: Export `LangChainAsapTool`, `CrewAIAsapTool` (and PydanticAI if implemented). Lazy imports: `def __getattr__(name)` or try/except per export to avoid loading optional deps on import.
  - **Verify**: `from asap.integrations import LangChainAsapTool` works when langchain-core installed; ImportError when not.

---

## Definition of Done

- [ ] `LangChainAsapTool(urn)` works
- [ ] `CrewAIAsapTool(urn)` works
- [ ] `uvx asap-mcp-server` runs
- [ ] `PYTHONPATH=src uv run pytest tests/integrations/ -v` passes (with optional deps)
