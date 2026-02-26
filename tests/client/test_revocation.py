"""Unit tests for asap.client.revocation module."""

import httpx
import pytest

from asap.client.revocation import RevokedAgentsList, is_revoked


def test_revoked_agents_list_parses_valid_json() -> None:
    """RevokedAgentsList.model_validate_json parses valid JSON."""
    json_str = '{"revoked": [{"urn": "urn:asap:agent:x", "reason": "compromised", "revoked_at": "2025-01-01T00:00:00Z"}], "version": "1.0"}'
    parsed = RevokedAgentsList.model_validate_json(json_str)
    assert len(parsed.revoked) == 1
    assert parsed.revoked[0].urn == "urn:asap:agent:x"
    assert parsed.revoked[0].reason == "compromised"
    assert parsed.version == "1.0"


def test_revoked_agents_list_empty() -> None:
    """RevokedAgentsList accepts empty revoked list."""
    parsed = RevokedAgentsList.model_validate({"revoked": [], "version": "1.0"})
    assert parsed.revoked == []
    assert parsed.version == "1.0"


@pytest.mark.asyncio
async def test_is_revoked_empty_list_returns_false() -> None:
    """Empty revoked list returns False for any URN."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"revoked": [], "version": "1.0"})

    result = await is_revoked(
        "urn:asap:agent:any",
        revoked_url="https://example.com/revoked.json",
        transport=httpx.MockTransport(mock_handler),
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_revoked_urn_in_list_returns_true() -> None:
    """URN in revoked list returns True."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "revoked": [
                    {
                        "urn": "urn:asap:agent:revoked-one",
                        "reason": "compromised",
                        "revoked_at": "2025-01-15T12:00:00Z",
                    }
                ],
                "version": "1.0",
            },
        )

    result = await is_revoked(
        "urn:asap:agent:revoked-one",
        revoked_url="https://example.com/revoked.json",
        transport=httpx.MockTransport(mock_handler),
    )
    assert result is True


@pytest.mark.asyncio
async def test_is_revoked_urn_not_in_list_returns_false() -> None:
    """URN not in revoked list returns False."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "revoked": [
                    {
                        "urn": "urn:asap:agent:other",
                        "reason": "compromised",
                        "revoked_at": "2025-01-15T12:00:00Z",
                    }
                ],
                "version": "1.0",
            },
        )

    result = await is_revoked(
        "urn:asap:agent:not-revoked",
        revoked_url="https://example.com/revoked.json",
        transport=httpx.MockTransport(mock_handler),
    )
    assert result is False


@pytest.mark.asyncio
async def test_is_revoked_http_error_raises() -> None:
    """HTTP error (e.g. 404, 500) propagates."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "not found"})

    with pytest.raises(httpx.HTTPStatusError):
        await is_revoked(
            "urn:asap:agent:x",
            revoked_url="https://example.com/revoked.json",
            transport=httpx.MockTransport(mock_handler),
        )


@pytest.mark.asyncio
async def test_is_revoked_invalid_json_raises() -> None:
    """Invalid JSON response raises validation error."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not valid json {{{")

    with pytest.raises(ValueError):
        await is_revoked(
            "urn:asap:agent:x",
            revoked_url="https://example.com/revoked.json",
            transport=httpx.MockTransport(mock_handler),
        )
