# Raw Fetch: Registry and Revocation (Non-Python Consumers)

This document describes how to fetch **registry.json** and **revoked_agents.json** over HTTP without using the Python SDK. Use this to implement your own client in JavaScript, Go, Rust, or any language (DOC-001).

## URLs

| Resource | URL | Notes |
|----------|-----|--------|
| **Lite Registry** | `https://asap-protocol.github.io/registry/registry.json` | Canonical; GitHub Pages. Caching (e.g. 5 min) is recommended (ADR-25). |
| **Revoked agents** | `https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json` | GitHub raw. **Do not cache** — check before every agent run. |

Override URLs via env (Python SDK): `ASAP_REGISTRY_CACHE_TTL`, `ASAP_REVOKED_AGENTS_URL`.

---

## 1. Fetch registry.json

**curl:**

```bash
curl -sS "https://asap-protocol.github.io/registry/registry.json"
```

**JavaScript (fetch):**

```javascript
const res = await fetch('https://asap-protocol.github.io/registry/registry.json');
const registry = await res.json();
// registry.version, registry.updated_at, registry.agents
```

**Schema (root):**

- `version` (string): Schema version, e.g. `"1.0"`.
- `updated_at` (string): ISO 8601 datetime when the registry was last updated.
- `agents` (array): List of agent entries.

**Agent entry (each element of `agents`):**

- `id` (string): Agent URN, e.g. `"urn:asap:agent:my-agent"`.
- `name` (string): Human-readable name.
- `description` (string): Short description.
- `endpoints` (object): Map of endpoint type to URL.
  - `http`: Base URL for ASAP HTTP (e.g. `"https://agent.example.com/asap"`).
  - `ws` (optional): WebSocket URL.
  - `manifest` (optional): Direct manifest URL; if missing, use `{http base}/.well-known/asap/manifest.json`.
- `skills` (array of strings): Skill identifiers.
- `asap_version` (string): Protocol version, e.g. `"1.1.0"`.
- `repository_url`, `documentation_url`, `built_with` (optional strings).
- `verification` (optional): `{ "status": "verified" }` for Verified badge.
- `online_check` (optional boolean): If `false`, UI may skip reachability check.

**Example payload (minimal):**

```json
{
  "version": "1.0",
  "updated_at": "2026-02-27T12:00:00Z",
  "agents": [
    {
      "id": "urn:asap:agent:echo",
      "name": "Echo Agent",
      "description": "Echoes input",
      "endpoints": {
        "http": "https://echo.example.com/asap",
        "manifest": "https://echo.example.com/.well-known/asap/manifest.json"
      },
      "skills": ["echo"],
      "asap_version": "1.1.0"
    }
  ]
}
```

---

## 2. Fetch revoked_agents.json

**curl:**

```bash
curl -sS "https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json"
```

**JavaScript (fetch):**

```javascript
const res = await fetch('https://raw.githubusercontent.com/adriannoes/asap-protocol/main/revoked_agents.json');
const data = await res.json();
// data.revoked, data.version — check if your agent URN is in data.revoked[].urn
```

**Schema:**

- `version` (string): List schema version, e.g. `"1.0"`.
- `revoked` (array): List of revoked entries.
  - Each entry: `urn` (string), `reason` (string), `revoked_at` (string, ISO 8601).

**Example payload:**

```json
{
  "revoked": [
    {
      "urn": "urn:asap:agent:compromised",
      "reason": "compromised",
      "revoked_at": "2026-01-15T12:00:00Z"
    }
  ],
  "version": "1.0"
}
```

Before running a task against an agent, check that its URN is **not** in `revoked[].urn`. If it is, do not call the agent (treat as revoked).

---

## 3. Implementing a minimal client

1. **Resolve URN to endpoint**
   - GET registry URL → parse JSON.
   - Find `agents[]` entry with `id === urn`.
   - Read `endpoints.http` (and optionally `endpoints.manifest` for manifest fetch).

2. **Check revocation**
   - GET revoked_agents URL → parse JSON.
   - If any `revoked[i].urn === urn`, abort (agent revoked).

3. **Optional: fetch manifest**
   - GET `endpoints.manifest` or `{endpoints.http base}/.well-known/asap/manifest.json`.
   - Validate signed manifest if your stack supports Ed25519 (see SDK trust layer).

4. **Send task**
   - POST to `{endpoints.http}/asap` with JSON-RPC 2.0 body: `method: "asap.send"`, `params.envelope` = ASAP envelope (e.g. task.request). See [Transport](transport.md) and [API Reference](api-reference.md).

---

## See also

- [Lite Registry (ADR-15)](../.cursor/product-specs/decision-records/README.md) — design of the static registry.
- [SDK cache strategy (ADR-25)](../.cursor/product-specs/decision-records/04-technology.md) — registry cache TTL; revocation never cached.
- Python SDK: `from asap.client import MarketClient` — resolve, trust, revocation, and run in one flow.
