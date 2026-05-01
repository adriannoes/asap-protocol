"""Unit tests for OpenAPI → ASAP capability mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asap.adapters.openapi.capability_mapper import (
    OpenAPIExecutionKind,
    OpenAPIOperationContext,
    map_openapi_to_capabilities,
)
from asap.adapters.openapi.spec_loader import load_spec

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "openapi"


def _write_tmp(data: dict[str, Any], name: str) -> Path:
    path = _FIXTURES / f"_tmp_{name}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_get_maps_path_and_query_parameters() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPet",
                    "summary": "Get a pet",
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "verbose",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "integer"}},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "get_path_query")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        c0 = caps[0]
        assert c0.skill.id == "getPet"
        assert c0.operation_id == "getPet"
        assert c0.http_method == "get"
        assert c0.path_template == "/pets/{petId}"
        assert c0.execution_kind == OpenAPIExecutionKind.SYNC
        assert c0.skill.description == "Get a pet"
        inp = c0.skill.input_schema
        assert inp is not None
        props = inp["properties"]
        assert props["petId"]["type"] == "string"
        assert props["petId"]["x-openapi-param-in"] == "path"
        assert props["verbose"]["x-openapi-param-in"] == "query"
        assert inp["required"] == ["petId"]
        out = c0.skill.output_schema
        assert out is not None
        assert out["properties"]["id"]["type"] == "integer"
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_post_merges_json_body_with_allof() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/pets": {
                "post": {
                    "operationId": "createPet",
                    "parameters": [
                        {
                            "name": "dryRun",
                            "in": "query",
                            "schema": {"type": "boolean"},
                        },
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {"name": {"type": "string"}},
                                    "required": ["name"],
                                },
                            },
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"id": {"type": "integer"}},
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "post_body")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        inp = caps[0].skill.input_schema
        assert inp is not None
        assert "allOf" in inp
        assert len(inp["allOf"]) == 2
        param_obj, body_obj = inp["allOf"]
        assert param_obj["properties"]["dryRun"]["x-openapi-param-in"] == "query"
        assert body_obj["properties"]["name"]["type"] == "string"
        assert body_obj["required"] == ["name"]
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_response_resolves_component_schema_ref() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "components": {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
            },
        },
        "paths": {
            "/pets": {
                "get": {
                    "operationId": "listPets",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Pet"},
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "ref_response")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        out = caps[0].skill.output_schema
        assert out is not None
        assert "$ref" not in out
        assert out["properties"]["name"]["type"] == "string"
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_missing_operation_id_uses_method_and_path_fallback() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/pets/{petId}": {
                "get": {
                    "summary": "Implicit id",
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }
    path = _write_tmp(raw, "no_op_id")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].skill.id == "get_pets_petId"
        assert caps[0].operation_id is None
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parameter_reference_from_components() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "components": {
            "parameters": {
                "PetId": {
                    "name": "petId",
                    "in": "path",
                    "required": True,
                    "schema": {"type": "string"},
                },
            },
        },
        "paths": {
            "/pets/{petId}": {
                "get": {
                    "operationId": "getPetRefParam",
                    "parameters": [{"$ref": "#/components/parameters/PetId"}],
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }
    path = _write_tmp(raw, "param_ref")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        inp = caps[0].skill.input_schema
        assert inp is not None
        assert inp["properties"]["petId"]["type"] == "string"
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_openapi_3_1_document() -> None:
    path = _FIXTURES / "minimal-3.1.0.json"
    doc = await load_spec(path)
    caps = map_openapi_to_capabilities(doc)
    assert caps == []


_MULTI_OP_RAW: dict[str, Any] = {
    "openapi": "3.0.3",
    "info": {"title": "T", "version": "1"},
    "paths": {
        "/items": {
            "get": {
                "operationId": "listItems",
                "responses": {"200": {"description": "ok"}},
            },
            "head": {
                "operationId": "listItemsHead",
                "responses": {"200": {"description": "ok"}},
            },
            "post": {
                "operationId": "createItem",
                "responses": {"200": {"description": "ok"}},
            },
        },
        "/items/{id}": {
            "get": {
                "operationId": "getItem",
                "responses": {"200": {"description": "ok"}},
            },
            "delete": {
                "operationId": "deleteItem",
                "responses": {"200": {"description": "ok"}},
            },
        },
    },
}


@pytest.mark.asyncio
async def test_default_capabilities_single_method_keeps_get_operations() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_get")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="GET")
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "getItem"}
        assert all(c.http_method == "get" for c in caps)
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_single_method_post_case_insensitive() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_post")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="post")
        assert [c.skill.id for c in caps] == ["createItem"]
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_single_method_no_match_returns_empty() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_patch")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="patch")
        assert caps == []
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_sequence_get_and_head() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_get_head")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities=["GET", "HEAD"])
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead", "getItem"}
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_sequence_excludes_unlisted_verbs() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_no_delete")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(
            doc,
            default_capabilities=["GET", "HEAD", "POST"],
        )
        ids = {c.skill.id for c in caps}
        assert "deleteItem" not in ids
        assert "createItem" in ids
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_sequence_is_case_insensitive() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_mixed_case")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(
            doc,
            default_capabilities=("get", "HeAd"),
        )
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead", "getItem"}
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_all_includes_every_operation() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_all")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="all")
        assert len(caps) == 5
        assert {c.skill.id for c in caps} == {
            "listItems",
            "listItemsHead",
            "createItem",
            "getItem",
            "deleteItem",
        }
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_default_equals_explicit_all() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_default_all")
    try:
        doc = await load_spec(path)
        assert map_openapi_to_capabilities(doc) == map_openapi_to_capabilities(
            doc,
            default_capabilities="all",
        )
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_all_on_empty_paths() -> None:
    doc = await load_spec(_FIXTURES / "minimal-3.0.3.json")
    assert map_openapi_to_capabilities(doc, default_capabilities="all") == []


@pytest.mark.asyncio
async def test_default_capabilities_callable_filters_by_operation_id() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_callable_id")
    try:
        doc = await load_spec(path)

        def _pred(ctx: OpenAPIOperationContext) -> bool:
            return ctx.operation_id is not None and ctx.operation_id.startswith("list")

        caps = map_openapi_to_capabilities(doc, default_capabilities=_pred)
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead"}
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_callable_filters_by_path_and_method() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_callable_path")
    try:
        doc = await load_spec(path)

        def _pred(ctx: OpenAPIOperationContext) -> bool:
            return ctx.path_template.startswith("/items/") and ctx.http_method == "get"

        caps = map_openapi_to_capabilities(doc, default_capabilities=_pred)
        assert [c.skill.id for c in caps] == ["getItem"]
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_callable_rejects_everything() -> None:
    path = _write_tmp(_MULTI_OP_RAW, "filter_callable_empty")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities=lambda _ctx: False)
        assert caps == []
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_execution_kind_streaming_when_text_event_stream_response() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/events": {
                "get": {
                    "operationId": "subscribe",
                    "responses": {
                        "200": {
                            "description": "sse",
                            "content": {
                                "text/event-stream": {"schema": {"type": "string"}},
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "exec_sse")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.STREAMING
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_execution_kind_async_polling_when_202_and_location_header() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/jobs": {
                "post": {
                    "operationId": "startJob",
                    "responses": {
                        "202": {
                            "description": "Accepted",
                            "headers": {
                                "Location": {"schema": {"type": "string", "format": "uri"}},
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "exec_202")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.ASYNC_POLLING
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_execution_kind_sync_for_typical_json_ok_response() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/items": {
                "get": {
                    "operationId": "listItems",
                    "responses": {
                        "200": {
                            "description": "ok",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            },
        },
    }
    path = _write_tmp(raw, "exec_sync")
    try:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.SYNC
    finally:
        path.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_default_capabilities_invalid_type_raises_type_error() -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/z": {"get": {"operationId": "z", "responses": {"200": {"description": "ok"}}}},
        },
    }
    path = _write_tmp(raw, "bad_filter_type")
    try:
        doc = await load_spec(path)
        with pytest.raises(TypeError, match="default_capabilities"):
            map_openapi_to_capabilities(doc, default_capabilities=object())
    finally:
        path.unlink(missing_ok=True)
