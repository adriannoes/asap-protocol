"""A2H approval example: notify human and request authorization via A2H Gateway.

Demonstrates the ASAP + A2H integration flow:
1. Create an A2HClient pointing to an A2H Gateway.
2. Optionally discover gateway capabilities.
3. Send an INFORM notification to the human.
4. Send an AUTHORIZE request and wait for approval.

Run:
    uv run python -m asap.examples.a2h_approval
    uv run python -m asap.examples.a2h_approval --gateway-url http://localhost:3000
    uv run python -m asap.examples.a2h_approval --gateway-url http://localhost:3000 --principal-id user@example.com

To run against Twilio's local demo:
    cd <a2h-repo>/demo && npm install && npm start
    uv run python -m asap.examples.a2h_approval --gateway-url http://localhost:3000
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from collections.abc import Sequence

import httpx

from asap.integrations.a2h import A2HApprovalProvider, A2HClient

logger = logging.getLogger(__name__)

DEFAULT_GATEWAY_URL = "http://localhost:3000"
DEFAULT_PRINCIPAL_ID = "user@example.com"
DEFAULT_AGENT_ID = "asap-demo-agent"


async def run_approval_demo(gateway_url: str, principal_id: str) -> None:
    """Discover gateway, send INFORM, then request AUTHORIZE approval."""
    client = A2HClient(gateway_url, agent_id=DEFAULT_AGENT_ID)
    provider = A2HApprovalProvider(client)

    try:
        caps = await client.discover()
        logger.info(
            "a2h.discovery",
            extra={"channels": caps.channels, "a2h_supported": caps.a2h_supported},
        )
    except httpx.HTTPError:
        logger.warning("a2h.discovery_skipped", extra={"reason": "Gateway discovery not available"})

    try:
        interaction_id = await provider.notify(
            principal_id=principal_id,
            body="ASAP agent is starting a task that requires your approval.",
        )
        logger.info("a2h.inform_sent", extra={"interaction_id": interaction_id})
    except Exception as exc:
        logger.error("a2h.inform_failed", extra={"error": str(exc)})
        return

    try:
        result = await provider.request_approval(
            context="Authorize agent to proceed with data processing task?",
            principal_id=principal_id,
            assurance_level="LOW",
            timeout_seconds=60.0,
        )
        logger.info(
            "a2h.approval_result",
            extra={
                "decision": result.decision,
                "interaction_id": result.interaction_id,
            },
        )
    except TimeoutError:
        logger.error("a2h.approval_timeout", extra={"message": "Human did not respond in time"})
    except Exception as exc:
        logger.error("a2h.approval_failed", extra={"error": str(exc)})


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the A2H approval demo."""
    parser = argparse.ArgumentParser(
        description="A2H approval demo: notify human + request authorization via A2H Gateway.",
    )
    parser.add_argument(
        "--gateway-url",
        default=DEFAULT_GATEWAY_URL,
        help=f"A2H gateway base URL (default: {DEFAULT_GATEWAY_URL})",
    )
    parser.add_argument(
        "--principal-id",
        default=DEFAULT_PRINCIPAL_ID,
        help=f"Human principal identifier (default: {DEFAULT_PRINCIPAL_ID})",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point for the A2H approval demo."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = parse_args(argv)
    asyncio.run(run_approval_demo(args.gateway_url, args.principal_id))


if __name__ == "__main__":
    main()
