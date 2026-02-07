# ASAP Protocol: Technology Stack & Architecture Decisions

This document provides a historical and technical rationale for the technology choices made throughout the evolution of the ASAP Protocol, from its core (v1.0) to the Marketplace (v2.0).

> **Goal**: Explain *why* we chose these tools, offering context for future contributors and architects.

---

## 1. Core Protocol (v1.0 - "Foundation")

The foundation required stability, developer experience (DX), and strict correctness.

### 1.1 Language: Python 3.11+
-   **Decision**: **Python**
-   **Rationale**:
    -   **AI Native**: The primary audience for Agentic Protocols are AI engineers, who predominantly use Python.
    -   **Sync/Async**: Python's `asyncio` is mature enough for high-concurrency IO-bound tasks (agents waiting on LLMs).
    -   **Ecosystem**: Unrivaled libraries for LLM integration (LangChain, OpenAI, Pydantic).
-   **Why strict typing?**: We enforce `mypy` strict mode because protocols cannot be ambiguous. Python 3.11+ brings massive performance wins and better type hints.

### 1.2 Data Core: Pydantic v2
-   **Decision**: **Pydantic**
-   **Rationale**:
    -   **Validation as Schema**: It defines the protocol schema (Models) and validator (Runtime) in one place.
    -   **Performance**: v2 is written in Rust, offering near-native serialization speeds.
    -   **JSON Schema**: Auto-generates standard JSON Schemas for interoperability with non-Python agents.

### 1.3 Communication: JSON-RPC 2.0
-   **Decision**: **JSON-RPC** over REST
-   **Rationale**:
    -   **Action-Oriented**: Agents perform *actions* (TaskRequest, TaskCancel), not just resource manipulation (GET/POST).
    -   **Transport Agnostic**: JSON-RPC works equally well over HTTP, WebSockets, or stdio (MCP).
    -   **Standard**: It is a stable, boring standard. Agents don't need creative URL schemes.

### 1.4 API Framework: FastAPI
-   **Decision**: **FastAPI**
-   **Rationale**:
    -   **Native Pydantic**: Seamless integration with our data core.
    -   **Async First**: Built on `Starlette`/`AnyIO`, critical for handling thousands of concurrent agent connections.
    -   **Doc Generation**: Auto-generates OpenAPI specs, helping developers visualize the protocol endpoints.

---

## 2. Identity & Transport (v1.1 - "Connectivity")

Focus shifted to secure, real-time communication.

### 2.1 Authentication: OAuth2 with JWT
-   **Decision**: **OAuth2 (Client Credentials Flow)**
-   **Rationale**:
    -   **Machine-to-Machine**: Agents are headless service accounts. Client Credentials is the standard for M2M.
    -   **Stateless**: JWTs allow signature verification without hitting a database for every request (performance).
    -   **Scopes**: Fine-grained permissions (`task:create`, `agent:read`) baked into the standard.

### 2.2 Real-time: WebSockets
-   **Decision**: **WebSockets**
-   **Rationale**:
    -   **Bi-directional**: Essential for "Interrupts" (Human-in-the-loop stopping an agent) and streaming partial LLM tokens.
    -   **Low Overhead**: Eliminates polling latency for agent-to-agent negotiation.

---

## 3. Trust & Intelligence (v1.2 - "Brain")

We needed to evaluate agent quality and ensure safety.

### 3.1 Evaluations: Hybrid (Native + DeepEval)
-   **Decision**: **Hybrid Approach**
-   **Rationale**:
    -   **Native (Shell)**: For protocol compliance (schema checks, state transitions), we wrote our own `pytest` harness. Third-party tools don't understand our binary wire format.
    -   **DeepEval (Brain)**: For "Intelligence" (Hallucination, Bias), we avoided reinventing the wheel. DeepEval gives us research-backed metrics out of the box.

---

## 4. Web Marketplace (v2.0 - "Product")

The shift from "Protocol" to "Product" required a modern, SEO-friendly web stack.

### 4.1 Frontend: Next.js 15 (App Router)
-   **Decision**: **Next.js** (over Vite/React SPA)
-   **Rationale**:
    -   **SEO**: The Agent Registry must be indexable by Google. Server-Side Rendering (SSR) is non-negotiable here.
    -   **React Server Components (RSC)**: Allows fetching Registry data directly in the component, simplifying the architecture (no client-side effect chains for static data).
    -   **Vercel Ecosystem**: The project infrastructure (monorepo, edge functions) aligns natively with Next.js.

### 4.2 Language: TypeScript
-   **Decision**: **TypeScript** (Strict)
-   **Rationale**:
    -   **Shared Types**: We can generate TypeScript interfaces from the Python Pydantic models (via `datamodel-code-generator`), ensuring the Frontend is always in sync with the Protocol.
    -   **Safety**: Large-scale frontend apps without types are unmaintainable.

### 4.3 Styling: TailwindCSS v4 + Shadcn/UI
-   **Decision**: **Tailwind + Shadcn**
-   **Rationale**:
    -   **Velocity**: Building a "Premium" look with Vanilla CSS takes months. Shadcn provides accessible, high-quality components (Radix primitives) that we can fully customize.
    -   **Modernity**: Tailwind v4 brings compiler performance improvements.
    -   **Standard**: This is currently the effective industry standard for modern React apps.

### 4.4 Authentication (Web): GitHub + WebCrypto (Hybrid)
-   **Decision**: **Hybrid Flow** (Proposed)
-   **Rationale**:
    -   **The Bootstrap Problem**: Developers don't want to use CLI tools to sign up.
    -   **Solution**: "Sign in with GitHub" to create the account ⇒ Browser generates ASAP Protocol keys (WebCrypto API) locally for agent operations. Low friction, high security.

---

## Summary

| Layer | Technology | Key Driver |
|-------|------------|------------|
| **Protocol** | Python 3.11+, Pydantic | Ecosystem, Validation |
| **API** | FastAPI, JSON-RPC | Async correctness, Simplicity |
| **Auth** | OAuth2, JWT | Standard M2M security |
| **Web** | Next.js 15, TypeScript | SEO, Type Safety |
| **UI** | Tailwind, Shadcn | Development Velocity |
