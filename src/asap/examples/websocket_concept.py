"""WebSocket concept for ASAP protocol (not implemented).

This module describes how WebSocket support would work with ASAP.
No WebSocket server or client is implemented here; the protocol currently
uses HTTP + JSON-RPC. This file is for documentation and design reference.

Concept:
    - Manifest Endpoint can expose an optional "events" URL (wss://...).
    - Same Envelope format: clients send and receive Envelopes as JSON over the wire.
    - Use cases: streaming task updates, real-time notifications, low-latency duplex.

Pseudocode (server side):
    1. Accept WebSocket connection at e.g. /asap/events.
    2. Optional: validate Bearer token from query or first message.
    3. Loop: receive JSON message -> parse as Envelope -> dispatch to handler
       -> optional: send response Envelope(s) back (e.g. task.update, task.response).
    4. On disconnect or error, close connection.

Pseudocode (client side):
    1. Connect to wss://agent.example.com/asap/events (from manifest.endpoints.events).
    2. Send Envelope as JSON: json.dumps(envelope.model_dump()).
    3. Loop: receive JSON -> parse Envelope -> handle (e.g. task.update, task.response).
    4. Optional: ping/pong for keepalive; reconnect with backoff on disconnect.

Message framing:
    - One Envelope per WebSocket text message (JSON).
    - Binary frames could carry compressed or binary-serialized Envelopes (future).

Run:
    uv run python -m asap.examples.websocket_concept
"""

from __future__ import annotations

import argparse
from typing import Sequence

from asap.models.entities import Endpoint
from asap.observability import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Pseudocode: how a WebSocket server would integrate (NOT IMPLEMENTED)
# ---------------------------------------------------------------------------
#
# async def websocket_asap_endpoint(websocket: WebSocket) -> None:
#     await websocket.accept()
#     # Optional: require auth via query param or first message
#     # token = websocket.query_params.get("token") or await read_first_message()
#     # agent_id = token_validator(token); if not agent_id: await websocket.close(4001)
#     try:
#         while True:
#             data = await websocket.receive_text()
#             envelope_dict = json.loads(data)
#             envelope = Envelope.model_validate(envelope_dict)
#             # Dispatch same as HTTP: handler = registry.get(envelope.payload_type)
#             # response_envelopes = await handler(envelope)
#             # for resp in response_envelopes:
#             #     await websocket.send_text(json.dumps(resp.model_dump()))
#     except WebSocketDisconnect:
#         pass
#     finally:
#         await websocket.close()
#
# # In FastAPI: @app.websocket("/asap/events"); def events(ws: WebSocket): asyncio.run(websocket_asap_endpoint(ws))
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Pseudocode: how a WebSocket client would integrate (NOT IMPLEMENTED)
# ---------------------------------------------------------------------------
#
# async def send_envelope_over_websocket(ws: ClientSession, envelope: Envelope) -> None:
#     await ws.send_str(json.dumps(envelope.model_dump()))
#
# async def receive_envelope(ws: ClientSession) -> Envelope | None:
#     msg = await ws.receive()
#     if msg.type == aiohttp.WSMsgType.TEXT:
#         return Envelope.model_validate(json.loads(msg.data))
#     return None
#
# # Client gets events URL from manifest: manifest.endpoints.events (wss://...)
# ---------------------------------------------------------------------------


def get_events_endpoint_concept() -> str:
    """Return the optional WebSocket events URL from an Endpoint (concept).

    In a real implementation, the agent manifest would expose
    endpoints.events (e.g. wss://agent.example.com/asap/events) for
    WebSocket connections. HTTP remains the primary transport.

    Returns:
        Example events URL string for documentation.
    """
    endpoint = Endpoint(
        asap="https://api.example.com/asap",
        events="wss://api.example.com/asap/events",
    )
    return endpoint.events or ""


def run_demo() -> None:
    """Print/log the WebSocket concept summary (no implementation)."""
    events_url = get_events_endpoint_concept()
    logger.info(
        "asap.websocket_concept.summary",
        message="WebSocket support is not implemented; same Envelope format would be used over WS",
        example_events_url=events_url,
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the WebSocket concept demo."""
    parser = argparse.ArgumentParser(
        description="WebSocket concept for ASAP (comments/pseudocode only, not implemented)."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the WebSocket concept demo (documentation only)."""
    parse_args(argv)
    run_demo()


if __name__ == "__main__":
    main()
