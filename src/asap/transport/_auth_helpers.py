"""Shared authentication helpers for transport route modules."""

from __future__ import annotations

from fastapi import Request


def bearer_token_from_request(request: Request) -> str | None:
    """Return raw Bearer token from the ``Authorization`` header, if present."""
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        return None
    return auth[7:].strip() or None
