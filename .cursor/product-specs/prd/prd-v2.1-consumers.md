# PRD: ASAP Protocol v2.1.0 — Consumers

> **Product Requirements Document**
>
> **Version**: 2.1.0
> **Created**: 2026-02-22
> **Last Updated**: 2026-02-22

---

## 1. Executive Summary

### 1.1 Purpose

While v2.0.0 focused heavily on Agent Providers (the supply side) adopting the protocol via IssueOps, v2.1.0 focuses entirely on **Consumers** (the demand side). 

This release delivers the tools required for orchestrators (like LangChain, CrewAI) and independent developers to reliably fetch, validate, and execute agents from the Lite Registry using a "Hybrid-First" approach, strongly prioritizing our Python SDK for secure "Handshakes."

### 1.2 Strategic Context

The ASAP Protocol acts as "The Shell, Not the Brain". We provide the standardized communication layer. If consumers find it difficult to connect their "Brains" (LLMs) to our "Shells" (Agents), the marketplace dies.

v2.1.0 eliminates integration friction by providing robust SDK tooling that handles:
1. URN resolution (fetching `manifest.json` from `registry.json`)
2. Cryptographic signature validation (JCS + RFC 8032)
3. Framework-native wrappers (Custom Tools for LangChain/CrewAI)

---

## 2. Goals

| Goal | Metric | Priority |
|------|--------|----------|
| Secure Consumption | 100% of SDK connections auto-validate Ed25519 signatures | P1 |
| DevX Velocity | < 5 lines of code to invoke an agent via ASAP Python SDK | P1 |
| Ecosystem Fit | Out-of-the-box Tool bindings for LangChain and CrewAI | P1 |
| Documentation | Clear guides on "Raw Fetch" vs "SDK Hybrid-First" | P2 |

---

## 3. User Stories

### Independent Developer
> As a **Python developer**, I want to **use `pip install asap-protocol`** so that **I can resolve an agent's URN, validate its trust badge, and `await` a response in 3 lines of code**.

### AI Orchestrator Architect
> As a **developer using CrewAI**, I want to **import an `AsapAgentTool`** so that **my local LLM logic can delegate tasks to ASAP Marketplace agents without writing custom HTTP/WebSocket transports**.

### Strict Security Consumer
> As an **Enterprise consumer**, I want the **ASAP Client to automatically fail if the Ed25519 signature of the manifest has been tampered with**, so that **I don't execute malicious payloads**.

---

## 4. Functional Requirements

### 4.1 Hybrid-First Consumption (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SDK-001 | `asap.client.resolve(urn: str)` fetches the Agent's Manifest from the GitHub Pages Lite Registry. | MUST |
| SDK-002 | `asap.client.run(manifest: Manifest, payload: dict)` orchestrates the WebSocket/HTTP connection automatically. | MUST |
| DOC-001 | Document how to perform Raw Fetches (fetching GitHub pages JSON manually) for non-Python languages, emphasizing transparency. | MUST |

---

### 4.2 Built-in Trust Validation (P1)

| ID | Requirement | Priority |
|----|-------------|----------|
| SEC-001 | Implement `verifyAgentTrust(payload)` in the Consumer SDK that utilizes the existing `asap.crypto.trust.verify_ca_signature` logic. | MUST |
| SEC-002 | `asap.client.resolve` must automatically throw a `SignatureVerificationError` if the manifest's signature does not match its payload (JCS). | MUST |
| SEC-003 | The SDK must embed the ASAP CA Public Key to verify agents with the `Verified` trust level locally. | MUST |
| SEC-004 | **Agent Revocation List**: The SDK must fetch and verify the URN against a centralized `revoked_agents.json` prior to execution. This acts as a lightweight CRL (Certificate Revocation List) to block compromised agents whose local cryptographic signatures are technically valid. | MUST |

---

### 4.3 Framework & Ecosystem Integrations (P1/P2)

The success of ASAP hinges on utility. We must provide zero-friction, native integrations where agents can be consumed instantly as "External Specialists" or "Tools."

#### 4.3.1 The "Pro-Code" Path (Frameworks)

