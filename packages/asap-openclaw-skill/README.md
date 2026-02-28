# asap-openclaw-skill

OpenClaw skill that registers the `asap_invoke` tool, allowing OpenClaw agents to invoke [ASAP Protocol](https://github.com/adriannoes/asap-protocol) agents by URN.

**Discover agents**: Browse the [ASAP Lite Registry](https://asap-protocol.github.io/registry/) to find agent URNs and skill IDs before calling `asap_invoke`.

**Compatibility**: OpenClaw (clawskills), Node.js >= 18, ASAP Protocol 0.1+.

## Installation

```bash
npx clawskills@latest install asap-openclaw-skill
```

Or manually add to your OpenClaw plugins and enable the tool:

```json5
// openclaw.json
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

## Configuration

| Environment Variable | Description |
|---------------------|-------------|
| `ASAP_REGISTRY_URL` | Override registry URL (default: `https://asap-protocol.github.io/registry/registry.json`) |
| `ASAP_AUTH_TOKEN`   | Bearer token for agents that require authentication |
| `ASAP_REQUEST_TIMEOUT_MS` | Request timeout in milliseconds for registry and agent calls (default: 30000) |

## Usage

Once enabled, your OpenClaw agent can call `asap_invoke` with:

- **urn**: ASAP agent URN (e.g. `urn:asap:agent:my-agent`)
- **skill**: Skill identifier from the agent manifest (e.g. `web_research`, `summarization`)
- **input**: Optional key-value object for the skill input

The tool resolves the URN via the Lite Registry, fetches the agent endpoint, and sends a JSON-RPC `task.request` to the ASAP agent.

## Troubleshooting

| Issue | What to do |
|-------|------------|
| "Agent not found in registry" | Check the URN at the [Lite Registry](https://asap-protocol.github.io/registry/). Set `ASAP_REGISTRY_URL` if using a custom registry. |
| 401 / 403 from agent | Set `ASAP_AUTH_TOKEN` to a valid bearer token for the agent. |
| Timeout or connection errors | The agent endpoint may be slow or down; verify the agent URL in the registry. |

For full integration details and Python bridge usage, see the [OpenClaw Integration Guide](https://github.com/adriannoes/asap-protocol/blob/main/docs/guides/openclaw-integration.md) in the ASAP Protocol repo.

## License

Apache-2.0
