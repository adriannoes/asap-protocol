"""OpenAPI 3.x → ASAP adapter (Sprint S1)."""

from __future__ import annotations

from asap.adapters.openapi.factory import (
    PETSTORE_OPENAPI_URL,
    OpenAPIAdapterBundle,
    create_from_openapi,
)

__all__ = [
    "PETSTORE_OPENAPI_URL",
    "OpenAPIAdapterBundle",
    "create_from_openapi",
]
