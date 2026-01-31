"""Authentication patterns example for ASAP protocol.

This module shows how to configure Bearer token auth, custom token validators,
and the OAuth2 concept (obtain Bearer tokens via OAuth2; ASAP validates Bearer).

Patterns:
    1. Bearer: AuthScheme(schemes=["bearer"]) and token_validator for create_app.
    2. Custom validators: Static map, env-based, or callable(token) -> agent_id | None.
    3. OAuth2 concept: oauth2 dict in AuthScheme for discovery; clients get Bearer via OAuth2.

Run:
    uv run python -m asap.examples.auth_patterns
"""

from __future__ import annotations

import argparse
import os
from typing import Callable, Sequence

from asap.models.entities import AuthScheme, Capability, Endpoint, Manifest, Skill
from asap.models.constants import SUPPORTED_AUTH_SCHEMES
from asap.observability import get_logger
from asap.transport.middleware import BearerTokenValidator
from asap.transport.server import create_app

logger = get_logger(__name__)

DEFAULT_ASAP_ENDPOINT = "http://localhost:8000/asap"
DEFAULT_AGENT_ID = "urn:asap:agent:secured"


def build_manifest_bearer_only(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> Manifest:
    """Build a manifest that requires Bearer token authentication.

    Use with create_app(manifest, token_validator=your_validator).
    Only schemes in SUPPORTED_AUTH_SCHEMES are allowed (e.g. bearer, basic).

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Manifest with auth=AuthScheme(schemes=["bearer"]).
    """
    return Manifest(
        id=DEFAULT_AGENT_ID,
        name="Secured Agent",
        version="0.1.0",
        description="Agent with Bearer token authentication",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="execute", description="Execute tasks")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
        auth=AuthScheme(schemes=["bearer"]),
    )


def build_manifest_oauth2_concept(asap_endpoint: str = DEFAULT_ASAP_ENDPOINT) -> Manifest:
    """Build a manifest with Bearer + OAuth2 discovery (concept).

    ASAP currently validates Bearer tokens only. The oauth2 dict describes
    where clients obtain tokens (authorization_url, token_url, scopes).
    Clients perform OAuth2 flow externally and send the access_token as Bearer.

    Args:
        asap_endpoint: URL where the agent receives ASAP messages.

    Returns:
        Manifest with auth=AuthScheme(schemes=["bearer"], oauth2={...}).
    """
    return Manifest(
        id=DEFAULT_AGENT_ID,
        name="OAuth2-Aware Agent",
        version="0.1.0",
        description="Agent with Bearer auth; clients get tokens via OAuth2",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="execute", description="Execute tasks")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint),
        auth=AuthScheme(
            schemes=["bearer"],
            oauth2={
                "authorization_url": "https://auth.example.com/authorize",
                "token_url": "https://auth.example.com/token",
                "scopes": ["asap:execute", "asap:read"],
            },
        ),
    )


def static_map_validator(token_to_agent: dict[str, str]) -> Callable[[str], str | None]:
    """Build a token validator that maps known tokens to agent IDs.

    Use for demos or small fixed sets. For production, use a secure store or JWT.

    Args:
        token_to_agent: Map from token string to agent URN.

    Returns:
        Callable(token) -> agent_id or None.
    """

    def validate(token: str) -> str | None:
        return token_to_agent.get(token)

    return validate


def env_based_validator(
    env_var: str = "ASAP_DEMO_TOKEN",
    expected_agent_id: str = "urn:asap:agent:demo-client",
) -> Callable[[str], str | None]:
    """Build a token validator that accepts a token from an environment variable.

    Use for testing; avoid in production (env vars can be inspected).

    Args:
        env_var: Environment variable holding the valid token.
        expected_agent_id: Agent ID to return when token matches.

    Returns:
        Callable(token) -> agent_id or None.
    """
    expected_token = os.environ.get(env_var, "")

    def validate(token: str) -> str | None:
        if token and token == expected_token:
            return expected_agent_id
        return None

    return validate


def run_demo() -> None:
    """Demonstrate auth patterns: Bearer manifest, custom validators, OAuth2 concept."""
    # Bearer-only manifest
    manifest_bearer = build_manifest_bearer_only()
    logger.info(
        "asap.auth_patterns.bearer_manifest",
        schemes=manifest_bearer.auth.schemes if manifest_bearer.auth else [],
    )

    # Custom validator: static map
    token_map = {
        "demo-token-123": "urn:asap:agent:client-a",
        "other-token": "urn:asap:agent:client-b",
    }
    validator_static = static_map_validator(token_map)
    bearer_validator = BearerTokenValidator(validator_static)
    agent_id = bearer_validator("demo-token-123")
    logger.info(
        "asap.auth_patterns.static_validator",
        token_preview="demo-token-***",
        agent_id=agent_id,
    )
    assert agent_id == "urn:asap:agent:client-a"
    assert bearer_validator("invalid") is None

    # Custom validator: env-based (no env set -> invalid)
    validator_env = env_based_validator(env_var="ASAP_DEMO_TOKEN")
    assert validator_env("any") is None
    logger.info(
        "asap.auth_patterns.env_validator",
        message="Use ASAP_DEMO_TOKEN to test env-based validator",
    )

    # OAuth2 concept manifest (Bearer + oauth2 discovery)
    manifest_oauth2 = build_manifest_oauth2_concept()
    logger.info(
        "asap.auth_patterns.oauth2_concept",
        schemes=manifest_oauth2.auth.schemes if manifest_oauth2.auth else [],
        oauth2_urls=(
            list(manifest_oauth2.auth.oauth2.keys())
            if manifest_oauth2.auth and manifest_oauth2.auth.oauth2
            else []
        ),
    )

    # Wire app with Bearer auth (no server started; just create_app)
    app = create_app(
        manifest_bearer,
        token_validator=validator_static,
    )
    logger.info(
        "asap.auth_patterns.app_created",
        message="create_app(manifest, token_validator=...) enables Bearer auth",
        supported_schemes=list(SUPPORTED_AUTH_SCHEMES),
    )
    # Reference app so it's not garbage-collected if someone holds the result
    assert app is not None


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the auth patterns demo."""
    parser = argparse.ArgumentParser(
        description="Authentication patterns: Bearer, custom validators, OAuth2 concept."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the auth patterns demo."""
    parse_args(argv)
    run_demo()


if __name__ == "__main__":
    main()
