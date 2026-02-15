"""Log sanitization utilities for sensitive data protection.

This module provides functions to sanitize sensitive data before logging
to prevent credential leaks, token exposure, and other security issues.

Example:
    >>> from asap.utils.sanitization import sanitize_token, sanitize_nonce, sanitize_url
    >>>
    >>> # Sanitize a token (shows only first 8 characters)
    >>> token = "sk_live_1234567890abcdef"
    >>> sanitize_token(token)  # Returns: "sk_live_..."
    >>>
    >>> # Sanitize a nonce (shows first 8 characters + "...")
    >>> nonce = "a1b2c3d4e5f6g7h8i9j0"
    >>> sanitize_nonce(nonce)  # Returns: "a1b2c3d4..."
    >>>
    >>> # Sanitize a URL with credentials
    >>> url = "https://user:password@example.com/api"
    >>> sanitize_url(url)  # Returns: "https://user:***@example.com/api"
"""

import re
from urllib.parse import urlparse, urlunparse

# Sanitization configuration
SANITIZE_PREFIX_LENGTH = 8
"""Number of characters to show when truncating sensitive values.

This constant defines how many characters of a sensitive value (token, nonce)
are preserved when sanitizing for logs. The value balances security (preventing
full exposure) with debuggability (allowing identification of value types).
"""


def sanitize_token(token: str) -> str:
    if not token:
        return ""
    if len(token) <= SANITIZE_PREFIX_LENGTH:
        return token
    return f"{token[:SANITIZE_PREFIX_LENGTH]}..."


def sanitize_nonce(nonce: str) -> str:
    if not nonce:
        return ""
    if len(nonce) <= SANITIZE_PREFIX_LENGTH:
        return nonce
    return f"{nonce[:SANITIZE_PREFIX_LENGTH]}..."


def sanitize_url(url: str) -> str:
    if not url:
        return ""

    try:
        parsed = urlparse(url)
        if (parsed.username or parsed.password) and parsed.password:
            netloc = f"{parsed.username}:***@{parsed.hostname}"
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"
            return urlunparse(
                (
                    parsed.scheme,
                    netloc,
                    parsed.path,
                    parsed.params,
                    parsed.query,
                    parsed.fragment,
                )
            )
        return url
    except Exception:
        return re.sub(r"://[^:]+:[^@]+@", r"://***:***@", url)


__all__ = [
    "sanitize_token",
    "sanitize_nonce",
    "sanitize_url",
]
