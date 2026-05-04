# Sprint E3: Framework Integrations

> **Goal**: Integrations for LangChain, CrewAI, PydanticAI, LlamaIndex, SmolAgents, Vercel AI SDK; Robust `asap-mcp-server`
> **Prerequisite**: Sprint E2 (MarketClient)
> **Parent Roadmap**: [tasks-v2.1.0-roadmap.md](./tasks-v2.1.0-roadmap.md)

---

## Relevant Files

- `pyproject.toml` — Optional deps `[mcp]`, `[langchain]`, `[crewai]`, `[llamaindex]`, `[smolagents]`, `[pydanticai]` (modified)
- `src/asap/integrations/langchain.py` — LangChainAsapTool (created)
- `src/asap/integrations/__init__.py` — Lazy exports (created)
- `tests/integrations/test_langchain.py` — LangChain integration tests (created)
- `src/asap/integrations/crewai.py` — CrewAIAsapTool (created)
- `tests/integrations/test_crewai.py` — CrewAI integration tests (created)
- `src/asap/integrations/pydanticai.py` — asap_tool_for_urn, Tool.from_schema (created)
- `tests/integrations/test_pydanticai.py` — PydanticAI integration tests (created)
- `src/asap/integrations/llamaindex.py` — LlamaIndexAsapTool wrapping FunctionTool (created)
- `tests/integrations/test_llamaindex.py` — LlamaIndex integration tests (created)
- `src/asap/mcp/serve.py` — asap-mcp-server (FastMCP, asap_invoke, asap_discover, --whitelist-urns)
- `tests/mcp/test_serve.py` — MCP serve tests (created)
- `src/asap/integrations/smolagents.py` — SmolAgentsAsapTool (created)
- `tests/integrations/test_smolagents.py` — SmolAgents integration tests (created)
- `src/asap/integrations/vercel_ai.py` — create_asap_tools_router (created)
- `tests/integrations/test_vercel_ai.py` — Vercel AI bridge tests (created)
- `docs/guides/vercel-ai-sdk.md` — Vercel AI SDK integration guide (created)
- `src/asap/integrations/__init__.py` — Exports
- `src/asap/mcp/serve.py` — asap-mcp-server entry point
- `tests/integrations/test_*.py`
- `tests/integrations/test_integrations_init.py` — Lazy exports and __all__ for asap.integrations

---

## Trigger / Enables / Depends on

**Trigger:** Developer imports ASAP tools for their framework of choice, or runs `uvx asap-mcp-server`.

**Enables:** Native integration with LangChain, CrewAI, PydanticAI, LlamaIndex, SmolAgents, Vercel AI SDK, and MCP (Claude Desktop/Cursor).

**Depends on:** Sprint E2 (MarketClient, ResolvedAgent).

---

## Acceptance Criteria

- [x] `LangChainAsapTool(urn)` inherits BaseTool; maps agent JSON schema to `args_schema` dynamically.
- [x] `CrewAIAsapTool(urn)` compatible with CrewAI BaseTool, properly typed.
- [x] PydanticAI integration leverages schemas.
- [x] `LlamaIndexAsapTool(urn)` compatible with LlamaIndex `FunctionTool`/`BaseTool`.
- [x] `SmolAgentsAsapTool(urn)` compatible with Hugging Face SmolAgents `Tool`.
- [x] Vercel AI SDK bridge implemented (FastAPI router or HTTP adapter).
- [x] `asap-mcp-server` installable via `uv run asap-mcp-server` (uvx when on PyPI); robustly exposes agents avoiding context limits.

---

## Task 3.1: Add optional dependencies to pyproject.toml

- [x] **3.1.1** Optional dependency groups
  - **File**: `pyproject.toml` (modify)
  - **What**: Add `[project.optional-dependencies]` entries for `mcp = ["mcp>=1.0.0"]`, `langchain = ["langchain-core>=0.2"]`, `crewai = ["crewai>=0.80"]`, `llamaindex = ["llama-index-core>=0.10"]`, `smolagents = ["smolagents>=1.0"]`.
  - **Why**: PKG-003 — optional groups for framework integrations without bloating the base package.
  - **Verify**: `uv sync --extra <name>` works for each group.

---

## Task 3.2: Create LangChain integration

- [x] **3.2.1** Create LangChainAsapTool class
  - **File**: `src/asap/integrations/langchain.py`
  - **What**: `LangChainAsapTool(urn: str, client: MarketClient | None = None)` inherits `BaseTool`. Lazy-import `langchain_core`.
  - **Refinement (Dynamic Schema):** Use `pydantic.create_model(...)` dynamically in `__init__` to map the ASAP agent's JSON Schema to a `pydantic.BaseModel` for the `args_schema` attribute. LangChain validates inputs against this schema.
- [x] **3.2.2** Implement _run and _arun
  - **What**: Call `client.resolve(urn)` then `agent.run(payload)`.
  - **Refinement (Exception Handling):** Catch `AgentRevokedException` or signature validation errors and return a string-formatted error message (e.g. `"Error: Agent revoked or invalid input: <details>"`) instead of throwing a Python exception. This allows the LLM to gracefully observe the failure and attempt to correct its tool arguments.
- [x] **3.2.3** Write tests for LangChain integration

---

## Task 3.3: Create CrewAI integration

