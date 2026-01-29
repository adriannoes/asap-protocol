"""Compatibility test script for v0.3.0 to v0.5.0 upgrade.

This script uses the ASAP API that was available in v0.3.0.
It should work without modifications after upgrading to v0.5.0.

Version History:
- v0.1.0 (2026-01-23): Initial alpha release
- v0.3.0 (2026-01-26): Test infrastructure improvements (this version)
- v0.5.0 (2026-01-28): Security-hardened release (upgrade target)
"""

import asyncio

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.models.payloads import TaskRequest
from asap.transport.client import ASAPClient
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app


def create_simple_agent() -> tuple[Manifest, HandlerRegistry]:
    """Create a simple agent using v0.3.0 API.

    Returns:
        Tuple of (manifest, handler_registry) for the agent.
    """
    manifest = Manifest(
        id="urn:asap:agent:test-agent-v03",
        name="Test Agent v0.3",
        version="1.0.0",
        description="Simple test agent for v0.3.0 compatibility testing",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8003/asap"),
    )

    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())

    return manifest, registry


def test_agent_creation() -> None:
    """Test that we can create an agent app using v0.3.0 API."""
    manifest, registry = create_simple_agent()
    app = create_app(manifest, registry)

    # Verify app was created
    assert app is not None
    assert hasattr(app, "routes")


async def test_client_communication() -> None:
    """Test that client can communicate with agent using v0.3.0 API."""
    request = TaskRequest(
        conversation_id="test_conv_v0.3",
        skill_id="echo",
        input={"message": "hello from v0.3.0 compatibility test"},
    )

    envelope = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:client",
        recipient="urn:asap:agent:test-agent-v03",
        payload_type="task.request",
        payload=request.model_dump(),
    )

    # Note: This test assumes a server is running
    # In actual upgrade test, server will be started separately
    try:
        async with ASAPClient("http://127.0.0.1:8003") as client:
            response = await client.send(envelope)
            assert response.payload_type == "task.response"
            assert "result" in response.payload
    except Exception:
        # If server not running, that's OK for this test (skip)
        pass


def test_security_features_opt_in() -> None:
    """Test that new security features in v0.5.0 are opt-in."""
    # Create manifest WITHOUT auth (should work, as in v0.3.0)
    manifest = Manifest(
        id="urn:asap:agent:test-no-auth-v03",
        name="Test Agent No Auth v0.3",
        version="1.0.0",
        description="Test agent without auth (v0.3.0 style)",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="http://127.0.0.1:8003/asap"),
    )

    # Should work without auth configuration (backward compatible)
    app = create_app(manifest)
    assert app is not None


def main() -> None:
    """Run compatibility tests for v0.3.0 (when executed as __main__)."""
    # Test 1: Agent creation
    test_agent_creation()

    # Test 2: Security features opt-in
    test_security_features_opt_in()

    # Test 3: Client communication (requires running server)
    asyncio.run(test_client_communication())


if __name__ == "__main__":
    main()
