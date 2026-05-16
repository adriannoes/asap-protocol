# WWW-Authenticate ASAP challenge

ASAP-aware HTTP clients can discover the agent manifest when a resource server returns **401 Unauthorized** by advertising an `ASAP` challenge alongside (or after) `Bearer`.

## Header format

```http
WWW-Authenticate: Bearer, ASAP discovery="https://agent.example/.well-known/asap/manifest.json"
```

The `discovery` parameter is a **quoted URL** to the JSON manifest (`GET` that URL). Servers should use HTTPS in production.

## Server: `WWWAuthenticateASAPMiddleware`

`create_app(..., asap_challenge_enabled=True)` registers middleware that, for configured path prefixes (default: `/asap/capability`, `/asap/agent`), appends the ASAP challenge to **HTTP 401** responses so unauthenticated clients can find the manifest.

Per-request override (advanced):

```python
request.state.asap_challenge_discovery_url = "https://other.example/.well-known/asap/manifest.json"
```

## OpenAPI adapter (CHAL-004)

When the upstream OpenAPI API returns **HTTP 401**, `OpenAPIUpstreamHandler` attaches `_www_authenticate_asap` into the `FatalError` details. The JSON-RPC error path strips that internal field from the JSON body and surfaces it as an HTTP **`WWW-Authenticate`** header on the JSON-RPC response (HTTP 200) so ASAP clients can react without scraping the body.

## Python client: `auto_register_on_asap_challenge`

`ASAPClient(..., auto_register_on_asap_challenge=True)` is **opt-in**. On HTTP 401 from `POST /asap`, the client parses `WWW-Authenticate: ASAP`, stores `last_asap_challenge_discovery_url`, and **best-effort** prefetches the manifest into the local cache. It does **not** silently create host keys or complete registration (that still requires your Host identity material).

**Security:** enabling prefetch reduces friction for friendly discovery but increases outbound traffic on auth failures; keep the default `False` unless you trust the peer.

## Interaction with v2.2.1 WebAuthn

Escalation and registration paths that require a **fresh host session** or **WebAuthn** are unchanged: the challenge only helps with **discovery** after a bare 401. Operators still satisfy `identity_fresh_session_config` / WebAuthn policies out-of-band.

## See also

- [Transport layer](../transport.md)
- [Capability escalation](../capabilities/escalation.md)
