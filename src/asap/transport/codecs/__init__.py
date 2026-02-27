"""Codec support for ASAP protocol transport layer.

This module provides content-type codecs for encoding and decoding
ASAP JSON-RPC payloads into alternative wire formats.

Currently supported codecs:
- Lambda Lang: Semantic compression using Lambda Lang atom substitution

Example:
    >>> from asap.transport.codecs import lambda_codec
    >>>
    >>> data = {"jsonrpc": "2.0", "method": "asap.message", "params": {"envelope": {}}}
    >>> encoded = lambda_codec.encode(data)
    >>> decoded = lambda_codec.decode(encoded)
    >>> assert decoded == data
"""

from __future__ import annotations

from asap.transport.codecs.lambda_codec import (
    LAMBDA_CONTENT_TYPE,
    decode,
    encode,
    is_available,
)

__all__ = [
    "LAMBDA_CONTENT_TYPE",
    "decode",
    "encode",
    "is_available",
]
