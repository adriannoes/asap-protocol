"""Transport-layer protocol errors for the ASAP client pairing paths.

These errors are raised on the CLIENT side when a remote peer returns a response
that violates a request/response binding invariant (e.g. a ``correlation_id``
that does not match the request id). They are distinct from the structural
``Envelope`` validation in ``asap.models.envelope``: the envelope may be
well-formed yet still be the wrong response for the in-flight request, which
under concurrency would mix request/response pairs.

The taxonomy code and JSON-RPC slot reuse ``asap:protocol/malformed_envelope``
(``RPC_MALFORMED_ENVELOPE``) to stay consistent with the existing error style
(``RemoteRPCError``, whose ``is_recoverable`` property distinguishes fatal
from retryable remote JSON-RPC failures after the v2.5.1 twin-class collapse).

This module is also the single source of truth for the response-binding checks
(``assert_correlation_binds`` / ``assert_stream_correlation_binds``) shared by
the HTTP client and WebSocket transport, so the binding contract cannot drift
between unary and streaming pairing sites (B6/BUG #6, CR#4).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from asap.errors import FatalError, RPC_MALFORMED_ENVELOPE
from asap.models.envelope import _normalize_payload_type

if TYPE_CHECKING:
    from asap.models.envelope import Envelope

__all__ = [
    "RESPONSE_PAYLOAD_KEYS",
    "STREAM_BOUND_PAYLOAD_KEYS",
    "ProtocolCorrelationError",
    "assert_correlation_binds",
    "assert_stream_correlation_binds",
]


# Unary response payload types whose correlation_id must bind to the request id
# (B6/BUG #6).
RESPONSE_PAYLOAD_KEYS = frozenset({"taskresponse", "mcptoolresult", "mcpresourcedata"})

# Streaming pairing is stricter than unary receive(): ``TaskStream`` chunks are
# also bound because they are emitted in answer to one specific request stream
# (CR#4).
STREAM_BOUND_PAYLOAD_KEYS = RESPONSE_PAYLOAD_KEYS | frozenset({"taskstream"})


class ProtocolCorrelationError(FatalError):
    """Raised when a response envelope's ``correlation_id`` does not bind to its request.

    A remote peer may return a structurally valid response (non-empty
    ``correlation_id``) that nonetheless does not match the id of the in-flight
    request. Accepting it would pair a response with the wrong request under
    concurrency, so the client MUST reject it.

    Attributes:
        request_id: The id of the request envelope we were awaiting a response for.
        correlation_id: The ``correlation_id`` actually carried by the response.
    """

    def __init__(
        self,
        request_id: str,
        correlation_id: str | None,
        details: dict[str, Any] | None = None,
    ) -> None:
        message = f"correlation_id mismatch: expected {request_id!r}, got {correlation_id!r}"
        super().__init__(
            "asap:protocol/malformed_envelope",
            message,
            {
                "request_id": request_id,
                "correlation_id": correlation_id,
                **(details or {}),
            },
            rpc_code=RPC_MALFORMED_ENVELOPE,
        )
        self.request_id = request_id
        self.correlation_id = correlation_id


def assert_correlation_binds(request_envelope_id: str, response: "Envelope") -> None:
    """Assert that a response envelope binds to the request it answers (B6/BUG #6).

    Envelope-level validation only guarantees the response carries a non-empty
    ``correlation_id``. This BINDING check ensures that id equals the request
    envelope id, so a buggy/malicious server cannot return a response meant for
    another request and have the client accept it under concurrency or in a
    batch.

    Non-response payload types (server-push notifications, acks, streaming
    chunks) intentionally skip the binding check because unary pairing sites do
    not bind them to a specific request id.

    Args:
        request_envelope_id: The ``id`` of the request envelope we are pairing
            the response against.
        response: The response envelope received from the peer.

    Raises:
        ProtocolCorrelationError: If ``response`` is a response payload type
            whose ``correlation_id`` does not equal ``request_envelope_id``.
    """
    if _normalize_payload_type(response.payload_type) not in RESPONSE_PAYLOAD_KEYS:
        return
    if response.correlation_id == request_envelope_id:
        return
    raise ProtocolCorrelationError(
        request_id=request_envelope_id,
        correlation_id=response.correlation_id,
    )


def assert_stream_correlation_binds(request_envelope_id: str, response: "Envelope") -> None:
    """Assert that a streamed envelope binds to the request that opened the stream.

    Streaming transport pairs each yielded chunk to a single request initiated
    by the client. In addition to regular response payloads, ``TaskStream``
    chunks MUST carry ``correlation_id == request_envelope_id`` so a
    buggy/malicious server cannot splice another request's chunks into the
    active stream (CR#4).

    Args:
        request_envelope_id: The ``id`` of the request envelope that opened the
            stream.
        response: The streamed envelope received from the peer.

    Raises:
        ProtocolCorrelationError: If ``response`` is a stream-bound payload type
            whose ``correlation_id`` does not equal ``request_envelope_id``.
    """
    if _normalize_payload_type(response.payload_type) not in STREAM_BOUND_PAYLOAD_KEYS:
        return
    if response.correlation_id == request_envelope_id:
        return
    raise ProtocolCorrelationError(
        request_id=request_envelope_id,
        correlation_id=response.correlation_id,
    )
