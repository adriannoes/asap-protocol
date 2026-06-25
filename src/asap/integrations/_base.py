"""Shared base for ASAP framework integrations (INT-001).

The LangChain, CrewAI, LlamaIndex, and SmolAgents wrappers each used to carry
their own copy of the same plumbing — JSON-Schema → framework-schema conversion,
the default skill-input model, agent-URN resolution, task-payload assembly, the
sync/async invoke flow, and error string formatting. This module centralizes it
so each framework file keeps only its class + base-tool wiring. The full surface
is listed in ``__all__``; the async invoke helpers duck-type their *cache*
argument over a framework tool's private ``_resolved`` / ``_skill_id``
attributes, so each tool instance is its own cache with no extra state object.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Type, cast

from pydantic import BaseModel, Field, create_model

from asap.client.market import MarketClient, ResolvedAgent
from asap.errors import AgentRevokedException, SignatureVerificationError
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# Sentinel placed on a client while its ``resolve`` is in flight so a
# re-entrant resolve of the same URN raises instead of scheduling forever.
_RESOLVING_SENTINEL: dict[str, Any] = {"_asap_resolving": True}

# Exceptions raised by ``MarketClient.resolve`` / ``ResolvedAgent.run`` that the
# wrappers translate into error strings rather than propagating.
RESOLVE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    OSError,
    ValueError,
    AgentRevokedException,
    SignatureVerificationError,
)


def default_input_schema(name: str = "AsapToolInput") -> Type[BaseModel]:
    """Build the generic ``{input: dict[str, Any]}`` fallback input model.

    Args:
        name: Pydantic model name (each framework passes its own prefix).

    Returns:
        A dynamically created ``BaseModel`` subclass with one ``input`` field.

    Example:
        >>> Model = default_input_schema("CrewAIAsapToolInput")
        >>> Model(input={"q": "hi"}).input == {"q": "hi"}
        True
    """
    return create_model(
        name,
        input=(dict[str, Any], Field(description="Skill input payload (key-value)")),
    )


def json_schema_to_pydantic(
    schema: dict[str, Any],
    model_name: str = "AsapToolArgs",
    default_name: str = "AsapToolInput",
) -> Type[BaseModel]:
    """Convert a JSON Schema ``object`` into a pydantic model.

    Falls back to :func:`default_input_schema` (named *default_name*) when
    *schema* is missing, not an ``object``, or yields no field definitions.
    Required fields default to ``None``; optional fields get type-appropriate
    empty defaults. *default_name* is separate from *model_name* so a
    framework's ``_json_schema_to_pydantic({})`` matches its
    ``_default_input_schema()``.

    Args:
        schema: JSON Schema dict (typically ``Skill.input_schema``).
        model_name: Name for the generated pydantic model when fields exist.
        default_name: Name for the fallback model (the framework default).

    Returns:
        A ``BaseModel`` subclass mirroring the schema's properties.
    """
    if not schema or schema.get("type") != "object":
        return default_input_schema(default_name)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    field_defs: dict[str, Any] = {}
    for key, prop in props.items():
        if not isinstance(prop, dict):
            continue
        field_defs[key] = _schema_property_to_field(key, prop, required)
    if not field_defs:
        return default_input_schema(default_name)
    return cast(Type[BaseModel], create_model(model_name, **field_defs))


def _schema_property_to_field(
    key: str, prop: dict[str, Any], required: set[str]
) -> tuple[type[Any], Any]:
    """Map a single JSON Schema property to a ``(python_type, Field)`` pair.

    The second element is a :class:`pydantic.FieldInfo` from
    :func:`pydantic.Field`; typed as ``Any`` because the pydantic mypy plugin
    exposes ``Field`` as a variable rather than a type.
    """
    typ = prop.get("type", "string")
    desc = prop.get("description") or key
    if typ == "string":
        return str, Field(default=None if key in required else "", description=desc)
    if typ == "integer":
        return int, Field(default=None if key in required else 0, description=desc)
    if typ == "number":
        return float, Field(default=None if key in required else 0.0, description=desc)
    if typ == "boolean":
        return bool, Field(default=None if key in required else False, description=desc)
    if typ == "array":
        return list[Any], Field(default_factory=list, description=desc)
    return dict[str, Any], Field(default_factory=dict, description=desc)


def resolve_and_cache_skill(client: MarketClient, urn: str) -> tuple[ResolvedAgent, str]:
    """Eagerly resolve *urn* (sync) and cache the result on *client*.

    Drives :meth:`MarketClient.resolve` via ``asyncio.run``. A running event loop
    signals deferral by raising :class:`RuntimeError`; wrappers catch it and
    resolve lazily on the first ``_arun``. The resolved agent and first skill id
    are stashed on the client as ``_asap_resolved`` / ``_asap_skill_id``. A
    re-entrant call for an in-flight URN raises :class:`RuntimeError` instead of
    deadlocking.

    Args:
        client: The market client performing the resolution.
        urn: Agent URN to resolve.

    Returns:
        ``(resolved_agent, skill_id)``; ``skill_id`` is ``""`` when the agent
        declares no skills.

    Raises:
        RuntimeError: If a loop is running or *urn* is already being resolved.
        OSError, ValueError, AgentRevokedException, SignatureVerificationError:
            Propagated from ``MarketClient.resolve`` (callers swallow or re-raise).
    """
    if _has_running_loop():
        raise RuntimeError(f"event loop running; defer resolve of {urn!r}")
    cached = getattr(client, "_asap_resolved", None)
    if cached is not None and cached is not _RESOLVING_SENTINEL:
        return cached, getattr(client, "_asap_skill_id", "")
    if cached is _RESOLVING_SENTINEL:
        raise RuntimeError(f"Re-entrant resolve detected for URN {urn!r}; aborting.")
    object.__setattr__(client, "_asap_resolved", _RESOLVING_SENTINEL)
    try:
        resolved = asyncio.run(client.resolve(urn))
    finally:
        if getattr(client, "_asap_resolved", None) is _RESOLVING_SENTINEL:
            object.__setattr__(client, "_asap_resolved", None)
    skills = resolved.manifest.capabilities.skills
    skill_id = skills[0].id if skills else ""
    object.__setattr__(client, "_asap_resolved", resolved)
    object.__setattr__(client, "_asap_skill_id", skill_id)
    return resolved, skill_id


def build_args_schema_from_manifest(
    manifest: Manifest, model_prefix: str = "Asap"
) -> Type[BaseModel] | None:
    """Build a pydantic args model from the agent's first skill, or ``None``.

    For wrappers (LangChain, CrewAI) whose args schema is optional: returns
    ``None`` when the agent has no skills or the first skill has no usable
    ``input_schema`` dict, so the caller keeps the default input model. The
    generated model is named ``{model_prefix}_{skill_id_with_underscores}``.
    ``Capability.skills`` is a required typed field, so it is accessed directly.

    Args:
        manifest: Resolved agent manifest.
        model_prefix: Prefix for the generated pydantic model name.

    Returns:
        A ``BaseModel`` subclass mirroring the first skill's input schema, or
        ``None`` when no schema is available.
    """
    skills = manifest.capabilities.skills
    if not skills:
        return None
    schema = skills[0].input_schema
    if not schema or not isinstance(schema, dict):
        return None
    name = f"{model_prefix}_{skills[0].id.replace('-', '_')}"
    return json_schema_to_pydantic(schema, model_name=name)


def build_fn_schema_from_manifest(
    manifest: Manifest, model_prefix: str = "Asap", default_name: str = "AsapToolInput"
) -> Type[BaseModel]:
    """Build a pydantic fn schema from the first skill, or the default model.

    For wrappers (LlamaIndex) whose schema is required: returns
    :func:`default_input_schema` (named *default_name*) when the agent has no
    skills or the first skill has no usable ``input_schema`` dict. The generated
    model is named ``{model_prefix}_{skill_id_with_underscores}``.

    Args:
        manifest: Resolved agent manifest.
        model_prefix: Prefix for the generated pydantic model name.
        default_name: Name for the fallback default model.

    Returns:
        A ``BaseModel`` subclass mirroring the first skill's input schema, or
        the default input model when no schema is available.
    """
    skills = manifest.capabilities.skills
    if not skills:
        return default_input_schema(default_name)
    schema = skills[0].input_schema
    if not schema or not isinstance(schema, dict):
        return default_input_schema(default_name)
    name = f"{model_prefix}_{skills[0].id.replace('-', '_')}"
    return json_schema_to_pydantic(schema, model_name=name, default_name=default_name)


# --- SmolAgents-oriented helpers (inputs dict shape + tool-name sanitization) -----

# SmolAgents AUTHORIZED_TYPES for inputs and output_type.
SMOLAGENTS_TYPES: frozenset[str] = frozenset(
    {"string", "boolean", "integer", "number", "image", "audio", "array", "object", "any", "null"}
)

# Default smolagents inputs when the agent schema is unavailable (generic object input).
DEFAULT_SMOLAGENTS_INPUTS: dict[str, dict[str, str]] = {
    "input": {
        "type": "object",
        "description": "Skill input payload (key-value dict matching agent schema)",
    }
}


def sanitize_tool_name(name: str) -> str:
    """Coerce *name* into a smolagents-valid identifier (alnum + underscore).

    Leading digits are prefixed with ``asap_``; an all-symbol name falls back to
    ``"asap_agent"``.

    Example:
        >>> sanitize_tool_name("My Agent!")
        'My_Agent'
        >>> sanitize_tool_name("123bot")
        'asap_123bot'
    """
    sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in name)
    sanitized = sanitized.strip("_") or "asap_agent"
    if sanitized[0].isdigit():
        sanitized = "asap_" + sanitized
    return sanitized


def json_schema_to_smolagents_inputs(
    schema: dict[str, Any], *, default_inputs: dict[str, dict[str, str]] | None = None
) -> dict[str, dict[str, str]]:
    """Convert a JSON Schema ``object`` into smolagents ``{field: {type, description}}`` inputs.

    Falls back to *default_inputs* (or :data:`DEFAULT_SMOLAGENTS_INPUTS`) when the
    schema is missing, not an ``object``, or yields no fields. Unknown JSON types
    coerce to ``"string"`` (smolagents' safest scalar).

    Args:
        schema: JSON Schema dict (typically ``Skill.input_schema``).
        default_inputs: Override fallback inputs dict.

    Returns:
        A smolagents inputs dict mapping each field to ``{type, description}``.
    """
    fallback = default_inputs if default_inputs is not None else DEFAULT_SMOLAGENTS_INPUTS
    if not schema or schema.get("type") != "object":
        return fallback.copy()
    props = schema.get("properties") or {}
    result: dict[str, dict[str, str]] = {}
    for key, prop in props.items():
        if not isinstance(prop, dict):
            continue
        smol_type = prop.get("type", "string")
        result[key] = {
            "type": smol_type if smol_type in SMOLAGENTS_TYPES else "string",
            "description": prop.get("description") or key,
        }
    return result or fallback.copy()


def build_smolagents_inputs_from_manifest(manifest: Manifest) -> dict[str, dict[str, str]]:
    """Build smolagents inputs from the agent's first skill, or the default inputs.

    Returns:
        A smolagents inputs dict, falling back to :data:`DEFAULT_SMOLAGENTS_INPUTS`
        when the agent has no skills or the first skill has no usable schema.
    """
    skills = manifest.capabilities.skills
    if not skills:
        return DEFAULT_SMOLAGENTS_INPUTS.copy()
    schema = skills[0].input_schema
    if not schema or not isinstance(schema, dict):
        return DEFAULT_SMOLAGENTS_INPUTS.copy()
    return json_schema_to_smolagents_inputs(schema)


def build_task_payload(skill_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
    """Assemble the ``TaskRequest`` payload dict for a skill invocation.

    *skill_id* must be non-empty (callers check); *input_payload* is the already
    coerced skill input dict.

    Returns:
        A payload dict with ``conversation_id``, ``skill_id``, and ``input``.
    """
    return {
        "conversation_id": generate_id(),
        "skill_id": skill_id,
        "input": input_payload,
    }


def format_invoke_error(exc: BaseException) -> str:
    """Map a caught invoke-time exception to a user-facing error string.

    Replaces the misleading shared ``"Agent revoked or invalid input"`` that
    fired for plain :class:`ValueError` as well as genuine revocations. Each
    type gets a distinct, truthful prefix preserving the exception message:

    - :class:`AgentRevokedException` → ``"Error: Agent revoked: …"``
    - :class:`SignatureVerificationError` → ``"Error: Agent signature
      verification failed: …"``
    - :class:`ValueError` → ``"Error: Invalid skill input or task request: …"``
    - any other exception → ``"Error: ASAP invocation failed: …"``
    """
    if isinstance(exc, AgentRevokedException):
        return f"Error: Agent revoked: {exc!s}"
    if isinstance(exc, SignatureVerificationError):
        return f"Error: Agent signature verification failed: {exc!s}"
    if isinstance(exc, ValueError):
        return f"Error: Invalid skill input or task request: {exc!s}"
    return f"Error: ASAP invocation failed: {exc!s}"


def coerce_tool_input(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    """Normalize positional/keyword tool input into the skill input dict.

    Non-dict positional input is wrapped as ``{"input": {"raw": value}}``.
    """
    tool_input = dict(kwargs) if kwargs else (args[0] if args else {})
    if not isinstance(tool_input, dict):
        tool_input = {"input": {"raw": tool_input}}
    return tool_input


def to_str_result(value: str | dict[str, Any]) -> str:
    """Coerce an invoke result to a string: JSON for dicts, ``str()`` otherwise."""
    if isinstance(value, dict):
        return json.dumps(value)
    return str(value)


async def _resolve_or_cache(client: MarketClient, urn: str, cache: Any) -> ResolvedAgent:
    """Return the cached resolved agent or resolve lazily; populate *cache*.

    *cache* is duck-typed over the private attributes ``_resolved`` and
    ``_skill_id`` (the framework tool instances expose them directly). The skill
    id is populated as ``""`` when the agent declares no skills; callers check
    it and surface the ``"Agent has no skills"`` error themselves.
    """
    cached = getattr(cache, "_resolved", None)
    if cached is not None:
        return cast(ResolvedAgent, cached)
    resolved = await client.resolve(urn)
    skills = resolved.manifest.capabilities.skills
    object.__setattr__(cache, "_resolved", resolved)
    object.__setattr__(cache, "_skill_id", skills[0].id if skills else "")
    return resolved


async def invoke_skill_async(
    client: MarketClient,
    urn: str,
    cache: Any,
    tool_input: dict[str, Any],
) -> str | dict[str, Any]:
    """Shared async invoke: resolve-or-cache, run, return dict-or-str result.

    *cache* is a framework tool instance exposing settable ``_resolved`` /
    ``_skill_id`` attributes (see :func:`_resolve_or_cache`); *tool_input* is a
    coerced skill input dict (see :func:`coerce_tool_input`).

    Returns:
        The ``TaskResponse.result`` dict when the agent returns a dict, else its
        ``str()`` form; an ``"Error: …"`` string on resolve/run failure or when
        the agent declares no skills.
    """
    try:
        resolved = await _resolve_or_cache(client, urn, cache)
        skill_id = getattr(cache, "_skill_id", "")
        if not skill_id:
            return "Error: Agent has no skills; cannot build task request."
        input_payload = tool_input.get("input", tool_input)
        if not isinstance(input_payload, dict):
            input_payload = {"value": input_payload}
        result = await resolved.run(build_task_payload(skill_id, input_payload))
        return result if isinstance(result, dict) else str(result)
    except Exception as exc:  # noqa: BLE001 — wrappers return error strings
        return format_invoke_error(exc)


async def invoke_skill_json_async(
    client: MarketClient,
    urn: str,
    cache: Any,
    tool_input: dict[str, Any],
) -> str:
    """Async invoke that JSON-stringifies dict results for str-only frameworks.

    Same flow as :func:`invoke_skill_async` but the success result is passed
    through :func:`to_str_result` so CrewAI/SmolAgents always receive ``str``.
    Error strings are returned unchanged.
    """
    result = await invoke_skill_async(client, urn, cache, tool_input)
    return result if isinstance(result, str) else to_str_result(result)


def _has_running_loop() -> bool:
    """True when an asyncio event loop is running in the current thread."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def eager_resolve_or_defer(client: MarketClient, urn: str) -> tuple[ResolvedAgent | None, str]:
    """Eagerly resolve *urn* (sync) or defer when a loop is running.

    For wrappers that swallow resolve failures in their constructor (LangChain,
    CrewAI, SmolAgents): returns ``(agent, skill_id)`` on success, else
    ``(None, "")`` when a loop is running (deferral) or a resolve exception
    fires — so the constructor keeps the default schema and the first ``_arun``
    resolves lazily.

    Returns:
        ``(resolved_agent, skill_id)`` on success, else ``(None, "")``.
    """
    try:
        return resolve_and_cache_skill(client, urn)
    except RuntimeError:
        return None, ""
    except RESOLVE_EXCEPTIONS:
        return None, ""


def eager_resolve_or_raise(client: MarketClient, urn: str) -> tuple[ResolvedAgent | None, str]:
    """Eagerly resolve *urn* (sync), raising ``ValueError`` on any failure.

    For wrappers that surface resolve failures in their constructor (LlamaIndex,
    PydanticAI): returns ``(agent, skill_id)`` on success. When a loop is running
    the resolve is deferred (returns ``(None, "")``) so the constructor does not
    raise inside a host event loop. Any other failure is wrapped as
    ``ValueError("Failed to resolve agent {urn}: …")``.

    Returns:
        ``(resolved_agent, skill_id)``; ``resolved_agent`` is ``None`` only when
        deferred because a loop was running.

    Raises:
        ValueError: If resolution failed for any non-deferral reason.
    """
    try:
        return resolve_and_cache_skill(client, urn)
    except RuntimeError:
        return None, ""  # loop running: defer to first invoke
    except Exception as exc:  # noqa: BLE001 — wrapped into ValueError
        raise ValueError(f"Failed to resolve agent {urn}: {exc}") from exc


__all__ = [
    "RESOLVE_EXCEPTIONS",
    "SMOLAGENTS_TYPES",
    "DEFAULT_SMOLAGENTS_INPUTS",
    "build_args_schema_from_manifest",
    "build_fn_schema_from_manifest",
    "build_smolagents_inputs_from_manifest",
    "build_task_payload",
    "coerce_tool_input",
    "default_input_schema",
    "eager_resolve_or_defer",
    "eager_resolve_or_raise",
    "format_invoke_error",
    "invoke_skill_async",
    "invoke_skill_json_async",
    "json_schema_to_pydantic",
    "json_schema_to_smolagents_inputs",
    "resolve_and_cache_skill",
    "sanitize_tool_name",
    "to_str_result",
]
