"""Unit tests for OpenAPI spec loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from openapi_pydantic.v3.v3_0.open_api import OpenAPI as OpenAPI_3_0
from openapi_pydantic.v3.v3_1.open_api import OpenAPI as OpenAPI_3_1
from unittest.mock import AsyncMock

from asap.adapters.openapi.spec_loader import OpenAPISpecError, load_spec

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "openapi"


@pytest.mark.asyncio
async def test_load_spec_from_path_openapi_3_0() -> None:
    path = _FIXTURES / "minimal-3.0.3.json"
    doc = await load_spec(path)
    assert isinstance(doc, OpenAPI_3_0)
    assert doc.openapi == "3.0.3"
    assert doc.info.title == "Fixture API"


@pytest.mark.asyncio
async def test_load_spec_from_path_openapi_3_1() -> None:
    path = _FIXTURES / "minimal-3.1.0.json"
    doc = await load_spec(path)
    assert isinstance(doc, OpenAPI_3_1)
    assert doc.openapi == "3.1.0"


@pytest.mark.asyncio
async def test_load_spec_from_str_path() -> None:
    path = _FIXTURES / "minimal-3.0.3.json"
    doc = await load_spec(str(path))
    assert isinstance(doc, OpenAPI_3_0)


@pytest.mark.asyncio
async def test_load_spec_rejects_openapi_2() -> None:
    bad = {
        "openapi": "2.0",
        "info": {"title": "x", "version": "1"},
        "paths": {},
    }
    path = Path(__file__).resolve().parent / "_tmp_invalid_openapi.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    try:
        with pytest.raises(OpenAPISpecError, match="Unsupported OpenAPI"):
            await load_spec(path)
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_load_spec_missing_openapi_field() -> None:
    path = Path(__file__).resolve().parent / "_tmp_no_version.json"
    path.write_text(
        json.dumps({"info": {"title": "x", "version": "1"}, "paths": {}}),
        encoding="utf-8",
    )
    try:
        with pytest.raises(OpenAPISpecError, match="Missing required 'openapi'"):
            await load_spec(path)
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_load_spec_missing_file() -> None:
    with pytest.raises(OpenAPISpecError, match="not found"):
        await load_spec(_FIXTURES / "does-not-exist.json")


@pytest.mark.asyncio
async def test_load_spec_from_url_with_injected_client() -> None:
    payload: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {"title": "Remote Fixture", "version": "2"},
        "paths": {},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/openapi.json"
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.test") as client:
        doc = await load_spec("https://example.test/openapi.json", http_client=client)

    assert isinstance(doc, OpenAPI_3_0)
    assert doc.info.title == "Remote Fixture"


@pytest.mark.asyncio
async def test_load_spec_url_http_error_wraps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.test") as client:
        with pytest.raises(OpenAPISpecError, match="HTTP 404"):
            await load_spec("https://example.test/missing.json", http_client=client)


@pytest.mark.asyncio
async def test_load_spec_url_connect_error_wraps() -> None:
    req = httpx.Request("GET", "https://example.test/o.json")
    client = AsyncMock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("refused", request=req))
    with pytest.raises(OpenAPISpecError, match="HTTP error"):
        await load_spec("https://example.test/o.json", http_client=client)


@pytest.mark.asyncio
async def test_load_spec_url_non_json_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.test") as client:
        with pytest.raises(OpenAPISpecError, match="did not return JSON"):
            await load_spec("https://example.test/o.json", http_client=client)


@pytest.mark.asyncio
async def test_load_spec_url_json_root_not_object() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://example.test") as client:
        with pytest.raises(OpenAPISpecError, match="root must be a JSON object"):
            await load_spec("https://example.test/o.json", http_client=client)


@pytest.mark.asyncio
async def test_load_spec_openapi_field_must_be_string(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad-version-type.json"
    bad_path.write_text(
        json.dumps({"openapi": 3, "info": {"title": "x", "version": "1"}, "paths": {}}),
        encoding="utf-8",
    )
    with pytest.raises(OpenAPISpecError, match="must be a string"):
        await load_spec(bad_path)


@pytest.mark.asyncio
async def test_load_spec_invalid_document_raises(tmp_path: Path) -> None:
    bad_path = tmp_path / "invalid-doc.json"
    bad_path.write_text(
        json.dumps({"openapi": "3.0.3", "info": [], "paths": {}}),
        encoding="utf-8",
    )
    with pytest.raises(OpenAPISpecError, match="Invalid OpenAPI"):
        await load_spec(bad_path)


@pytest.mark.asyncio
async def test_load_spec_file_invalid_json(tmp_path: Path) -> None:
    bad_path = tmp_path / "broken.json"
    bad_path.write_text("{not json", encoding="utf-8")
    with pytest.raises(OpenAPISpecError, match="not valid JSON"):
        await load_spec(bad_path)


@pytest.mark.asyncio
async def test_load_spec_file_root_not_object(tmp_path: Path) -> None:
    bad_path = tmp_path / "array-root.json"
    bad_path.write_text(json.dumps(["x"]), encoding="utf-8")
    with pytest.raises(OpenAPISpecError, match="root must be a JSON object"):
        await load_spec(bad_path)


@pytest.mark.asyncio
async def test_load_spec_file_read_os_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "unreadable.json"
    target.write_text(
        json.dumps({"openapi": "3.0.3", "info": {"title": "x", "version": "1"}, "paths": {}}),
        encoding="utf-8",
    )
    real_read = Path.read_text

    def patched_read(self: Path, *a: Any, **kw: Any) -> str:
        if self.resolve() == target.resolve():
            raise OSError("permission denied")
        return real_read(self, *a, **kw)

    monkeypatch.setattr(Path, "read_text", patched_read)
    with pytest.raises(OpenAPISpecError, match="Cannot read"):
        await load_spec(target)


@pytest.mark.asyncio
async def test_load_spec_url_without_client_opens_temporary_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from asap.adapters.openapi import spec_loader as spec_loader_mod

    payload = {"openapi": "3.0.3", "info": {"title": "T", "version": "1"}, "paths": {}}
    instances: list[Any] = []
    real_async_client = spec_loader_mod.httpx.AsyncClient

    class _CapturingClient:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            instances.append(kwargs)
            self._inner = real_async_client(
                transport=httpx.MockTransport(
                    lambda _r: httpx.Response(200, json=payload),
                ),
                **kwargs,
            )

        async def __aenter__(self) -> httpx.AsyncClient:
            return await self._inner.__aenter__()

        async def __aexit__(self, *exc: Any) -> bool | None:
            return await self._inner.__aexit__(*exc)

    monkeypatch.setattr(
        "asap.adapters.openapi.spec_loader.httpx.AsyncClient",
        _CapturingClient,
    )
    doc = await load_spec("https://remote.example/openapi.json")
    assert doc.openapi == "3.0.3"
    assert instances and instances[0].get("follow_redirects") is True
