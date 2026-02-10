"""Secure agent example: OAuth2 server and client with Custom Claims (v1.1).

Copy-paste ready example showing:
- ASAP server with OAuth2Config and OAuth2Middleware
- Environment variables: ASAP_AUTH_CUSTOM_CLAIM, ASAP_AUTH_ISSUER, ASAP_AUTH_AUDIENCE,
  ASAP_AUTH_JWKS_URI (or OIDC discovery from ASAP_AUTH_ISSUER)
- Client usage with OAuth2ClientCredentials: get token, send request with Bearer

Run server (requires JWKS endpoint and env vars):
    ASAP_AUTH_JWKS_URI=https://your-tenant.auth0.com/.well-known/jwks.json \\
    ASAP_AUTH_CUSTOM_CLAIM=https://asap.ai/agent_id \\
    uv run python -m asap.examples.secure_agent --server --port 8000

Run client (requires token endpoint and credentials):
    ASAP_OAUTH2_CLIENT_ID=... ASAP_OAUTH2_CLIENT_SECRET=... \\
    ASAP_OAUTH2_TOKEN_URL=https://your-tenant.auth0.com/oauth/token \\
    uv run python -m asap.examples.secure_agent --client --agent-url http://127.0.0.1:8000

See docs/security/v1.1-security-model.md for Custom Claims and IdP setup.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import httpx

from asap.auth import OAuth2Config
from asap.auth.oauth2 import OAuth2ClientCredentials
from asap.auth.oidc import OIDCDiscovery
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.ids import generate_id
from asap.models.payloads import TaskRequest
from asap.observability import get_logger
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

logger = get_logger(__name__)

DEFAULT_AGENT_ID = "urn:asap:agent:secure-agent"
DEFAULT_ASAP_ENDPOINT = "http://127.0.0.1:8000/asap"

# Server env vars
ENV_JWKS_URI = "ASAP_AUTH_JWKS_URI"
ENV_ISSUER = "ASAP_AUTH_ISSUER"
ENV_CUSTOM_CLAIM = "ASAP_AUTH_CUSTOM_CLAIM"
ENV_AUDIENCE = "ASAP_AUTH_AUDIENCE"
# Client env vars
ENV_CLIENT_ID = "ASAP_OAUTH2_CLIENT_ID"
ENV_CLIENT_SECRET = "ASAP_OAUTH2_CLIENT_SECRET"
ENV_TOKEN_URL = "ASAP_OAUTH2_TOKEN_URL"


def _get_jwks_uri() -> str | None:
    """Resolve JWKS URI from ASAP_AUTH_JWKS_URI or OIDC discovery from ASAP_AUTH_ISSUER."""
    jwks = os.environ.get(ENV_JWKS_URI)
    if jwks:
        return jwks
    issuer = os.environ.get(ENV_ISSUER)
    if not issuer:
        return None

    async def discover() -> str | None:
        discovery = OIDCDiscovery(issuer_url=issuer)
        config = await discovery.discover()
        return config.jwks_uri

    try:
        # If there's already a running loop (Jupyter, async framework), use it.
        asyncio.get_running_loop()
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, discover()).result()
    except RuntimeError:
        # No running loop — safe to use asyncio.run().
        return asyncio.run(discover())


def run_server(host: str, port: int) -> None:
    """Run ASAP server with OAuth2 protection."""
    jwks_uri = _get_jwks_uri()
    if not jwks_uri:
        logger.error(
            "secure_agent.server.missing_config",
            message=(
                f"Set {ENV_JWKS_URI} or {ENV_ISSUER} (for OIDC discovery) to run the server. "
                "See docs/security/v1.1-security-model.md"
            ),
        )
        sys.exit(1)

    base = f"http://{host}:{port}"
    manifest = Manifest(
        id=DEFAULT_AGENT_ID,
        name="Secure Agent",
        version="1.0.0",
        description="Agent protected with OAuth2 and Custom Claims (v1.1)",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo with OAuth2")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=f"{base}/asap"),
    )

    custom_claim = os.environ.get(ENV_CUSTOM_CLAIM)
    oauth2_config = OAuth2Config(
        jwks_uri=jwks_uri,
        manifest_id=manifest.id,
        custom_claim=custom_claim or None,
    )

    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())
    app = create_app(manifest, registry=registry, oauth2_config=oauth2_config)

    import uvicorn

    uvicorn.run(app, host=host, port=port)


async def run_client(agent_url: str) -> None:
    """Run client: get OAuth2 token, send TaskRequest to secure agent."""
    client_id = os.environ.get(ENV_CLIENT_ID)
    client_secret = os.environ.get(ENV_CLIENT_SECRET)
    token_url = os.environ.get(ENV_TOKEN_URL)
    if not all((client_id, client_secret, token_url)):
        logger.error(
            "secure_agent.client.missing_config",
            message=f"Set {ENV_CLIENT_ID}, {ENV_CLIENT_SECRET}, and {ENV_TOKEN_URL} to run the client.",
        )
        sys.exit(1)
    assert client_id is not None and client_secret is not None and token_url is not None

    oauth2 = OAuth2ClientCredentials(
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )
    token = await oauth2.get_access_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"{token.token_type} {token.access_token}",
    }

    request = TaskRequest(
        conversation_id=generate_id(),
        skill_id="echo",
        input={"message": "hello from secure client"},
    )
    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:secure-client",
        recipient=DEFAULT_AGENT_ID,
        payload_type="task.request",
        payload=request.model_dump(),
    )

    json_rpc_body = {
        "jsonrpc": "2.0",
        "method": "asap/deliver",
        "params": {"envelope": envelope.model_dump(mode="json"), "idempotency_key": generate_id()},
        "id": "req-1",
    }
    asap_endpoint = agent_url.rstrip("/") + "/asap"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(asap_endpoint, headers=headers, json=json_rpc_body)
        response.raise_for_status()
        rpc_response = response.json()
        if "result" in rpc_response:
            result_env = rpc_response["result"].get("envelope")
            if result_env:
                response_payload = result_env.get("payload", {})
                logger.info("secure_agent.client.response", payload=response_payload)
                print("Response payload:", json.dumps(response_payload, indent=2))
            else:
                print("Response:", json.dumps(rpc_response["result"], indent=2))
        else:
            print("Error:", json.dumps(rpc_response, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Secure agent example (OAuth2 server + client with Custom Claims)"
    )
    parser.add_argument("--server", action="store_true", help="Run the OAuth2-protected server")
    parser.add_argument("--client", action="store_true", help="Run the OAuth2 client")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument(
        "--agent-url",
        type=str,
        default="http://127.0.0.1:8000",
        help="Agent base URL for client (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Server bind host (default: 127.0.0.1)"
    )
    args = parser.parse_args()

    if args.server:
        run_server(args.host, args.port)
    elif args.client:
        asyncio.run(run_client(args.agent_url))
    else:
        parser.print_help()
        print(
            "\nExample: start server with JWKS/issuer set, then run client with "
            "ASAP_OAUTH2_CLIENT_ID, ASAP_OAUTH2_CLIENT_SECRET, ASAP_OAUTH2_TOKEN_URL."
        )
        sys.exit(0)


if __name__ == "__main__":
    main()
