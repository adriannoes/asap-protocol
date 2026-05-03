"""WWW-Authenticate ASAP challenge for HTTP 401 responses (CHAL-001)."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable

from pydantic import ConfigDict, Field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from asap.discovery import wellknown
from asap.models.base import ASAPBaseModel

# HTTP 401
HTTP_UNAUTHORIZED = 401

_ASAP_SCHEME_RE = re.compile(r"\bASAP\b", re.IGNORECASE)


class WWWAuthenticateASAPChallenge(ASAPBaseModel):
    """Parsed or constructed ``WWW-Authenticate: ASAP`` challenge parameters."""

    model_config = ConfigDict(extra="forbid")

    discovery: str = Field(
        ..., min_length=1, description="Absolute URL of the ASAP manifest (discovery)."
    )


def format_www_authenticate_asap(discovery_url: str) -> str:
    """Return a ``WWW-Authenticate`` header value for the ASAP scheme."""
    escaped = discovery_url.replace("\\", "\\\\").replace('"', '\\"')
    return f'ASAP discovery="{escaped}"'


def parse_www_authenticate_asap(header_value: str | None) -> str | None:
    """Extract ``discovery`` URL from a ``WWW-Authenticate`` header, if present."""
    if not header_value or not _ASAP_SCHEME_RE.search(header_value):
        return None
    match = re.search(r'discovery\s*=\s*"((?:[^"\\]|\\.)*)"', header_value, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1)
    return raw.replace('\\"', '"').replace("\\\\", "\\")


def default_manifest_discovery_url(asap_http_endpoint: str) -> str:
    """Build ``/.well-known/asap/manifest.json`` on the same origin as *asap_http_endpoint*."""
    from urllib.parse import urlparse

    parsed = urlparse(asap_http_endpoint.strip())
    if not parsed.scheme or not parsed.netloc:
        msg = f"Invalid ASAP endpoint URL for discovery: {asap_http_endpoint!r}"
        raise ValueError(msg)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    return origin.rstrip("/") + wellknown.WELLKNOWN_MANIFEST_PATH


class WWWAuthenticateASAPMiddleware(BaseHTTPMiddleware):
    """Attach ``WWW-Authenticate: ASAP discovery=\"...\"`` to selected HTTP 401 responses."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_discovery_url: str,
        path_prefixes: tuple[str, ...] | None = None,
        path_matcher: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__(app)
        self._default_discovery_url = default_discovery_url
        self._path_prefixes = path_prefixes
        self._path_matcher = path_matcher

    def _should_challenge(self, request: Request) -> bool:
        if self._path_matcher is not None:
            return self._path_matcher(request.url.path)
        if self._path_prefixes:
            return any(request.url.path.startswith(p) for p in self._path_prefixes)
        return True

    def _discovery_for(self, request: Request) -> str:
        override = getattr(request.state, "asap_challenge_discovery_url", None)
        if isinstance(override, str) and override.strip():
            return override.strip()
        return self._default_discovery_url

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        if response.status_code != HTTP_UNAUTHORIZED:
            return response
        if not self._should_challenge(request):
            return response
        discovery = self._discovery_for(request)
        header_value = format_www_authenticate_asap(discovery)
        existing = response.headers.get("www-authenticate")
        if existing:
            response.headers["WWW-Authenticate"] = f"{existing}, {header_value}"
        else:
            response.headers["WWW-Authenticate"] = header_value
        return response
