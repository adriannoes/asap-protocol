"""Map OpenAPI 3.x operations to ASAP :class:`~asap.models.entities.Skill` definitions."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, Literal, Protocol, TypeAlias, cast

from asap.adapters.openapi.spec_loader import OpenAPIDocument
from asap.models.entities import Skill

_HTTP_METHODS: tuple[str, ...] = (
    "get",
    "put",
    "post",
    "delete",
    "options",
    "head",
    "patch",
    "trace",
)


class OpenAPIExecutionKind(StrEnum):
    """How upstream responses should be executed (OA-010)."""

    SYNC = "sync"
    STREAMING = "streaming"
    ASYNC_POLLING = "async_polling"


class _SupportsRef(Protocol):
    ref: str


def _is_reference(obj: object) -> bool:
    """Detect Reference models across openapi-pydantic v3.0 / v3.1 types."""
    return type(obj).__name__ == "Reference" and hasattr(obj, "ref")


def _ref_fragment(ref: str, prefix: str) -> str | None:
    if not ref.startswith(prefix):
        return None
    return ref.removeprefix(prefix)


@dataclass(frozen=True, slots=True)
class OpenAPICapability:
    """One ASAP skill derived from an OpenAPI operation plus HTTP routing metadata."""

    skill: Skill
    http_method: str
    """Lowercase HTTP verb (e.g. ``get``, ``post``)."""
    path_template: str
    """OpenAPI path template (e.g. ``/pets/{petId}``)."""
    execution_kind: OpenAPIExecutionKind
    """Derived from response media types and status codes (``202`` + ``Location``, SSE)."""
    operation_id: str | None = None
    """Raw ``operationId`` from the spec when present; used for approval-strength lookup."""


@dataclass(frozen=True, slots=True)
class OpenAPIOperationContext:
    """OpenAPI operation identity exposed to :func:`map_openapi_to_capabilities` filters."""

    http_method: str
    """Lowercase HTTP verb (e.g. ``get``, ``head``)."""
    path_template: str
    capability_name: str
    """Resolved ASAP capability id (``operationId`` or method/path fallback)."""
    operation_id: str | None
    """Raw ``operationId`` from the spec, if present and non-empty."""
    openapi_operation: object
    """Underlying *openapi-pydantic* operation model for advanced filtering."""


DefaultCapabilitiesFilter: TypeAlias = (
    Literal["all"] | str | Sequence[str] | Callable[[OpenAPIOperationContext], bool]
)


def _predicate_from_default_capabilities(
    spec: DefaultCapabilitiesFilter,
) -> Callable[[OpenAPIOperationContext], bool]:
    """Turn *spec* into a predicate applied while scanning operations."""
    if spec == "all":
        return lambda _ctx: True
    if callable(spec):
        return spec
    if isinstance(spec, str):
        verb = spec.strip().lower()
        return lambda ctx: ctx.http_method == verb
    if isinstance(spec, Sequence) and not isinstance(spec, (str, bytes)):
        verbs = {str(m).strip().lower() for m in spec}
        return lambda ctx: ctx.http_method in verbs
    raise TypeError(
        "default_capabilities must be 'all', an HTTP method string, a sequence of methods, "
        f"or a callable; got {type(spec)!r}.",
    )


class _SchemaResolver:
    """Resolve ``#/components/schemas/*`` references into inlined JSON Schema dicts."""

    def __init__(self, raw_by_name: dict[str, dict[str, Any]]) -> None:
        self._raw_by_name = raw_by_name

    @classmethod
    def from_components(cls, components: object | None) -> _SchemaResolver:
        if components is None:
            return cls({})
        schemas = getattr(components, "schemas", None)
        if not schemas:
            return cls({})
        raw: dict[str, dict[str, Any]] = {}
        for name, schema_obj in cast(dict[str, Any], schemas).items():
            raw[name] = schema_obj.model_dump(mode="json", by_alias=True, exclude_none=True)
        return cls(raw)

    def expand_refs(self, node: Any, seen: frozenset[str]) -> Any:
        """Inline internal component schema refs; leave unknown or cyclic ``$ref`` as-is."""
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str):
                name = _ref_fragment(ref, "#/components/schemas/")
                if name is not None and name in self._raw_by_name:
                    if name in seen:
                        return {"$ref": ref}
                    base = self._raw_by_name[name]
                    return self.expand_refs(base, seen | {name})
            return {k: self.expand_refs(v, seen) for k, v in node.items()}
        if isinstance(node, list):
            return [self.expand_refs(item, seen) for item in node]
        return node

    def materialize(self, schema_or_ref: object | None) -> dict[str, Any] | None:
        if schema_or_ref is None:
            return None
        if _is_reference(schema_or_ref):
            ref = cast(_SupportsRef, schema_or_ref).ref
            name = _ref_fragment(ref, "#/components/schemas/")
            if name is None or name not in self._raw_by_name:
                return {"$ref": ref}
            return cast(
                dict[str, Any],
                self.expand_refs(self._raw_by_name[name], frozenset({name})),
            )
        model_dump = getattr(schema_or_ref, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(mode="json", by_alias=True, exclude_none=True)
            return cast(dict[str, Any], self.expand_refs(dumped, frozenset()))
        return None


def _resolve_parameter(
    param_or_ref: object,
    components: object | None,
) -> object | None:
    if not _is_reference(param_or_ref):
        return param_or_ref
    ref = cast(_SupportsRef, param_or_ref).ref
    key = _ref_fragment(ref, "#/components/parameters/")
    if key is None or components is None:
        return None
    bag = getattr(components, "parameters", None)
    if not bag or key not in bag:
        return None
    target = bag[key]
    if _is_reference(target):
        return _resolve_parameter(target, components)
    return cast(object | None, target)


def _param_location_str(loc_raw: Any) -> str:
    return cast(str, loc_raw.value) if isinstance(loc_raw, Enum) else str(loc_raw)


def _merge_parameters(
    path_item: object,
    operation: object,
    components: object | None,
) -> list[object]:
    merged: dict[tuple[str, str], object] = {}
    for entry in getattr(path_item, "parameters", None) or []:
        resolved = _resolve_parameter(entry, components)
        if resolved is not None and hasattr(resolved, "name") and hasattr(resolved, "param_in"):
            r = cast(Any, resolved)
            name = cast(str, r.name)
            loc_val = _param_location_str(r.param_in)
            merged[(name, loc_val)] = resolved
    for entry in getattr(operation, "parameters", None) or []:
        resolved = _resolve_parameter(entry, components)
        if resolved is not None and hasattr(resolved, "name") and hasattr(resolved, "param_in"):
            r = cast(Any, resolved)
            name = cast(str, r.name)
            loc_val = _param_location_str(r.param_in)
            merged[(name, loc_val)] = resolved
    return list(merged.values())


def _resolve_request_body(obj: object | None, components: object | None) -> object | None:
    if obj is None:
        return None
    if not _is_reference(obj):
        return obj
    ref = cast(_SupportsRef, obj).ref
    key = _ref_fragment(ref, "#/components/requestBodies/")
    if key is None or components is None:
        return None
    bag = getattr(components, "requestBodies", None)
    if not bag or key not in bag:
        return None
    body = bag[key]
    return _resolve_request_body(body, components)


def _resolve_response(obj: object | None, components: object | None) -> object | None:
    if obj is None:
        return None
    if not _is_reference(obj):
        return obj
    ref = cast(_SupportsRef, obj).ref
    key = _ref_fragment(ref, "#/components/responses/")
    if key is None or components is None:
        return None
    bag = getattr(components, "responses", None)
    if not bag or key not in bag:
        return None
    target = bag[key]
    return _resolve_response(target, components)


def _responses_include_event_stream(operation: object, components: object | None) -> bool:
    responses = getattr(operation, "responses", None)
    if not responses:
        return False
    for _, ref_or_resp in cast(dict[str, Any], responses).items():
        resp = _resolve_response(ref_or_resp, components)
        if resp is None:
            continue
        content = getattr(resp, "content", None)
        if not content:
            continue
        for media_type in content:
            if isinstance(media_type, str) and media_type.lower() == "text/event-stream":
                return True
    return False


def _responses_202_include_location(operation: object, components: object | None) -> bool:
    responses = getattr(operation, "responses", None)
    if not responses or "202" not in responses:
        return False
    resp = _resolve_response(cast(dict[str, Any], responses)["202"], components)
    if resp is None:
        return False
    headers = getattr(resp, "headers", None)
    if not headers:
        return False
    for name in cast(dict[str, Any], headers):
        if isinstance(name, str) and name.lower() == "location":
            return True
    return False


def detect_openapi_execution_kind(
    operation: object, components: object | None
) -> OpenAPIExecutionKind:
    """Classify an operation for async/sync/streaming registration (OA-010)."""
    if _responses_include_event_stream(operation, components):
        return OpenAPIExecutionKind.STREAMING
    if _responses_202_include_location(operation, components):
        return OpenAPIExecutionKind.ASYNC_POLLING
    return OpenAPIExecutionKind.SYNC


def _json_media_schema(media: object | None, resolver: _SchemaResolver) -> dict[str, Any] | None:
    if media is None:
        return None
    schema_obj = getattr(media, "media_type_schema", None)
    return resolver.materialize(schema_obj)


def _body_json_schema(
    request_body: object | None, resolver: _SchemaResolver
) -> dict[str, Any] | None:
    if request_body is None:
        return None
    content = getattr(request_body, "content", None)
    if not content:
        return None
    media = content.get("application/json")
    if media is None:
        return None
    return _json_media_schema(media, resolver)


def _success_response_schema(
    operation: object,
    components: object | None,
    resolver: _SchemaResolver,
) -> dict[str, Any] | None:
    responses = getattr(operation, "responses", None)
    if not responses:
        return None
    for code in ("200", "201"):
        if code not in responses:
            continue
        resp = _resolve_response(responses[code], components)
        if resp is None:
            continue
        content = getattr(resp, "content", None)
        if not content:
            continue
        media = content.get("application/json")
        if media is None:
            continue
        return _json_media_schema(media, resolver)
    return None


def _parameter_properties(
    parameters: list[object],
    resolver: _SchemaResolver,
) -> tuple[dict[str, Any], list[str]]:
    properties: dict[str, Any] = {}
    required: list[str] = []
    for model in parameters:
        m = cast(Any, model)
        name = cast(str, m.name)
        schema_obj = m.param_schema
        if schema_obj is None:
            content = m.content
            if content:
                mt = content.get("application/json")
                if mt is not None:
                    schema_obj = mt.media_type_schema
        base = resolver.materialize(schema_obj) if schema_obj is not None else {"type": "string"}
        if base is None:
            base = {"type": "string"}
        loc = m.param_in
        loc_val = _param_location_str(loc)
        prop_schema: dict[str, Any] = {
            **base,
            "x-openapi-param-in": loc_val,
        }
        desc = m.description
        if isinstance(desc, str) and desc and "description" not in prop_schema:
            prop_schema["description"] = desc
        properties[name] = prop_schema
        if m.required and name not in required:
            required.append(name)
    return properties, required


def _build_input_schema(
    parameters: list[object],
    body_schema: dict[str, Any] | None,
    resolver: _SchemaResolver,
) -> dict[str, Any] | None:
    param_props, param_req = _parameter_properties(parameters, resolver)
    parts: list[dict[str, Any]] = []
    if param_props:
        obj: dict[str, Any] = {"type": "object", "properties": dict(param_props)}
        if param_req:
            obj["required"] = list(param_req)
        parts.append(obj)
    if body_schema:
        parts.append(body_schema)
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return {"allOf": parts}


def _fallback_capability_name(method: str, path_template: str) -> str:
    trimmed = path_template.strip("/")
    part = (
        "rootpath" if not trimmed else trimmed.replace("/", "_").replace("{", "").replace("}", "")
    )
    return f"{method.lower()}_{part}"


def _operation_description(operation: object, path_item: object, fallback: str) -> str:
    for attr in ("summary", "description"):
        val = getattr(operation, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for attr in ("summary", "description"):
        val = getattr(path_item, attr, None)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return fallback


def map_openapi_to_capabilities(
    doc: OpenAPIDocument,
    *,
    default_capabilities: DefaultCapabilitiesFilter = "all",
) -> list[OpenAPICapability]:
    """Derive ASAP skills (and HTTP metadata) from operations in *doc*.

    Each :class:`OpenAPICapability` includes :attr:`OpenAPICapability.execution_kind`
    (OA-010): ``streaming`` if any response advertises ``text/event-stream``,
    else ``async_polling`` if a ``202`` response declares a ``Location`` header,
    else ``sync``.

    Args:
        doc: Parsed OpenAPI 3.0 / 3.1 root model.
        default_capabilities: Which HTTP operations to include. The literal
            ``all`` keeps every verb. A single string (e.g. ``GET``) or a
            sequence of method names matches case-insensitively against the
            lowercase verb used internally. A callable receives
            :class:`OpenAPIOperationContext` for each operation and must return
            ``True`` to include it.
    """
    paths_raw = getattr(doc, "paths", None)
    if not paths_raw:
        return []

    resolver = _SchemaResolver.from_components(getattr(doc, "components", None))
    components = getattr(doc, "components", None)
    predicate = _predicate_from_default_capabilities(default_capabilities)

    capabilities: list[OpenAPICapability] = []
    for path_template, path_item in cast(dict[str, Any], paths_raw).items():
        for method in _HTTP_METHODS:
            operation = getattr(path_item, method, None)
            if operation is None:
                continue

            op_id = getattr(operation, "operationId", None)
            op_id_str = op_id.strip() if isinstance(op_id, str) and op_id.strip() else None
            cap_name = op_id_str if op_id_str else _fallback_capability_name(method, path_template)

            ctx = OpenAPIOperationContext(
                http_method=method,
                path_template=path_template,
                capability_name=cap_name,
                operation_id=op_id_str,
                openapi_operation=operation,
            )
            if not predicate(ctx):
                continue

            params = _merge_parameters(path_item, operation, components)
            rb = _resolve_request_body(getattr(operation, "requestBody", None), components)
            body_json = _body_json_schema(rb, resolver)

            input_schema = _build_input_schema(params, body_json, resolver)
            output_schema = _success_response_schema(operation, components, resolver)

            description = _operation_description(operation, path_item, cap_name)
            execution_kind = detect_openapi_execution_kind(operation, components)

            skill = Skill(
                id=cap_name,
                description=description,
                input_schema=input_schema,
                output_schema=output_schema,
            )
            capabilities.append(
                OpenAPICapability(
                    skill=skill,
                    http_method=method,
                    path_template=path_template,
                    execution_kind=execution_kind,
                    operation_id=op_id_str,
                ),
            )

    return capabilities


__all__ = [
    "DefaultCapabilitiesFilter",
    "OpenAPICapability",
    "OpenAPIExecutionKind",
    "OpenAPIOperationContext",
    "detect_openapi_execution_kind",
    "map_openapi_to_capabilities",
]
