"""Tests for ``WWWAuthenticateASAPMiddleware`` (CHAL-001)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from starlette.requests import Request

from asap.transport.challenge import (
    HTTP_UNAUTHORIZED,
    WWWAuthenticateASAPMiddleware,
    default_manifest_discovery_url,
    format_www_authenticate_asap,
    parse_www_authenticate_asap,
)

if TYPE_CHECKING:
    from asap.models.entities import Manifest


@pytest.fixture
def challenge_app(sample_manifest: Manifest) -> FastAPI:
    """Minimal app with challenge middleware on ``/asap/capability`` prefix."""
    app = FastAPI()

    @app.get("/asap/capability/list")
    async def cap_list() -> JSONResponse:
        return JSONResponse(status_code=HTTP_UNAUTHORIZED, content={"detail": "nope"})

    @app.get("/health")
    async def health() -> JSONResponse:
        return JSONResponse(status_code=HTTP_UNAUTHORIZED, content={"detail": "nope"})

    app.add_middleware(
        WWWAuthenticateASAPMiddleware,
        default_discovery_url="https://agent.example/.well-known/asap/manifest.json",
        path_prefixes=("/asap/capability",),
    )
    return app


def test_format_and_parse_roundtrip() -> None:
    url = "https://ex.test/.well-known/asap/manifest.json"
    header = format_www_authenticate_asap(url)
    assert "ASAP" in header
    assert parse_www_authenticate_asap(header) == url


def test_parse_www_authenticate_returns_none_when_missing() -> None:
    assert parse_www_authenticate_asap(None) is None
    assert parse_www_authenticate_asap("") is None
    assert parse_www_authenticate_asap('Bearer realm="x"') is None
    assert parse_www_authenticate_asap('ASAP realm="x"') is None


def test_default_manifest_discovery_url_builds_wellknown() -> None:
    assert default_manifest_discovery_url("https://api.example/v1/asap").endswith(
        "/.well-known/asap/manifest.json"
    )


def test_default_manifest_discovery_url_invalid_raises() -> None:
    with pytest.raises(ValueError, match="Invalid ASAP endpoint"):
        default_manifest_discovery_url("not-a-url")


def test_challenge_middleware_path_matcher() -> None:
    app = FastAPI()

    @app.get("/x")
    async def x() -> JSONResponse:
        return JSONResponse(status_code=HTTP_UNAUTHORIZED, content={})

    app.add_middleware(
        WWWAuthenticateASAPMiddleware,
        default_discovery_url="https://d.test/m.json",
        path_matcher=lambda path: path.startswith("/x"),
    )
    r = TestClient(app).get("/x")
    assert "ASAP" in r.headers.get("WWW-Authenticate", "")


def test_challenge_middleware_appends_to_existing_www_authenticate() -> None:
    app = FastAPI()

    @app.get("/asap/capability/z")
    async def z() -> JSONResponse:
        resp = JSONResponse(status_code=HTTP_UNAUTHORIZED, content={})
        resp.headers["WWW-Authenticate"] = 'Bearer realm="asap"'
        return resp

    app.add_middleware(
        WWWAuthenticateASAPMiddleware,
        default_discovery_url="https://d.test/m.json",
        path_prefixes=("/asap/capability",),
    )
    www = TestClient(app).get("/asap/capability/z").headers.get("WWW-Authenticate", "")
    assert www.startswith("Bearer")
    assert "ASAP" in www


def test_challenge_middleware_adds_header_on_401(challenge_app: FastAPI) -> None:
    client = TestClient(challenge_app)
    r = client.get("/asap/capability/list")
    assert r.status_code == 401
    www = r.headers.get("WWW-Authenticate", "")
    assert "ASAP" in www
    assert "discovery=" in www


def test_challenge_middleware_skips_unmatched_paths(challenge_app: FastAPI) -> None:
    client = TestClient(challenge_app)
    r = client.get("/health")
    assert r.status_code == 401
    assert "ASAP" not in r.headers.get("WWW-Authenticate", "")


def test_challenge_middleware_applies_to_all_paths_when_no_prefix_configured() -> None:
    app = FastAPI()

    @app.get("/misc/protected")
    async def misc() -> JSONResponse:
        return JSONResponse(status_code=HTTP_UNAUTHORIZED, content={})

    app.add_middleware(
        WWWAuthenticateASAPMiddleware,
        default_discovery_url="https://d.test/m.json",
    )
    r = TestClient(app).get("/misc/protected")
    assert "ASAP" in r.headers.get("WWW-Authenticate", "")


def test_request_state_override_discovery() -> None:
    app = FastAPI()

    @app.get("/asap/capability/x")
    async def x(request: Request) -> JSONResponse:
        request.state.asap_challenge_discovery_url = "https://override.test/m.json"
        return JSONResponse(status_code=401, content={})

    app.add_middleware(
        WWWAuthenticateASAPMiddleware,
        default_discovery_url="https://default.test/m.json",
        path_prefixes=("/asap/capability",),
    )
    r = TestClient(app).get("/asap/capability/x")
    parsed = parse_www_authenticate_asap(r.headers.get("www-authenticate"))
    assert parsed == "https://override.test/m.json"
