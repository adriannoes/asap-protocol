from unittest.mock import AsyncMock

import pytest
from httpx import Response

from asap.crypto.keys import generate_keypair, public_key_to_base64
from asap.crypto.signing import sign_manifest
from asap.errors import SignatureVerificationError
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.client import ASAPClient


def _sample_manifest() -> Manifest:
    return Manifest(
        id="urn:asap:agent:test-client-signing",
        name="Test Agent",
        version="1.0.0",
        description="Agent for client signing tests",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://example.com/asap"),
    )


@pytest.mark.asyncio
async def test_get_manifest_verify_signatures_success() -> None:
    """ASAPClient verifies signature correctly when valid key is provided."""
    # Setup keys
    private_key, public_key = generate_keypair()
    public_key_b64 = public_key_to_base64(public_key)
    manifest = _sample_manifest()

    # Sign manifest
    signed = sign_manifest(manifest, private_key)
    signed_dict = signed.model_dump()
    # Ensure signed manifest has public_key field populated too (though client ignores it for trust)
    assert signed_dict["public_key"] == public_key_b64

    # Mock HTTP response
    mock_response = AsyncMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = signed_dict
    mock_response.headers = {}

    target_url = "http://agent.example.com/.well-known/asap/manifest.json"

    # Initialize client with trusted key
    async with ASAPClient(
        "http://client.example.com",
        verify_signatures=True,
        trusted_manifest_keys={target_url: public_key_b64},
        require_https=False,
    ) as client:
        # Mock the underlying HTTP client
        client._client.get = AsyncMock(return_value=mock_response)

        # Test
        result = await client.get_manifest(target_url)

        # Verify
        assert result.id == manifest.id
        client._client.get.assert_called_once_with(target_url, timeout=pytest.approx(10.0))


@pytest.mark.asyncio
async def test_get_manifest_verify_signatures_failure_tampering() -> None:
    """ASAPClient raises SignatureVerificationError on tampering."""
    private_key, public_key = generate_keypair()
    public_key_b64 = public_key_to_base64(public_key)
    manifest = _sample_manifest()
    signed = sign_manifest(manifest, private_key)

    # Tamper with the manifest payload
    signed_dict = signed.model_dump()
    signed_dict["manifest"]["name"] = "Tampered Agent"  # Violates signature

    mock_response = AsyncMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = signed_dict
    mock_response.headers = {}

    target_url = "http://agent.example.com/.well-known/asap/manifest.json"

    async with ASAPClient(
        "http://client.example.com",
        verify_signatures=True,
        trusted_manifest_keys={target_url: public_key_b64},
        require_https=False,
    ) as client:
        client._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(SignatureVerificationError) as exc:
            await client.get_manifest(target_url)

        assert "verification failed" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_get_manifest_verify_signatures_no_trusted_key() -> None:
    """ASAPClient raises SignatureVerificationError if no trusted key provided for URL."""
    private_key, _ = generate_keypair()
    manifest = _sample_manifest()
    signed = sign_manifest(manifest, private_key)

    mock_response = AsyncMock(spec=Response)
    mock_response.status_code = 200
    mock_response.json.return_value = signed.model_dump()
    mock_response.headers = {}

    target_url = "http://agent.example.com/.well-known/asap/manifest.json"

    # Trusted key NOT provided for this URL
    async with ASAPClient(
        "http://client.example.com",
        verify_signatures=True,
        trusted_manifest_keys={},
        require_https=False,
    ) as client:
        client._client.get = AsyncMock(return_value=mock_response)

        with pytest.raises(SignatureVerificationError) as exc:
            await client.get_manifest(target_url)

        assert "no trusted public key provided" in str(exc.value)
