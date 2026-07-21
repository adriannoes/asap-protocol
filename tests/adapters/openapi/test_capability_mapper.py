"""Unit tests for OpenAPI → ASAP capability mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from asap.adapters.openapi.capability_mapper import (
    OpenAPIExecutionKind,
    OpenAPIOperationContext,
    _SchemaResolver,
    map_openapi_to_capabilities,
)
from asap.adapters.openapi.spec_loader import load_spec

from tests.adapters.openapi.conftest import tmp_openapi_spec

_FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "openapi"


@pytest.mark.asyncio
async def test_get_maps_path_and_query_parameters(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "get_path_query") as path:
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


@pytest.mark.asyncio
async def test_post_merges_json_body_with_allof(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "post_body") as path:
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


@pytest.mark.asyncio
async def test_response_resolves_component_schema_ref(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "ref_response") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        out = caps[0].skill.output_schema
        assert out is not None
        assert "$ref" not in out
        assert out["properties"]["name"]["type"] == "string"


@pytest.mark.asyncio
async def test_missing_operation_id_uses_method_and_path_fallback(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "no_op_id") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].skill.id == "get_pets_petId"
        assert caps[0].operation_id is None


@pytest.mark.asyncio
async def test_parameter_reference_from_components(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "param_ref") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        inp = caps[0].skill.input_schema
        assert inp is not None
        assert inp["properties"]["petId"]["type"] == "string"


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
async def test_default_capabilities_single_method_keeps_get_operations(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_get") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="GET")
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "getItem"}
        assert all(c.http_method == "get" for c in caps)


@pytest.mark.asyncio
async def test_default_capabilities_single_method_post_case_insensitive(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_post") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="post")
        assert [c.skill.id for c in caps] == ["createItem"]


@pytest.mark.asyncio
async def test_default_capabilities_single_method_no_match_returns_empty(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_patch") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities="patch")
        assert caps == []


@pytest.mark.asyncio
async def test_default_capabilities_sequence_get_and_head(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_get_head") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities=["GET", "HEAD"])
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead", "getItem"}


@pytest.mark.asyncio
async def test_default_capabilities_sequence_excludes_unlisted_verbs(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_no_delete") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(
            doc,
            default_capabilities=["GET", "HEAD", "POST"],
        )
        ids = {c.skill.id for c in caps}
        assert "deleteItem" not in ids
        assert "createItem" in ids


@pytest.mark.asyncio
async def test_default_capabilities_sequence_is_case_insensitive(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_mixed_case") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(
            doc,
            default_capabilities=("get", "HeAd"),
        )
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead", "getItem"}


@pytest.mark.asyncio
async def test_default_capabilities_all_includes_every_operation(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_all") as path:
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


@pytest.mark.asyncio
async def test_default_capabilities_default_equals_explicit_all(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_default_all") as path:
        doc = await load_spec(path)
        assert map_openapi_to_capabilities(doc) == map_openapi_to_capabilities(
            doc,
            default_capabilities="all",
        )


@pytest.mark.asyncio
async def test_default_capabilities_all_on_empty_paths() -> None:
    doc = await load_spec(_FIXTURES / "minimal-3.0.3.json")
    assert map_openapi_to_capabilities(doc, default_capabilities="all") == []


@pytest.mark.asyncio
async def test_default_capabilities_callable_filters_by_operation_id(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_callable_id") as path:
        doc = await load_spec(path)

        def _pred(ctx: OpenAPIOperationContext) -> bool:
            return ctx.operation_id is not None and ctx.operation_id.startswith("list")

        caps = map_openapi_to_capabilities(doc, default_capabilities=_pred)
        ids = {c.skill.id for c in caps}
        assert ids == {"listItems", "listItemsHead"}


@pytest.mark.asyncio
async def test_default_capabilities_callable_filters_by_path_and_method(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_callable_path") as path:
        doc = await load_spec(path)

        def _pred(ctx: OpenAPIOperationContext) -> bool:
            return ctx.path_template.startswith("/items/") and ctx.http_method == "get"

        caps = map_openapi_to_capabilities(doc, default_capabilities=_pred)
        assert [c.skill.id for c in caps] == ["getItem"]


@pytest.mark.asyncio
async def test_default_capabilities_callable_rejects_everything(tmp_path: Path) -> None:
    with tmp_openapi_spec(tmp_path, _MULTI_OP_RAW, "filter_callable_empty") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc, default_capabilities=lambda _ctx: False)
        assert caps == []


@pytest.mark.asyncio
async def test_execution_kind_streaming_when_text_event_stream_response(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "exec_sse") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.STREAMING


@pytest.mark.asyncio
async def test_execution_kind_sync_when_202_and_location_header_after_polling_prune(
    tmp_path: Path,
) -> None:
    """202 + Location classifies as SYNC after the ASYNC_POLLING prune.

    The ``async_polling`` variant was dead metadata (no production consumer); a
    ``202`` + ``Location`` operation now falls through to ``SYNC`` until a
    polling handler is wired.
    """
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
    assert not hasattr(OpenAPIExecutionKind, "ASYNC_POLLING")
    with tmp_openapi_spec(tmp_path, raw, "exec_202") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.SYNC


@pytest.mark.asyncio
async def test_execution_kind_sync_for_typical_json_ok_response(tmp_path: Path) -> None:
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
    with tmp_openapi_spec(tmp_path, raw, "exec_sync") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].execution_kind == OpenAPIExecutionKind.SYNC


@pytest.mark.asyncio
async def test_default_capabilities_invalid_type_raises_type_error(tmp_path: Path) -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/z": {"get": {"operationId": "z", "responses": {"200": {"description": "ok"}}}},
        },
    }
    with tmp_openapi_spec(tmp_path, raw, "bad_filter_type") as path:
        doc = await load_spec(path)
        with pytest.raises(TypeError, match="default_capabilities"):
            map_openapi_to_capabilities(doc, default_capabilities=object())


def test_expand_refs_depth_returns_early_without_error_on_deep_trees() -> None:
    """Regression: pathological schema-shape dicts cannot recurse deeper than depth 51."""
    resolver = _SchemaResolver({})
    root: dict[str, Any] = {"top": 1}
    cur = root
    for _ in range(52):
        nxt: dict[str, Any] = {}
        cur["child"] = nxt
        cur = nxt
    cur["leaf"] = 2
    result = resolver.expand_refs(root, frozenset())
    assert result["top"] == 1
    assert isinstance(result["child"], dict)


def test_expand_refs_cyclic_schema_keeps_ref() -> None:
    raw = {
        "A": {"properties": {"b": {"$ref": "#/components/schemas/B"}}},
        "B": {"properties": {"a": {"$ref": "#/components/schemas/A"}}},
    }
    resolver = _SchemaResolver(raw)
    expanded = resolver.expand_refs({"$ref": "#/components/schemas/A"}, frozenset())
    assert expanded["properties"]["b"]["properties"]["a"] == {"$ref": "#/components/schemas/A"}


def test_expand_refs_expands_nested_lists() -> None:
    resolver = _SchemaResolver({"Item": {"type": "string"}})
    node = {"items": [{"$ref": "#/components/schemas/Item"}]}
    expanded = resolver.expand_refs(node, frozenset())
    assert expanded["items"][0]["type"] == "string"


def test_fallback_capability_name_root_path() -> None:
    from asap.adapters.openapi.capability_mapper import _fallback_capability_name

    assert _fallback_capability_name("GET", "/") == "get_rootpath"


def test_detect_openapi_execution_kind_sync_default() -> None:
    from asap.adapters.openapi.capability_mapper import detect_openapi_execution_kind

    class _Op:
        responses = {"200": object()}

    assert detect_openapi_execution_kind(_Op(), None).value == "sync"


@pytest.mark.asyncio
async def test_operation_id_whitespace_only_uses_fallback_name(tmp_path: Path) -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/items": {
                "get": {
                    "operationId": "   ",
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }
    with tmp_openapi_spec(tmp_path, raw, "ws_op_id") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        assert caps[0].skill.id == "get_items"


@pytest.mark.asyncio
async def test_merge_parameters_operation_overrides_path_item(tmp_path: Path) -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/items/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "description": "path-level"},
                    }
                ],
                "get": {
                    "operationId": "getItem",
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer", "description": "op-level"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }
    with tmp_openapi_spec(tmp_path, raw, "param_override") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        props = caps[0].skill.input_schema["properties"]
        assert props["id"]["type"] == "integer"


@pytest.mark.asyncio
async def test_parameter_schema_via_content_application_json(tmp_path: Path) -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "paths": {
            "/search": {
                "get": {
                    "operationId": "search",
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"term": {"type": "string"}},
                                    },
                                }
                            },
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                },
            },
        },
    }
    with tmp_openapi_spec(tmp_path, raw, "param_content_json") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        q_schema = caps[0].skill.input_schema["properties"]["q"]
        assert q_schema["type"] == "object"


@pytest.mark.asyncio
async def test_request_body_and_response_via_components_ref(tmp_path: Path) -> None:
    raw = {
        "openapi": "3.0.3",
        "info": {"title": "T", "version": "1"},
        "components": {
            "schemas": {"Widget": {"type": "object", "properties": {"id": {"type": "string"}}}},
            "requestBodies": {
                "WidgetBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Widget"},
                        }
                    }
                }
            },
            "responses": {
                "WidgetResp": {
                    "description": "ok",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Widget"},
                        }
                    },
                }
            },
        },
        "paths": {
            "/widgets": {
                "post": {
                    "operationId": "createWidget",
                    "requestBody": {"$ref": "#/components/requestBodies/WidgetBody"},
                    "responses": {"200": {"$ref": "#/components/responses/WidgetResp"}},
                },
            },
        },
    }
    with tmp_openapi_spec(tmp_path, raw, "components_ref") as path:
        doc = await load_spec(path)
        caps = map_openapi_to_capabilities(doc)
        assert len(caps) == 1
        inp = caps[0].skill.input_schema
        assert inp is not None
        out = caps[0].skill.output_schema
        assert out is not None
