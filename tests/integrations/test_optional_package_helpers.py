"""Tests for optional integration helper functions."""

from __future__ import annotations

import json
from importlib import import_module
from typing import Any

import pytest

from asap.models.entities import Capability, Endpoint, Manifest, Skill


def _manifest_minimal(
    *,
    skills: list[Skill],
    description: str = "Agent",
) -> Manifest:
    return Manifest(
        id="urn:asap:agent:fixture",
        name="Fixture",
        version="1.0.0",
        description=description,
        capabilities=Capability(
            asap_version="0.1",
            skills=skills,
            state_persistence=False,
        ),
        endpoints=Endpoint(asap="https://agent.example/asap"),
    )


@pytest.mark.parametrize(
    "integration_module",
    [
        pytest.param("crewai", id="crewai"),
        pytest.param("langchain", id="langchain"),
        pytest.param("llamaindex", id="llamaindex"),
    ],
)
def test_json_schema_helpers_cover_primitive_types(integration_module: str) -> None:
    if integration_module == "crewai":
        pytest.importorskip("crewai")
        mod_name = "asap.integrations.crewai"
    elif integration_module == "langchain":
        pytest.importorskip("langchain_core")
        mod_name = "asap.integrations.langchain"
    else:
        pytest.importorskip("llama_index.core")
        mod_name = "asap.integrations.llamaindex"

    mod = import_module(mod_name)
    schema_fn = mod._json_schema_to_pydantic
    default_cls = mod._default_input_schema()
    assert schema_fn({}).__name__ == default_cls.__name__
    assert schema_fn({"type": "array"}).__name__ == default_cls.__name__
    empty_obj = schema_fn({"type": "object", "properties": {}})
    assert empty_obj.__name__ == default_cls.__name__

    rich: dict[str, Any] = {
        "type": "object",
        "properties": {
            "a": {"type": "string", "description": "sa"},
            "b": {"type": "integer"},
            "c": {"type": "number"},
            "d": {"type": "boolean"},
            "e": {"type": "array"},
            "f": {"type": "object"},
            "g": {"type": "other"},
            "skip": "not-a-dict",
        },
        "required": ["a"],
    }
    Model = schema_fn(rich, model_name="RichArgs")
    m = Model(a="x", b=1, c=1.5, d=True, e=[], f={}, g={})
    assert m.a == "x"


@pytest.mark.parametrize(
    "integration_module",
    [
        pytest.param("crewai", id="crewai"),
        pytest.param("langchain", id="langchain"),
    ],
)
def test_build_args_schema_from_manifest_branches(integration_module: str) -> None:
    if integration_module == "crewai":
        pytest.importorskip("crewai")
        mod_name = "asap.integrations.crewai"
    else:
        pytest.importorskip("langchain_core")
        mod_name = "asap.integrations.langchain"

    mod = import_module(mod_name)
    empty_caps = _manifest_minimal(skills=[])
    assert mod._build_args_schema_from_manifest(empty_caps) is None

    no_schema = _manifest_minimal(
        skills=[Skill(id="echo", description="e", input_schema=None)],
    )
    assert mod._build_args_schema_from_manifest(no_schema) is None

    skill_schema = {
        "type": "object",
        "properties": {"msg": {"type": "string"}},
        "required": ["msg"],
    }
    hyphen = _manifest_minimal(
        skills=[Skill(id="my-echo", description="e", input_schema=skill_schema)],
    )
    built = mod._build_args_schema_from_manifest(hyphen)
    assert built is not None
    assert built(msg="hi").msg == "hi"


def test_llama_index_build_fn_schema_from_manifest() -> None:
    pytest.importorskip("llama_index.core")
    import asap.integrations.llamaindex as mod

    default_model = mod._default_input_schema()
    empty = _manifest_minimal(skills=[])
    assert mod._build_fn_schema_from_manifest(empty).__name__ == default_model.__name__

    no_schema = _manifest_minimal(
        skills=[Skill(id="x", description="d", input_schema=None)],
    )
    assert mod._build_fn_schema_from_manifest(no_schema).__name__ == default_model.__name__

    skill_schema = {"type": "object", "properties": {"q": {"type": "string"}}}
    mnf = _manifest_minimal(
        skills=[Skill(id="search", description="s", input_schema=skill_schema)],
    )
    FnModel = mod._build_fn_schema_from_manifest(mnf)
    assert FnModel(q="why").q == "why"


def test_pydanticai_parameters_schema_and_to_str() -> None:
    pytest.importorskip("pydantic_ai")
    import asap.integrations.pydanticai as mod

    assert json.loads(mod._to_str_result({"a": 1})) == {"a": 1}
    assert mod._to_str_result("x") == "x"

    empty = _manifest_minimal(skills=[])
    assert mod._parameters_schema_from_manifest(empty) == mod.DEFAULT_PARAMETERS_JSON_SCHEMA

    bad = _manifest_minimal(
        skills=[Skill(id="e", description="d", input_schema={"type": "string"})],
    )
    assert mod._parameters_schema_from_manifest(bad) == mod.DEFAULT_PARAMETERS_JSON_SCHEMA

    good = _manifest_minimal(
        skills=[
            Skill(
                id="e",
                description="d",
                input_schema={
                    "type": "object",
                    "properties": {"inp": {"type": "string"}},
                },
            ),
        ],
    )
    params = mod._parameters_schema_from_manifest(good)
    assert params["type"] == "object"
    assert "inp" in params["properties"]


def test_smolagents_schema_and_name_helpers() -> None:
    pytest.importorskip("smolagents")
    import asap.integrations.smolagents as mod

    assert mod._sanitize_tool_name("My Agent!") == "My_Agent"
    assert mod._sanitize_tool_name("123bot") == "asap_123bot"
    assert mod._sanitize_tool_name("___") == "asap_agent"

    bad = mod._json_schema_to_smolagents_inputs({"type": "string"})
    assert bad == mod._DEFAULT_INPUTS.copy()

    rich: dict[str, Any] = {
        "type": "object",
        "properties": {
            "x": {"type": "string", "description": "dx"},
            "y": {"type": "integer"},
            "z": {"type": "weird", "description": "z"},
            "bad": "skip",
        },
    }
    inputs = mod._json_schema_to_smolagents_inputs(rich)
    assert inputs["x"]["type"] == "string"
    assert inputs["y"]["type"] == "integer"
    assert inputs["z"]["type"] == "string"

    empty_m = _manifest_minimal(skills=[])
    assert mod._build_inputs_from_manifest(empty_m) == mod._DEFAULT_INPUTS.copy()

    sm_manifest = _manifest_minimal(
        skills=[
            Skill(
                id="s",
                description="d",
                input_schema={"type": "object", "properties": {"q": {"type": "boolean"}}},
            ),
        ],
    )
    built = mod._build_inputs_from_manifest(sm_manifest)
    assert built["q"]["type"] == "boolean"

    assert json.loads(mod._to_str_result({"k": "v"})) == {"k": "v"}
    assert mod._to_str_result("plain") == "plain"
