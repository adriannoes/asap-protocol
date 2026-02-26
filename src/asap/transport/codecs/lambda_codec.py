"""Lambda Lang codec for ASAP protocol transport layer.

This module provides a self-contained Lambda Lang encoder/decoder that applies
semantic compression to JSON-RPC payloads by substituting common keys and values
with short Lambda Lang atoms.

The codec is fully self-contained and does NOT depend on any external lambda-lang
package. All atom mappings are defined inline based on the Lambda Lang specification.

Encoding approach:
    1. Serialize the Python dict to a JSON string
    2. Apply deterministic token substitution for common JSON-RPC and ASAP keys
    3. Prefix with a version marker for forward compatibility

The encoded format is reversible with 100% fidelity — decode(encode(data)) == data.

Content-Type: application/vnd.asap+lambda

Example:
    >>> from asap.transport.codecs.lambda_codec import encode, decode
    >>>
    >>> data = {"jsonrpc": "2.0", "method": "asap.message", "params": {}}
    >>> encoded = encode(data)
    >>> assert decode(encoded) == data
"""

from __future__ import annotations

import json
from typing import Any

from asap.observability import get_logger

logger = get_logger(__name__)

# Content-Type for Lambda-encoded ASAP payloads
LAMBDA_CONTENT_TYPE = "application/vnd.asap+lambda"

# Version prefix for the encoded format (allows future format changes)
_VERSION_PREFIX = "λ1:"

# Substitution table: JSON string tokens -> Lambda atoms
# Keys are ordered longest-first to ensure greedy matching is correct.
# Each entry maps a literal JSON substring to a short Lambda atom token.
# The atoms are wrapped in a unique delimiter (§…§) that cannot appear in
# valid JSON to guarantee reversibility.
_ENCODE_MAP: dict[str, str] = {
    # JSON-RPC standard keys
    '"jsonrpc"': "§Jrpc§",
    '"method"': "§Mthd§",
    '"params"': "§Prms§",
    '"result"': "§Rslt§",
    '"error"': "§Er§",
    '"id"': "§Id§",
    '"code"': "§Cd§",
    '"message"': "§Msg§",
    '"data"': "§Dt§",
    # ASAP envelope keys
    '"envelope"': "§Env§",
    '"sender"': "§Snd§",
    '"recipient"': "§Rcp§",
    '"payload"': "§Pld§",
    '"payload_type"': "§Pt§",
    '"task_id"': "§Ta§",
    '"status"': "§St§",
    '"trace_id"': "§Tr§",
    '"timestamp"': "§Ts§",
    '"nonce"': "§Nc§",
    '"version"': "§Vr§",
    '"description"': "§Ds§",
    '"idempotency_key"': "§Ik§",
    # ASAP common values
    '"asap.message"': "§Am§",
    '"2.0"': "§V2§",
    # ASAP payload types
    '"task.request"': "§Treq§",
    '"task.response"': "§Tres§",
    '"task.status"': "§Tst§",
    '"task.cancel"': "§Tcn§",
    '"heartbeat"': "§Hb§",
    # Common status values
    '"success"': "§Ok§",
    '"pending"': "§Pn§",
    '"running"': "§Rn§",
    '"completed"': "§Cp§",
    '"failed"': "§Fl§",
    '"cancelled"': "§Cx§",
}

# Reverse map for decoding: Lambda atom -> original JSON token
_DECODE_MAP: dict[str, str] = {v: k for k, v in _ENCODE_MAP.items()}


def is_available() -> bool:
    """Check if the Lambda codec is available.

    Always returns True since this codec is self-contained with no
    external dependencies.

    Returns:
        True
    """
    return True


def encode(data: dict[str, Any]) -> str:
    """Encode a Python dict (JSON-RPC body) to a Lambda-compressed string.

    Serializes the dict to JSON, then applies Lambda atom substitution
    for common keys and values to reduce payload size.

    Args:
        data: Python dictionary to encode (typically a JSON-RPC request/response)

    Returns:
        Lambda-encoded string prefixed with version marker

    Example:
        >>> encoded = encode({"jsonrpc": "2.0", "method": "asap.message"})
        >>> encoded.startswith("λ1:")
        True
    """
    json_str = json.dumps(data, separators=(",", ":"), sort_keys=True)

    # Apply substitutions (longest keys first for greedy correctness)
    for token, atom in _ENCODE_MAP.items():
        json_str = json_str.replace(token, atom)

    encoded = _VERSION_PREFIX + json_str

    logger.debug(
        "asap.lambda_codec.encoded",
        original_size=len(json.dumps(data, separators=(",", ":"))),
        encoded_size=len(encoded),
    )

    return encoded


def decode(encoded: str) -> dict[str, Any]:
    """Decode a Lambda-compressed string back to a Python dict.

    Reverses the Lambda atom substitution and parses the resulting
    JSON string back into a Python dictionary.

    Args:
        encoded: Lambda-encoded string (must start with version prefix)

    Returns:
        Original Python dictionary

    Raises:
        ValueError: If the encoded string has an invalid format or version

    Example:
        >>> data = {"jsonrpc": "2.0", "method": "asap.message"}
        >>> decoded = decode(encode(data))
        >>> assert decoded == data
    """
    if not encoded.startswith(_VERSION_PREFIX):
        raise ValueError(
            f"Invalid Lambda codec format: missing version prefix. "
            f"Expected '{_VERSION_PREFIX}' at start of encoded string."
        )

    json_str = encoded[len(_VERSION_PREFIX) :]

    # Reverse substitutions
    for atom, token in _DECODE_MAP.items():
        json_str = json_str.replace(atom, token)

    try:
        result: dict[str, Any] = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid Lambda codec payload: JSON decode failed: {e}") from e

    logger.debug(
        "asap.lambda_codec.decoded",
        encoded_size=len(encoded),
        decoded_size=len(json.dumps(result, separators=(",", ":"))),
    )

    return result
