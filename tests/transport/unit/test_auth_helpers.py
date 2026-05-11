"""Tests for shared transport authentication helpers."""

from __future__ import annotations

from starlette.requests import Request

from asap.transport._auth_helpers import bearer_token_from_request


def _request_with_authorization(value: str | None) -> Request:
    """Build a minimal HTTP request carrying an optional Authorization header."""
    headers: list[tuple[bytes, bytes]] = []
    if value is not None:
        headers.append((b"authorization", value.encode()))
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
        }
    )


def test_bearer_token_from_request_extracts_token() -> None:
    request = _request_with_authorization("Bearer abc.def")

    assert bearer_token_from_request(request) == "abc.def"


def test_bearer_token_from_request_strips_token_whitespace() -> None:
    request = _request_with_authorization("Bearer   abc.def   ")

    assert bearer_token_from_request(request) == "abc.def"


def test_bearer_token_from_request_missing_or_empty_returns_none() -> None:
    assert bearer_token_from_request(_request_with_authorization(None)) is None
    assert bearer_token_from_request(_request_with_authorization("Bearer ")) is None
    assert bearer_token_from_request(_request_with_authorization("Bearer   ")) is None


def test_bearer_token_from_request_non_bearer_returns_none() -> None:
    request = _request_with_authorization("Basic abc.def")

    assert bearer_token_from_request(request) is None
