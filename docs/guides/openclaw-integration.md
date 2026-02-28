# OpenClaw Integration

This guide describes how to use ASAP Protocol agents with [OpenClaw](https://github.com/openclaw), an autonomous AI agent framework. Integration is available via:

**Compatibility**: OpenClaw (clawskills), Node.js >= 18, ASAP Protocol 0.1+. Python bridge requires `asap-protocol` with optional `[openclaw]` extra.

1. **OpenClaw Skill (Node.js plugin)**: Registers the `asap_invoke` tool so OpenClaw agents can call ASAP agents directly.
2. **Python bridge**: `OpenClawAsapBridge` for hybrid pipelines combining OpenClawClient with MarketClient.

## Discover agents

To find available ASAP agents and their skill IDs, use the **Lite Registry**:

- **Web**: [ASAP Registry](https://asap-protocol.github.io/registry/) (browse agents and copy URNs/skills).
- **JSON**: Default registry URL: `https://asap-protocol.github.io/registry/registry.json` (use `ASAP_REGISTRY_URL` to override).

Each agent lists its URN (e.g. `urn:asap:agent:my-agent`) and `capabilities.skills[].id` (e.g. `web_research`, `summarization`). Use these when calling `asap_invoke` or `run_asap`.

## OpenClaw Skill (Plugin)

### Installation

```bash
npx clawskills@latest install asap-openclaw-skill
```

Or add the package to your OpenClaw plugins directory and configure it.

### Configuration

Enable the tool in `openclaw.json`:

```json5
{
  agents: {
    list: [
      {
        id: "main",
        tools: {
          allow: ["asap_invoke"],
        },
      },
    ],
  },
}
```

### Environment Variables

| Variable          | Description                                                                 |
|-------------------|-----------------------------------------------------------------------------|
| `ASAP_REGISTRY_URL` | Override registry URL (default: `https://asap-protocol.github.io/registry/registry.json`) |
| `ASAP_AUTH_TOKEN`   | Bearer token for agents that require authentication                         |
| `ASAP_REQUEST_TIMEOUT_MS` | Request timeout in ms for registry and agent calls (default: 30000) |

### Usage

Once enabled, your OpenClaw agent can call `asap_invoke` with:

- **urn**: ASAP agent URN (e.g. `urn:asap:agent:my-agent`)
- **skill**: Skill identifier from the agent manifest (e.g. `web_research`, `summarization`)
- **input**: Optional key-value object for the skill input

The tool resolves the URN via the Lite Registry, fetches the agent endpoint, and sends a JSON-RPC `task.request` to the ASAP agent.

## Python Bridge (Hybrid Pipelines)

For Python workflows that combine OpenClaw agents with ASAP agents, use `OpenClawAsapBridge`:

### Installation

```bash
pip install "asap-protocol[openclaw]"
```

### Basic Usage

```python
import asyncio
from asap.integrations import OpenClawAsapBridge, is_error_result

async def main():
    bridge = OpenClawAsapBridge()
    # Optional: custom registry
    # bridge = OpenClawAsapBridge(registry_url="https://my-registry/registry.json")
    result = await bridge.run_asap(
        urn="urn:asap:agent:my-agent",
        skill_id="web_research",
        input_payload={"query": "latest AI news"},
    )
    if is_error_result(result):
        print("Failed:", result)  # result is str
    else:
        print(result)  # result is dict

asyncio.run(main())
```

### List agents (discovery)

To discover agents programmatically without opening the registry in a browser:

```python
agents = await bridge.list_agents()
for a in agents:
    print(f"{a.urn} ({a.name}): skills={a.skill_ids}")
```

### Auto-Skill (First Available)

If you don't know the skill ID, use `run_asap_auto_skill` to invoke the first skill from the agent manifest:

```python
result = await bridge.run_asap_auto_skill(
    urn="urn:asap:agent:my-agent",
    input_payload={"query": "summarize this"},
)
```

### Combined with OpenClawClient

```python
from openclaw_sdk import OpenClawClient
from asap.integrations import OpenClawAsapBridge, is_error_result

async def hybrid_pipeline():
    bridge = OpenClawAsapBridge()
    async with OpenClawClient.connect() as openclaw:
        # Run OpenClaw agent
        oc_result = await openclaw.get_agent("research-bot").execute("Research topic X")
        # Invoke ASAP agent with the result
        asap_result = await bridge.run_asap_auto_skill(
            "urn:asap:agent:summarizer",
            input_payload={"text": oc_result.content},
        )
        return asap_result
```

## Result and error handling

**Python**: `run_asap` and `run_asap_auto_skill` return either a **dict** (success) or a **str** (error message). Use the helper so you don’t rely on string inspection:

```python
from asap.integrations import OpenClawAsapBridge, is_error_result, get_result

result = await bridge.run_asap(urn, skill_id, input_payload)
if is_error_result(result):
    # result is str, e.g. "Error: Agent has no skills; ..."
    handle_error(result)
else:
    # result is dict with the agent output
    use(result)

# Or fail fast: get_result raises ValueError on error
data = get_result(await bridge.run_asap(urn, skill_id, input_payload))
```

**Plugin**: The `asap_invoke` tool returns content with a `"Error: ..."` text on failure.

Both paths can fail when:

- The agent is not found in the registry
- The agent has been revoked
- Signature verification fails
- The agent endpoint returns an error (e.g. 4xx/5xx, timeout)

## Troubleshooting

| Symptom | Cause | What to do |
|--------|--------|------------|
| "Agent not found in registry" | URN not in the registry or wrong registry URL | Check URN at the [Lite Registry](https://asap-protocol.github.io/registry/). Set `ASAP_REGISTRY_URL` if using a custom registry. |
| "Agent has no skills" | Manifest has no `capabilities.skills` | Use an agent that exposes at least one skill, or call `run_asap` with a known `skill_id`. |
| 401 / 403 from agent | Agent requires auth | Set `ASAP_AUTH_TOKEN` (plugin) or pass `auth_token=...` (Python). |
| Timeout or connection errors | Agent endpoint slow or unreachable | Increase timeout if your client supports it; confirm the agent URL in the registry. |
| "invalid signature" / "revoked" | Trust or revocation check failed | Ensure you use the official registry or trust the agent’s manifest; check revocation list if configured. |
