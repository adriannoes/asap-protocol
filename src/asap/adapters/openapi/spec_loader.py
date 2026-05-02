"""Load OpenAPI 3.x documents from URLs or local JSON files."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from openapi_pydantic import parse_obj
from openapi_pydantic.v3.v3_0.open_api import OpenAPI as OpenAPI_3_0
from openapi_pydantic.v3.v3_1.open_api import OpenAPI as OpenAPI_3_1
from pydantic import ValidationError

OpenAPIDocument = OpenAPI_3_0 | OpenAPI_3_1

_DEFAULT_HTTP_TIMEOUT = 30.0

logger = logging.getLogger(__name__)


class OpenAPISpecError(ValueError):
    """The document is missing, not valid OpenAPI 3.x, or could not be loaded."""


def _is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


async def _load_json_from_url(url: str, client: httpx.AsyncClient) -> dict[str, Any]:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "OpenAPI spec HTTP fetch failed url=%r status=%s",
            url,
            exc.response.status_code,
        )
        raise OpenAPISpecError(
            f"Failed to fetch OpenAPI document from {url!r} (HTTP {exc.response.status_code}).",
        ) from exc
    except httpx.HTTPError as exc:
        logger.error("OpenAPI spec HTTP error url=%r", url)
        raise OpenAPISpecError(f"HTTP error while fetching OpenAPI document from {url!r}.") from exc
    try:
        data = response.json()
    except json.JSONDecodeError as exc:
        logger.error("OpenAPI URL did not return JSON url=%r", url)
        raise OpenAPISpecError(f"OpenAPI URL did not return JSON: {url!r}.") from exc
    if not isinstance(data, dict):
        logger.error("OpenAPI URL root is not a JSON object url=%r", url)
        raise OpenAPISpecError(f"OpenAPI root must be a JSON object: {url!r}.")
    return data


async def _load_json_from_path(path: Path) -> dict[str, Any]:
    """Read a local spec without blocking the event loop (filesystem + decode in worker thread)."""

    def _sync_load() -> dict[str, Any]:
        if not path.is_file():
            raise OpenAPISpecError(f"OpenAPI spec file not found: {path}")
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise OpenAPISpecError(f"Cannot read OpenAPI spec file: {path}") from exc
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAPISpecError(f"OpenAPI spec file is not valid JSON: {path}") from exc
        if not isinstance(data, dict):
            raise OpenAPISpecError(f"OpenAPI root must be a JSON object: {path}")
        return data

    try:
        return await asyncio.to_thread(_sync_load)
    except OpenAPISpecError as exc:
        logger.error("OpenAPI spec load from path failed path=%s: %s", path, exc)
        raise


def _ensure_openapi_version_3_x(data: dict[str, Any]) -> None:
    version = data.get("openapi")
    if version is None:
        logger.error("OpenAPI document missing required 'openapi' field")
        raise OpenAPISpecError("Missing required 'openapi' field (expected OpenAPI 3.x).")
    if not isinstance(version, str):
        logger.error(
            "OpenAPI 'openapi' version field must be a string, got %s", type(version).__name__
        )
        raise OpenAPISpecError("'openapi' version field must be a string.")
    if not version.startswith("3."):
        logger.error("Unsupported OpenAPI version %r (only 3.x supported)", version)
        raise OpenAPISpecError(
            f"Unsupported OpenAPI version {version!r}; only 3.x is supported.",
        )


def _parse_openapi_document(data: dict[str, Any]) -> OpenAPIDocument:
    try:
        parsed: OpenAPIDocument = parse_obj(data)
    except ValidationError as exc:
        logger.error("Invalid OpenAPI document: %s", exc)
        raise OpenAPISpecError(f"Invalid OpenAPI document: {exc}") from exc
    return parsed


async def load_spec(
    url_or_path: str | Path,
    *,
    http_client: httpx.AsyncClient | None = None,
) -> OpenAPIDocument:
    """Fetch or read an OpenAPI 3.x document and validate it with ``openapi-pydantic``.

    Local files must be UTF-8 JSON (``.json``). YAML is not supported yet.

    Args:
        url_or_path: ``https://`` / ``http://`` URL or filesystem path string / :class:`~pathlib.Path`.
        http_client: Optional shared client for URL loads (e.g. tests with
            :class:`httpx.MockTransport`). When ``None``, a temporary client is used.

    Returns:
        Parsed OpenAPI 3.0 or 3.1 root model.

    Raises:
        OpenAPISpecError: Missing file, non-JSON payload, non-3.x version, or schema errors.
    """
    source = str(url_or_path) if isinstance(url_or_path, Path) else url_or_path
    logger.debug("Loading OpenAPI spec from %r", source)
    if isinstance(url_or_path, Path):
        data = await _load_json_from_path(url_or_path)
    elif isinstance(url_or_path, str) and _is_http_url(url_or_path):
        if http_client is None:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=_DEFAULT_HTTP_TIMEOUT,
            ) as client:
                data = await _load_json_from_url(url_or_path, client)
        else:
            data = await _load_json_from_url(url_or_path, http_client)
    else:
        data = await _load_json_from_path(Path(url_or_path))

    _ensure_openapi_version_3_x(data)
    doc = _parse_openapi_document(data)
    logger.info("Loaded OpenAPI spec source=%r openapi=%r", source, data.get("openapi"))
    return doc


__all__ = ["OpenAPIDocument", "OpenAPISpecError", "load_spec"]
