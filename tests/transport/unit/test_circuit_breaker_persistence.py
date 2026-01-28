import asyncio
import httpx
import pytest
from asap.transport.client import ASAPClient, RetryConfig
from asap.models.envelope import Envelope
from asap.transport.circuit_breaker import get_registry


@pytest.mark.asyncio
async def test_circuit_breaker_persistence():
    """Verify that circuit breaker state persists across different client instances."""

    # Clear registry to start fresh
    get_registry().clear()

    # Simulate a failing transport (500 Error)
    class FailingTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(500, content="Internal Server Error")

    config = RetryConfig(
        max_retries=1,  # Fast fail
        circuit_breaker_enabled=True,
        circuit_breaker_threshold=2,  # Should open after 2 failures
    )

    base_url = "http://localhost:8000"

    # Create a dummy envelope
    env = Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:sender",
        recipient="urn:asap:agent:receiver",
        payload_type="test",
        payload={},
    )

    failing_transport = FailingTransport()

    # Request 1: Fail
    try:
        async with ASAPClient(base_url, transport=failing_transport, retry_config=config) as client:
            await client.send(env)
    except Exception:
        pass

    # Request 2: Fail (Should trip breaker after this)
    try:
        async with ASAPClient(base_url, transport=failing_transport, retry_config=config) as client:
            await client.send(env)
    except Exception:
        pass

    # Request 3: Should fail with CircuitOpenError immediately
    # We use a NEW client instance to prove persistence
    with pytest.raises(Exception) as excinfo:
        async with ASAPClient(base_url, transport=failing_transport, retry_config=config) as client:
            await client.send(env)

    # Verify it was a CircuitOpenError (or wrapper)
    # Note: ASAPClient raises ASAPConnectionError wrapping underlying errors,
    # lets check the logs or the exception chain if accessible,
    # but ASAPClient logic raises CircuitOpenError *before* sending if open.
    from asap.errors import CircuitOpenError

    assert isinstance(excinfo.value, CircuitOpenError) or isinstance(
        excinfo.value.__cause__, CircuitOpenError
    )


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker_persistence())
