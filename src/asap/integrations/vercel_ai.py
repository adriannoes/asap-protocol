"""Vercel AI SDK bridge: FastAPI router exposing ASAP agents for Next.js/React frontends.

Provides HTTP endpoints that return tool definitions in JSON Schema format,
compatible with Vercel AI SDK's `tool({ parameters: jsonSchema(...) })`.
The frontend fetches tool definitions and invokes agents via POST /invoke.

Usage:
    from fastapi import FastAPI
    from asap.integrations.vercel_ai import create_asap_tools_router

    app = FastAPI()
    app.include_router(create_asap_tools_router(), prefix="/api/asap", tags=["asap-tools"])
"""

from __future__ import annotations

from typing import Any, cast

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from asap.client.cache import get_registry
from asap.client.market import MarketClient
from asap.discovery.registry import DEFAULT_REGISTRY_URL, LiteRegistry
from asap.models.entities import Manifest
from asap.models.ids import generate_id

# JSON Schema for asap_invoke tool (Vercel AI SDK jsonSchema-compatible).
ASAP_INVOKE_PARAMETERS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "urn": {
            "type": "string",
            "description": "ASAP agent URN (e.g. urn:asap:agent:example)",
        },
        "payload": {
            "type": "object",
            "description": "Skill input payload matching the agent's schema",
        },
    },
    "required": ["urn", "payload"],
}

ASAP_INVOKE_TOOL_DEF: dict[str, Any] = {
    "name": "asap_invoke",
    "description": (
        "Invoke an ASAP agent by URN with the given payload. "
        "Use asap_discover first to find available agent URNs."
    ),
    "parameters": ASAP_INVOKE_PARAMETERS_SCHEMA,
}


def _search_registry(registry: LiteRegistry, query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return [e.model_dump() for e in registry.agents]
    matches = [
        e
        for e in registry.agents
        if q in e.name.lower()
        or q in (e.description or "").lower()
        or q in e.id.lower()
        or any(q in s.lower() for s in e.skills)
    ]
    return [e.model_dump() for e in matches]


def _parameters_schema_from_manifest(manifest: Manifest) -> dict[str, Any]:
    skills = getattr(manifest.capabilities, "skills", None) or []
    if not skills:
        return {
            "type": "object",
            "properties": {
                "input": {"type": "object", "description": "Skill input payload"},
            },
        }
    first = skills[0]
    schema = getattr(first, "input_schema", None) if first else None
    if not schema or not isinstance(schema, dict) or schema.get("type") != "object":
        return {
            "type": "object",
            "properties": {
                "input": {"type": "object", "description": "Skill input payload"},
            },
        }
    return cast(dict[str, Any], schema)


class InvokeRequest(BaseModel):
    urn: str = Field(..., description="ASAP agent URN")
    payload: dict[str, Any] = Field(..., description="Skill input payload")


class InvokeResponse(BaseModel):
    result: dict[str, Any] | str | None = Field(None, description="Agent result")
    error: str | None = Field(None, description="Error message if invocation failed")


class ToolDefinition(BaseModel):
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    parameters: dict[str, Any] = Field(..., description="JSON Schema for parameters")
    urn: str | None = Field(
        default=None,
        description="Fixed URN for whitelist tools; omit for asap_invoke (urn in params)",
    )


class ToolsListResponse(BaseModel):
    tools: list[ToolDefinition] = Field(..., description="List of tool definitions")


def create_asap_tools_router(
    *,
    registry_url: str = DEFAULT_REGISTRY_URL,
    whitelist_urns: list[str] | None = None,
    auth_token: str | None = None,
) -> APIRouter:
    """FastAPI router: GET /tools, POST /invoke, GET /discover for Vercel AI SDK."""
    client = MarketClient(
        registry_url=registry_url,
        auth_token=auth_token,
    )
    router = APIRouter()

    @router.get("/tools", response_model=ToolsListResponse)
    async def list_tools() -> ToolsListResponse:
        tools: list[ToolDefinition] = [
            ToolDefinition(
                name=ASAP_INVOKE_TOOL_DEF["name"],
                description=ASAP_INVOKE_TOOL_DEF["description"],
                parameters=ASAP_INVOKE_TOOL_DEF["parameters"],
            )
        ]
        if whitelist_urns:
            for urn in whitelist_urns:
                try:
                    resolved = await client.resolve(urn)
                    params = _parameters_schema_from_manifest(resolved.manifest)
                    safe_name = urn.replace(":", "_").replace(".", "_")
                    tools.append(
                        ToolDefinition(
                            name=f"asap_{safe_name}",
                            description=resolved.manifest.description or f"Invoke ASAP agent {urn}",
                            parameters=params,
                            urn=urn,
                        )
                    )
                except (OSError, ValueError):
                    pass
        return ToolsListResponse(tools=tools)

    @router.post("/invoke", response_model=InvokeResponse)
    async def invoke_agent(req: InvokeRequest) -> InvokeResponse:
        try:
            agent = await client.resolve(req.urn)
            skill_id = (
                agent.manifest.capabilities.skills[0].id
                if agent.manifest.capabilities.skills
                else ""
            )
            if not skill_id:
                return InvokeResponse(error="Agent has no skills")
            input_payload = req.payload.get("input", req.payload)
            if not isinstance(input_payload, dict):
                input_payload = {"value": input_payload}
            task_payload = {
                "conversation_id": generate_id(),
                "skill_id": skill_id,
                "input": input_payload,
            }
            result = await agent.run(task_payload)
            if isinstance(result, dict):
                return InvokeResponse(result=result)
            return InvokeResponse(result={"value": str(result)})
        except Exception as e:
            return InvokeResponse(error=str(e))

    @router.get("/discover")
    async def discover_agents(query: str = "") -> list[dict[str, Any]]:
        try:
            registry = await get_registry(registry_url)
            return _search_registry(registry, query)
        except Exception as e:
            raise HTTPException(status_code=502, detail="Failed to fetch registry") from e

    return router
