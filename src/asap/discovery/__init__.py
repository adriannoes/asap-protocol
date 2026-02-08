"""ASAP Protocol Discovery Layer.

This module provides discovery of agents via well-known URIs (RFC 8615):
- Well-known endpoint: GET /.well-known/asap/manifest.json for agent manifest
- Health endpoint: GET /.well-known/asap/health for agent liveness
- Manifest validation: schema, version compatibility, skill matching
- Future: Lite Registry client, DNS-SD (optional)

Public exports:
    wellknown: Well-known URI handler for manifest and caching
    health: Health/liveness endpoint handler
    validation: Manifest validation (schema, version, skills)
"""

from asap.discovery import health
from asap.discovery import validation
from asap.discovery import wellknown

__all__ = [
    "health",
    "validation",
    "wellknown",
]
