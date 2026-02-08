"""ASAP Protocol Discovery Layer.

This module provides discovery of agents via well-known URIs (RFC 8615):
- Well-known endpoint: GET /.well-known/asap/manifest.json for agent manifest
- Future: Lite Registry client, DNS-SD (optional)

Public exports:
    wellknown: Well-known URI handler for manifest and caching
"""

from asap.discovery import wellknown

__all__ = [
    "wellknown",
]
