"""Assemble manifest + handler registry from a loaded OpenAPI document (OA-001)."""

from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

from asap.adapters.openapi.approval import collect_webauthn_required_capability_names
from asap.adapters.openapi.capability_mapper import (
    DefaultCapabilitiesFilter,
    OpenAPIExecutionKind,
    OpenAPICapability,
    map_openapi_to_capabilities,
)
from asap.adapters.openapi.handler import (
    OpenAPIUpstreamHandler,
    ResolveHeaders,
    create_openapi_task_handler,
)
from asap.adapters.openapi.spec_loader import OpenAPISpecError, OpenAPIDocument, load_spec
from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.transport.handlers import HandlerRegistry

logger = logging.getLogger(__name__)

PETSTORE_OPENAPI_URL = "https://petstore3.swagger.io/api/v3/openapi.json"

_KNOWN_CREATE_FROM_OPENAPI_KEYS: frozenset[str] = frozenset(
    (
        "spec_url",
        "spec_path",
        "http_client",
        "upstream_base_url",
        "default_capabilities",
        "approval_strength",
        "resolve_headers",
        "manifest_id",
        "manifest_name",
        "asap_endpoint",
    ),
)


@dataclass(frozen=True, slots=True)
class OpenAPIAdapterBundle:
    """Result of :func:`create_from_openapi` — ready for :func:`asap.transport.server.create_app`."""

    manifest: Manifest
    registry: HandlerRegistry
    capabilities: list[OpenAPICapability]
    require_webauthn_for: list[str]
    upstream_base_url: str


def _infer_upstream_base_url(
    doc: OpenAPIDocument,
    override: str | None,
    *,
    resolution_base: str | None,
) -> str:
    if override is not None and override.strip():
        return override.strip().rstrip("/")
    servers = getattr(doc, "servers", None)
    if not servers:
        msg = "OpenAPI document has no `servers`; pass upstream_base_url= to create_from_openapi."
        raise OpenAPISpecError(msg)
    first = servers[0]
    raw_url = getattr(first, "url", None)
    if not isinstance(raw_url, str) or not raw_url.strip():
        msg = "OpenAPI `servers[0].url` is missing or empty."
        raise OpenAPISpecError(msg)
    candidate = raw_url.strip()
    if candidate.startswith(("http://", "https://")):
        return candidate.rstrip("/")
    if resolution_base is None or not resolution_base.strip():
        msg = (
            f"Relative OpenAPI server URL {raw_url!r} requires upstream_base_url= "
            "when the spec is loaded from a local path."
        )
        raise OpenAPISpecError(msg)
    joined = urljoin(resolution_base.strip(), candidate)
    return joined.rstrip("/")


def _build_manifest(
    *,
    doc: OpenAPIDocument,
    caps: list[OpenAPICapability],
    manifest_id: str,
    manifest_name: str,
    asap_endpoint: str,
) -> Manifest:
    title = getattr(getattr(doc, "info", None), "title", None)
    ver = getattr(getattr(doc, "info", None), "version", None)
    name = (
        manifest_name.strip()
        if manifest_name.strip()
        else (title.strip() if isinstance(title, str) and title.strip() else "OpenAPI Adapter")
    )
    version = ver.strip() if isinstance(ver, str) and ver.strip() else "1.0.0"
    skills = [
        Skill(
            id=c.skill.id,
            description=c.skill.description,
            input_schema=c.skill.input_schema,
            output_schema=c.skill.output_schema,
        )
        for c in caps
    ]
    return Manifest(
        id=manifest_id.strip(),
        name=name,
        version=version,
        description=f"ASAP adapter for OpenAPI spec {name!r}",
        capabilities=Capability(
            asap_version="0.1",
            skills=skills,
            streaming=any(c.execution_kind == OpenAPIExecutionKind.STREAMING for c in caps),
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=asap_endpoint.strip()),
    )


