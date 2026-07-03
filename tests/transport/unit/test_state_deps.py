"""Unit tests for typed ``app.state`` FastAPI dependencies."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from starlette.requests import Request

from asap.transport._state_deps import rate_limiter, require_identity_limiter, require_state


def _request_for_app(app: FastAPI) -> Request:
    """Return an HTTP request whose ``request.app`` is *app*."""
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "scheme": "http",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": app,
    }
    return Request(scope)


def test_require_state_returns_configured_attribute() -> None:
    app = FastAPI()
    sentinel = object()
    app.state.snapshot_store = sentinel
    request = _request_for_app(app)

    assert require_state(request, "snapshot_store", "missing") is sentinel


def test_require_state_raises_503_when_attribute_missing() -> None:
    app = FastAPI()
    request = _request_for_app(app)

    with pytest.raises(HTTPException) as exc_info:
        require_state(request, "snapshot_store", "Snapshot store not configured")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Snapshot store not configured"


def test_rate_limiter_returns_none_when_unconfigured() -> None:
    app = FastAPI()
    request = _request_for_app(app)

    assert rate_limiter(request) is None


def test_rate_limiter_returns_limiter_when_configured() -> None:
    app = FastAPI()
    limiter = object()
    app.state.limiter = limiter
    request = _request_for_app(app)

    assert rate_limiter(request) is limiter


def test_require_identity_limiter_raises_503_when_unconfigured() -> None:
    app = FastAPI()
    request = _request_for_app(app)

    with pytest.raises(HTTPException) as exc_info:
        require_identity_limiter(request)

    assert exc_info.value.status_code == 503
    assert "identity_limiter" in exc_info.value.detail


def test_require_identity_limiter_returns_limiter_when_configured() -> None:
    app = FastAPI()
    limiter = object()
    app.state.identity_limiter = limiter
    request = _request_for_app(app)

    assert require_identity_limiter(request) is limiter