- [x] **3.3.1** Create CrewAIAsapTool class
  - **File**: `src/asap/integrations/crewai.py`
  - **What**: `CrewAIAsapTool(urn: str, client: MarketClient | None = None)` compatible with CrewAI BaseTool. Lazy-import `crewai`.
  - **Refinement (Pydantic v2):** Like LangChain, CrewAI relies heavily on Pydantic v2 schemas. Ensure dynamically created models using `pydantic.create_model` are attached so the framework's native validators work correctly. Avoid arbitrary/untyped keyword arguments.
- [x] **3.3.2** Write tests for CrewAI integration

---

## Task 3.4: Create PydanticAI integration

- [x] **3.4.1** PydanticAI binding
  - **File**: `src/asap/integrations/pydanticai.py`
  - **What**: Native integration wrapping `MarketClient.run`.
  - **Refinement (Static vs Dynamic Types):** Since PydanticAI relies on static type hints on functions (e.g., `@tool`), dynamically mapping a single URN requires care. Utilize the programmatic approach: `pydantic_ai.Tool(function, name, description, parameters_schema=...)` and inject the translated JSON Schema of the ASAP agent manually if dynamic BaseModel generation encounters issues.

---

## Task 3.5: Create asap-mcp-server

- [x] **3.5.1** Create serve.py scaffold
  - **File**: `src/asap/mcp/serve.py`
  - **Refinement (Transport & API):** Evaluate using `FastMCP` (from the official `mcp` SDK) to bootstrap the server, as it acts like FastAPI for MCP tools and handles underlying complexities. Explicitly ensure `StdioServerTransport` is used, as it is the standard transport required by Claude Desktop and Cursor.
- [x] **3.5.2** Register MCP Tools context-safely
  - **Refinement (Context Limits & Discovery):** Do **NOT** blindly register hundreds of agents as discrete tools, as this exceeds the LLM context window/tool limits (~100 tools max practical limit).
    - Provide a primary `asap_invoke(urn: str, payload: dict)` tool allowing the model to call any discovered agent.
    - Provide an `asap_discover(query: str = "")` tool so the model can search the registry.
    - Provide an optional `--whitelist-urns` CLI flag to expose specific agents dynamically as top-level explicit tools.
- [x] **3.5.3** Async Event Loop & Error Handling
  - **Refinement:** Ensure the server gracefully handles `MarketClient` network latency without blocking. Catch network/resolution errors and return standard MCP Error tool responses (using MCP error string formatting) rather than crashing the Stdio transport.
- [x] **3.5.4** Add pyproject scripts entry (`asap-mcp-server`, requires `[mcp]`)
- [x] **3.5.5** Write tests for MCP server

---

## Task 3.6: Create LlamaIndex integration

- [x] **3.6.1** Create LlamaIndexAsapTool class
  - **File**: `src/asap/integrations/llamaindex.py`
  - **What**: Inherit from or wrap `llama_index.core.tools.FunctionTool` or `BaseTool`. Translate ASAP JSON schema into LlamaIndex's `ToolMetadata` and `fn_schema`.
  - **Why**: Major framework for enterprise RAG and Agent applications.
- [x] **3.6.2** Write tests checking compatibility with LlamaIndex agent loops

---

## Task 3.7: Create SmolAgents integration

- [x] **3.7.1** Create SmolAgentsAsapTool class
  - **File**: `src/asap/integrations/smolagents.py`
  - **What**: Subclass `smolagents.Tool`. Implement `name`, `description`, `inputs` (dictionary defining schema properties), `output_type`, and the `forward()` method mapping to `MarketClient.run`.
  - **Why**: High adoption curve on Hugging Face due to extreme simplicity and code-generation agent performance.
- [x] **3.7.2** Write tests for SmolAgents compatibility

---

## Task 3.8: Create Vercel AI SDK Bridge integration

- [x] **3.8.1** Design Vercel AI SDK Python Adapter
  - **File**: `src/asap/integrations/vercel_ai.py`
  - **What**: Vercel AI SDK is TypeScript/JS-first (`@ai-sdk/core` `tool()`). Provide a Python router extension (e.g., leveraging FastAPI) that serves ASAP agents via an HTTP endpoint. The response format should provide definitions that a Vercel AI frontend can natively interpret as a `tool({ parameters: z.object(...) })`.
  - **Why**: Enables Next.js/React ecosystems to invoke ASAP Python Agents through a standard REST backend adapter.
- [x] **3.8.2** Write documentation for Vercel AI SDK integration usage

---

## Task 3.9: Create integrations package __init__

- [x] **3.9.1** Exports with lazy imports
  - **File**: `src/asap/integrations/__init__.py`
  - **What**: Safely export `LangChainAsapTool`, `CrewAIAsapTool`, `LlamaIndexAsapTool`, `SmolAgentsAsapTool`, etc. Use `__getattr__` module-level lazy loading (PEP 562) or `try/except` to prevent `ModuleNotFoundError` if optional dependencies are missing.

---

## Definition of Done

- [x] Optional dependency groups working (`[mcp]`, `[langchain]`, `[crewai]`, `[llamaindex]`, `[smolagents]`)
- [x] `LangChainAsapTool(urn)` and `CrewAIAsapTool(urn)` generate dynamic Pydantic models
- [x] `LlamaIndexAsapTool`, `SmolAgentsAsapTool`, `PydanticAITool` implemented robustly
- [x] `uvx asap-mcp-server` runs using Stdio, offering `asap_invoke` and `asap_discover`
- [x] Vercel AI SDK integration adapter implemented
- [x] Tests pass for each integration using mock endpoints or mocked registry
