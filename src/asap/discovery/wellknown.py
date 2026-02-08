"""Well-known URI handler for ASAP agent discovery (RFC 8615).

Serves GET /.well-known/asap/manifest.json with optional HTTP caching
(Cache-Control, ETag, If-None-Match) for discovery by other agents.
"""

from __future__ import annotations

import hashlib
import json

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from asap.models.entities import Manifest

WELLKNOWN_MANIFEST_PATH = "/.well-known/asap/manifest.json"
"""Standard path for the ASAP agent manifest (RFC 8615)."""

CONTENT_TYPE_JSON = "application/json"
"""Content-Type for manifest JSON response."""

CACHE_MAX_AGE_SECONDS = 300
"""Default max-age for Cache-Control (5 minutes)."""

CACHE_CONTROL_VALUE = f"public, max-age={CACHE_MAX_AGE_SECONDS}"
"""Cache-Control header value for manifest responses."""

HEADER_ETAG = "etag"
HEADER_IF_NONE_MATCH = "if-none-match"
HEADER_CACHE_CONTROL = "cache-control"


def get_manifest_json(manifest: Manifest) -> dict:
    """Return manifest as JSON-serializable dict for the well-known endpoint.

    Args:
        manifest: The agent's manifest.

    Returns:
        Dictionary suitable for JSON response (model_dump).
    """
    return manifest.model_dump()


def compute_manifest_etag(manifest: Manifest) -> str:
    """Compute a strong ETag for the manifest from its canonical JSON.

    Uses SHA-256 of sorted JSON so the same manifest always yields the same ETag.

    Args:
        manifest: The agent's manifest.

    Returns:
        ETag value without quotes (caller adds quotes in header if needed).
    """
    payload = json.dumps(get_manifest_json(manifest), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _etag_header_value(etag: str) -> str:
    """Format ETag for HTTP header (quoted)."""
    return f'"{etag}"'


async def get_manifest_response(manifest: Manifest, request: Request) -> Response:
    """Return FastAPI response for GET /.well-known/asap/manifest.json.

    Returns the agent manifest as JSON with Content-Type: application/json,
    Cache-Control: public, max-age=300, and ETag. If the request sends
    If-None-Match matching the current ETag, returns 304 Not Modified.

    Args:
        manifest: The agent's manifest.
        request: The incoming request (used for If-None-Match).

    Returns:
        JSONResponse (200) with body and caching headers, or Response (304) when
        client sent matching If-None-Match.
    """
    etag = compute_manifest_etag(manifest)
    etag_header = _etag_header_value(etag)
    if_none_match = request.headers.get(HEADER_IF_NONE_MATCH)

    # RFC 7232: If-None-Match can be a single value or comma-separated list
    match = (
        if_none_match is not None
        and any(part.strip() == etag_header for part in if_none_match.split(","))
    )
    if match:
        return Response(
            status_code=304,
            headers={
                HEADER_ETAG: etag_header,
                HEADER_CACHE_CONTROL: CACHE_CONTROL_VALUE,
            },
        )

    return JSONResponse(
        content=get_manifest_json(manifest),
        media_type=CONTENT_TYPE_JSON,
        headers={
            HEADER_ETAG: etag_header,
            HEADER_CACHE_CONTROL: CACHE_CONTROL_VALUE,
        },
    )
