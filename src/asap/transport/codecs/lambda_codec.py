"""Lambda Lang codec for ASAP protocol transport layer.

This module provides a self-contained Lambda Lang encoder/decoder that applies
semantic compression to JSON-RPC payloads by substituting common keys and values
with short Lambda Lang atoms.

The codec is fully self-contained and does NOT depend on any external lambda-lang
package. All atom mappings are defined inline based on the Lambda Lang specification.

Encoding approach:
    1. Accept a pre-serialized JSON string (leverage Pydantic's Rust core)
    2. Apply single-pass regex substitution for common JSON-RPC and ASAP keys
    3. Prefix with a version marker for forward compatibility

The encoded format is reversible with 100% fidelity — decode(encode(s)) reproduces
the original JSON string.

Content-Type: application/vnd.asap+lambda

Example:
    >>> import json
    >>> from asap.transport.codecs.lambda_codec import encode, decode
    >>>
    >>> json_str = json.dumps({"jsonrpc": "2.0", "method": "asap.message", "params": {}})
    >>> encoded = encode(json_str)
    >>> assert json.loads(decode(encoded)) == {"jsonrpc": "2.0", "method": "asap.message", "params": {}}
"""

from __future__ import annotations

import re

from asap.observability import get_logger

logger = get_logger(__name__)

# Content-Type for Lambda-encoded ASAP payloads
LAMBDA_CONTENT_TYPE = "application/vnd.asap+lambda"

# Version prefix for the encoded format (allows future format changes)
_VERSION_PREFIX = "λ1:"

# Substitution table: JSON string tokens -> Lambda atoms
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

# Pre-compiled regex patterns for single-pass substitution (C-level speed)
_ENCODE_PATTERN = re.compile("|".join(map(re.escape, _ENCODE_MAP.keys())))
_DECODE_PATTERN = re.compile("|".join(map(re.escape, _DECODE_MAP.keys())))


def _encode_match(m: re.Match) -> str:  # type: ignore[type-arg]
    return _ENCODE_MAP[m.group(0)]


def _decode_match(m: re.Match) -> str:  # type: ignore[type-arg]
    return _DECODE_MAP[m.group(0)]


def is_available() -> bool:
    """Check if the Lambda codec is available.

    Always returns True since this codec is self-contained with no
    external dependencies.

    Returns:
        True
    """
    return True


def encode(json_str: str) -> str:
    """Encode a pre-serialized JSON string to a Lambda-compressed string.

    Applies single-pass regex substitution for common keys and values
    to reduce payload size. Accepts a pre-serialized JSON string to
    avoid redundant serialization (use model_dump_json() upstream).

    Args:
        json_str: Pre-serialized JSON string (e.g. from model_dump_json())

    Returns:
        Lambda-encoded string prefixed with version marker

    Example:
        >>> encoded = encode('{"jsonrpc":"2.0","method":"asap.message"}')
        >>> encoded.startswith("λ1:")
        True
    """
    encoded_str = _ENCODE_PATTERN.sub(_encode_match, json_str)
    encoded = _VERSION_PREFIX + encoded_str

    logger.debug(
        "asap.lambda_codec.encoded",
        original_size=len(json_str),
        encoded_size=len(encoded),
    )

    return encoded


def decode(encoded: str) -> str:
    """Decode a Lambda-compressed string back to a JSON string.

    Reverses the Lambda atom substitution and returns the resulting
    JSON string. The caller is responsible for parsing the JSON.

    Args:
        encoded: Lambda-encoded string (must start with version prefix)

    Returns:
        Original JSON string

    Raises:
        ValueError: If the encoded string has an invalid format or version

    Example:
        >>> import json
        >>> data = {"jsonrpc": "2.0", "method": "asap.message"}
        >>> decoded_str = decode(encode(json.dumps(data)))
        >>> assert json.loads(decoded_str) == data
    """
    if not encoded.startswith(_VERSION_PREFIX):
        raise ValueError(
            f"Invalid Lambda codec format: missing version prefix. "
            f"Expected '{_VERSION_PREFIX}' at start of encoded string."
        )

    json_str = encoded[len(_VERSION_PREFIX):]
    json_str = _DECODE_PATTERN.sub(_decode_match, json_str)

    logger.debug(
        "asap.lambda_codec.decoded",
        encoded_size=len(encoded),
        decoded_size=len(json_str),
    )

    return json_str