async def create_from_openapi(
    *,
    spec_url: str | None = None,
    spec_path: str | Path | None = None,
    http_client: httpx.AsyncClient,
    upstream_base_url: str | None = None,
    default_capabilities: DefaultCapabilitiesFilter = "all",
    approval_strength: dict[str, str] | None = None,
    resolve_headers: ResolveHeaders | None = None,
    manifest_id: str = "urn:asap:agent:openapi-adapter",
    manifest_name: str = "",
    asap_endpoint: str = "http://localhost:8000/asap",
    **kwargs: Any,
) -> OpenAPIAdapterBundle:
    """Load OpenAPI 3.x, map operations to skills, and wire an upstream proxy handler.

    Args:
        spec_url: HTTPS (or HTTP) URL of the OpenAPI JSON/YAML document.
        spec_path: Local path to a document (alternative to ``spec_url``).
        http_client: Shared ``httpx`` client used for spec fetch (if URL) and upstream calls.
        upstream_base_url: Base URL for API calls; defaults to the first OpenAPI ``servers``.
        default_capabilities: Filter forwarded to :func:`map_openapi_to_capabilities`.
        approval_strength: Optional OA-008 mapping; use
            :attr:`OpenAPIAdapterBundle.require_webauthn_for` with
            :class:`asap.auth.self_auth.FreshSessionConfig`.
        resolve_headers: Optional `(session) -> headers` for upstream auth (OA-009).
        manifest_id: ``Manifest.id`` (also Host JWT ``aud`` when using identity routes).
        manifest_name: Override manifest display name (default: ``info.title``).
        asap_endpoint: Advertised ``/asap`` URL in the manifest.
        **kwargs: Reserved; unknown keys emit :class:`UserWarning` to surface typos.

    Returns:
        Bundle containing manifest, handler registry, and metadata.

    Raises:
        OpenAPISpecError: Invalid document, unsupported server URL, etc.
        ValueError: Duplicate capability ids in the spec.
    """
    remainder = dict(kwargs)
    for _key in _KNOWN_CREATE_FROM_OPENAPI_KEYS:
        remainder.pop(_key, None)
    if remainder:
        warnings.warn(
            "create_from_openapi ignored unexpected keyword arguments: "
            + ", ".join(sorted(remainder)),
            UserWarning,
            stacklevel=2,
        )
    if (spec_url is None) == (spec_path is None):
        msg = "Exactly one of spec_url or spec_path must be set."
        raise OpenAPISpecError(msg)
    if spec_url is not None:
        doc = await load_spec(spec_url, http_client=http_client)
        resolution_base = spec_url
    else:
        if spec_path is None:
            msg = "spec_path is required when spec_url is omitted."
            raise OpenAPISpecError(msg)
        doc = await load_spec(spec_path)
        resolution_base = None
    caps = map_openapi_to_capabilities(doc, default_capabilities=default_capabilities)
    logger.info(
        "OpenAPI capabilities mapped count=%s manifest_id=%s",
        len(caps),
        manifest_id,
    )
    base = _infer_upstream_base_url(doc, upstream_base_url, resolution_base=resolution_base)
    require_wa = (
        collect_webauthn_required_capability_names(caps, approval_strength)
        if approval_strength
        else []
    )
    manifest = _build_manifest(
        doc=doc,
        caps=caps,
        manifest_id=manifest_id,
        manifest_name=manifest_name,
        asap_endpoint=asap_endpoint,
    )
    upstream = OpenAPIUpstreamHandler.from_capabilities(
        base_url=base,
        capabilities=caps,
        http_client=http_client,
        resolve_headers=resolve_headers,
    )
    registry = HandlerRegistry()
    registry.register("task.request", create_openapi_task_handler(upstream))
    return OpenAPIAdapterBundle(
        manifest=manifest,
        registry=registry,
        capabilities=list(caps),
        require_webauthn_for=require_wa,
        upstream_base_url=base,
    )


__all__ = [
    "OpenAPIAdapterBundle",
    "PETSTORE_OPENAPI_URL",
    "create_from_openapi",
]
