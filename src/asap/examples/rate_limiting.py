"""Rate limiting strategies example for ASAP protocol.

This module shows how rate limiting is configured and how per-sender
and per-endpoint patterns work with the server.

Patterns:
    1. Global limit: create_app(..., rate_limit="10/second;100/minute") or ASAP_RATE_LIMIT env.
    2. Per-sender: key_func returns sender URN when available (envelope.sender), else IP.
    3. Per-endpoint: apply different limit strings to different routes (e.g. /asap vs /metrics).

Run:
    uv run python -m asap.examples.rate_limiting
"""

from __future__ import annotations

import argparse
import os
from typing import Sequence

from asap.observability import get_logger
from asap.transport.middleware import (
    DEFAULT_RATE_LIMIT,
    create_limiter,
)

logger = get_logger(__name__)


def get_server_rate_limit_config() -> str:
    """Return the effective rate limit string used by create_app.

    create_app uses rate_limit parameter or ASAP_RATE_LIMIT env.
    Default is "10/second;100/minute" (burst + sustained).

    Returns:
        Rate limit string (e.g. "10/second;100/minute").
    """
    return os.environ.get("ASAP_RATE_LIMIT", DEFAULT_RATE_LIMIT)


def per_sender_key_concept(sender_urn: str | None, client_ip: str) -> str:
    """Build a rate limit key for per-sender strategy (concept).

    When the envelope sender is known (e.g. after auth or body parse), key by sender
    so each agent has its own quota. Otherwise fall back to client IP.
    The server's _get_sender_from_envelope(request) does this: it tries envelope.sender
    then falls back to get_remote_address(request).

    Args:
        sender_urn: Sender URN from envelope, or None if not yet available.
        client_ip: Client IP address (fallback key).

    Returns:
        Key string for the rate limiter (e.g. "urn:asap:agent:client-a" or "192.168.1.1").
    """
    if sender_urn:
        return sender_urn
    return client_ip


def per_endpoint_limits_concept() -> dict[str, str]:
    """Return example per-endpoint limit strings (concept).

    Different routes can have different limits, e.g. strict for /asap and
    looser for read-only /.well-known/asap/manifest.json.
    The server currently applies one limit to the /asap route; this shows
    the pattern for multiple routes.

    Returns:
        Map from route/path description to limit string.
    """
    return {
        "asap": "10/second;100/minute",  # Burst + sustained for main endpoint
        "metrics": "10/minute",  # Lower limit for metrics scraping
        "manifest": "200/minute",  # Higher limit for discovery
    }


def run_demo() -> None:
    """Demonstrate rate limiting config: global, per-sender key, per-endpoint pattern."""
    # Global: server config
    effective_limit = get_server_rate_limit_config()
    logger.info(
        "asap.rate_limiting.server_config",
        rate_limit=effective_limit,
        env_var="ASAP_RATE_LIMIT",
    )

    # Per-sender: key concept (sender URN vs IP fallback)
    key_sender = per_sender_key_concept("urn:asap:agent:client-a", "192.168.1.1")
    key_ip = per_sender_key_concept(None, "192.168.1.1")
    logger.info(
        "asap.rate_limiting.per_sender_key",
        when_sender_known=key_sender,
        when_fallback=key_ip,
    )

    # Per-endpoint: different limits per route
    limits = per_endpoint_limits_concept()
    logger.info(
        "asap.rate_limiting.per_endpoint",
        limits=limits,
        message="Apply @limiter.limit(limit)(handler) per route",
    )

    # create_limiter uses _get_sender_from_envelope as key_func
    _limiter = create_limiter(["50/minute"])
    logger.info(
        "asap.rate_limiting.limiter_created",
        limits=["50/minute"],
        key_func="get_sender_from_envelope (sender or IP)",
    )

    # rate_limit_handler is used by the server for 429 responses
    logger.info(
        "asap.rate_limiting.handler",
        message="rate_limit_handler returns JSON-RPC error with Retry-After header",
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the rate limiting demo."""
    parser = argparse.ArgumentParser(
        description="Rate limiting strategies: per-sender, per-endpoint patterns."
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the rate limiting demo."""
    parse_args(argv)
    run_demo()


if __name__ == "__main__":
    main()