| ID | Requirement | Priority |
|----|-------------|----------|
| INT-001 | **LangChain**: Provide a `LangChainAsapTool(urn: str)` class that inherits from `BaseTool`. It automatically maps the Agent's Pydantic schema to the tool's args_schema. | MUST |
| INT-002 | **CrewAI**: Provide a `CrewAIAsapTool(urn: str)` class compatible with CrewAI's `@tool` decorator or BaseTool implementation. | MUST |
| INT-003 | **PydanticAI**: Since ASAP uses Pydantic schema validation natively, provide native integration bindings for PydanticAI, leveraging its strict typing out-of-the-box. | SHOULD |
| INT-004 | **Microsoft AutoGen**: Provide a `register_asap_function` helper to bind an ASAP Agent as a callable function to an AutoGen `ConversableAgent`, allowing complex multi-agent conversations to delegate tasks to the marketplace. | SHOULD |
| INT-005 | **OpenAI Swarm**: Provide lightweight `agent.functions` mappings so Swarm orchestrators can execute ASAP agents as direct functional calls. | COULD |
| INT-006 | When any LLM invokes an ASAP wrapper/tool, the wrapper must execute the standard ASAP Handshake and return the result synchronously or asynchronously. | MUST |

#### 4.3.2 The "Tooling" Path (Protocols)

| ID | Requirement | Priority |
|----|-------------|----------|
| INT-007 | **Model Context Protocol (MCP)**: Provide an `asap-mcp-server` package exposing ASAP Marketplace agents as MCP Tools. This enables users of desktop clients like Claude Desktop or Cursor IDE to immediately query and execute remote ASAP agents natively. | MUST |

---

### 4.4 Economy & Quotas (P2)

| ID | Requirement | Priority |
|----|-------------|----------|
| ECO-001 | SDK should elegantly handle HTTP 429 Too Many Requests resulting from provider-level rate limiting defined in their `SLASection`. | MUST |
| ECO-002 | While Economy Settlement is deferred to v3.0, the SDK must support passing `Authorization: Bearer <token>` for agents that use proprietary paywalls today. | MUST |

---

## 5. Non-Goals (Out of Scope)

| Feature | Reason | When |
|---------|--------|------|
| Economy Settlement / Built-in Paywalls | We facilitate the connection; if the agent charges globally via Stripe on their end, that is their business today. Protocol-level billing is deferred. | v3.0 |
| Node.js / Go SDKs | We will prioritize Python for v2.1.0 as it commands the AI orchestrator market. Other languages must use the "Raw Fetch" documentation. | TBD |

---

## 6. Technical Considerations

### 6.1 Cryptographic Implementation

Consult `src/asap/crypto/trust.py` for existing server-side logic. The Consumer SDK must use `verify_ca_signature` or equivalent local routines to ensure cryptographic strictness (RFC 8032) without relying on external tutorials that leave margin for error.

### 6.2 Agent Resolution Architecture

```python
# The desired Developer Experience for v2.1.0
import asyncio
from asap.client import MarketClient

async def main():
    client = MarketClient()
    
    # 1. Resolves URN against registry.json
    # 2. Fetches remote manifest
    # 3. Automatically validates Ed25519 signature
    agent = await client.resolve("urn:asap:example:math-agent")
    
    # 4. Executes handshake and task
    result = await agent.run({"operation": "add", "a": 5, "b": 10})
    print(result)

asyncio.run(main())
```

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| SDK Adoption | 50% of active URN pings originate from the official `@asap-protocol` Python SDK. |
| Time to First Call (TTFC) | A developer can copy a snippet from the Landing Page and execute an agent in under 2 minutes. |
| Framework Usage | Evidence of LangChain/CrewAI wrappers deployed in production projects. |

---

## 8. Open Questions

- **Q1**: Should the SDK cache the Lite Registry locally (e.g., in memory for 5 minutes) to avoid pulling the large JSON on every `resolve()` call if a consumer is running a loop?
- **Q2**: Should `CrewAI` and `LangChain` wrappers be packaged in the core `asap-protocol` package, or separated into `asap-langchain` to keep dependencies light?
