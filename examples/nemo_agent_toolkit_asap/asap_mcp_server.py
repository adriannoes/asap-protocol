"""ASAP protected MCP stdio server for the NeMo Agent Toolkit demo.

Reuses ``examples/mcp_auth_bridge/server.py`` (echo + secure_action + protect_server)
and injects the minted demo Agent JWT into ``ASAP_AGENT_JWT`` so NAT ``mcp_client``
(stdio) can call protected tools without ``_meta.asap_agent_jwt``.

NAT will not send ASAP ``_meta``; this is a **dev-only** env fallback
(``allow_env_jwt_fallback=True``). Do not deploy unchanged.

Run (from repo root)::

    uv run python examples/nemo_agent_toolkit_asap/asap_mcp_server.py

Negative path (no env JWT)::

    uv run python examples/nemo_agent_toolkit_asap/asap_mcp_server.py --no-env-jwt
"""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from asap.observability.logging import configure_logging

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MCP_AUTH_BRIDGE_SERVER = _REPO_ROOT / "examples" / "mcp_auth_bridge" / "server.py"
_ENV_JWT_KEY = "ASAP_AGENT_JWT"


def route_observability_logs_to_stderr() -> None:
    """Send ASAP structlog to stderr so MCP stdout stays JSON-RPC-only.

    With ``ASAP_AGENT_JWT`` set, ``ProtectedMCPServer`` emits
    ``mcp.tool.public_jwt_ignored`` / ``mcp.tool.authorized`` via the default
    ``StreamHandler(sys.stdout)``. Those lines break NAT ``mcp_client`` and ASAP
    ``MCPClient`` parsers on the next ``tools/call``.

    Example:
        route_observability_logs_to_stderr()
        await server.run_stdio()
    """
    configure_logging(force=True)
    root = logging.getLogger()
    formatter = root.handlers[0].formatter if root.handlers else None
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    if formatter is not None:
        handler.setFormatter(formatter)
    root.addHandler(handler)


def _load_mcp_auth_bridge_server() -> ModuleType:
    """Import the mcp_auth_bridge example server module by file path.

    Example:
        module = _load_mcp_auth_bridge_server()
        server, identity = await module.build_protected_server()
    """
    if not _MCP_AUTH_BRIDGE_SERVER.is_file():
        raise FileNotFoundError(
            f"mcp_auth_bridge server missing: expected {_MCP_AUTH_BRIDGE_SERVER}, "
            "got missing file (run from ASAP repo checkout)",
        )
    spec = importlib.util.spec_from_file_location(
        "mcp_auth_bridge_server_for_nat",
        _MCP_AUTH_BRIDGE_SERVER,
    )
    if spec is None or spec.loader is None:
        raise ImportError(
            f"cannot load mcp_auth_bridge server from {_MCP_AUTH_BRIDGE_SERVER!s}",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def inject_demo_jwt_env(demo_jwt: str) -> None:
    """Put the minted demo JWT into the process env for ``allow_env_jwt_fallback``.

    Args:
        demo_jwt: Agent JWT string minted by the mcp_auth_bridge demo.

    Example:
        inject_demo_jwt_env(identity.demo_jwt)
    """
    if not demo_jwt or not isinstance(demo_jwt, str):
        raise ValueError(
            f"demo_jwt must be a non-empty str, got {type(demo_jwt).__name__}: {demo_jwt!r}",
        )
    os.environ[_ENV_JWT_KEY] = demo_jwt


def _print_path_a_startup_banner(identity: Any, *, inject_env_jwt: bool) -> None:
    """Print Path A warnings on stderr without dumping the minted JWT.

    The mcp_auth_bridge helper ``_print_startup_instructions`` prints the live
    Agent JWT. Calling it from ``build_and_prepare_server`` can leak tokens into
    pytest/smoke captured stderr and CI logs when assertions concatenate stderr.
    Keep a local banner for interactive stdio only and never print
    ``identity.demo_jwt``.

    Args:
        identity: Demo identity from mcp_auth_bridge (agent_id for operators).
        inject_env_jwt: Whether this process injects ``ASAP_AGENT_JWT``.
    """
    agent_id = getattr(
        getattr(identity, "agent_session", None),
        "agent_id",
        "<unknown>",
    )
    if inject_env_jwt:
        print(
            f"WARNING: {_ENV_JWT_KEY} injected for NAT Path A (dev-only env JWT fallback). "
            "Do not deploy / do not use in multi-tenant production. "
            "NAT OAuth2/Keycloak is not used.",
            file=sys.stderr,
            flush=True,
        )
    else:
        print(
            f"WARNING: --no-env-jwt: {_ENV_JWT_KEY} not injected. "
            "Protected tools require _meta.asap_agent_jwt or a pre-set env JWT.",
            file=sys.stderr,
            flush=True,
        )
    print(
        f"ASAP Path A MCP server ready (agent_id={agent_id}). "
        "Demo JWT is held in-process only — not printed.",
        file=sys.stderr,
        flush=True,
    )


async def build_and_prepare_server(
    *,
    inject_env_jwt: bool = True,
    print_instructions: bool = False,
) -> tuple[Any, Any]:
    """Build the protected MCP server and optionally inject ``ASAP_AGENT_JWT``.

    Args:
        inject_env_jwt: When True (default), set ``ASAP_AGENT_JWT`` from the
            minted demo token so NAT stdio clients need no ``_meta``.
        print_instructions: When True, print a stderr banner (stdio ``main`` /
            ``_run_stdio`` only). Default False so in-process pytest/smoke do
            not dump operator noise or risk leaking tokens into CI logs.

    Returns:
        ``(protected_server, demo_identity)`` from mcp_auth_bridge.

    Example:
        server, identity = await build_and_prepare_server(inject_env_jwt=True)
    """
    module = _load_mcp_auth_bridge_server()
    server, identity = await module.build_protected_server()
    if inject_env_jwt:
        inject_demo_jwt_env(identity.demo_jwt)
    if print_instructions:
        _print_path_a_startup_banner(identity, inject_env_jwt=inject_env_jwt)
    return server, identity


async def _run_stdio(*, inject_env_jwt: bool) -> None:
    """Start the protected MCP server on stdio."""
    route_observability_logs_to_stderr()
    server, _identity = await build_and_prepare_server(
        inject_env_jwt=inject_env_jwt,
        print_instructions=True,
    )
    await server.run_stdio()


def main() -> None:
    """Parse CLI args and run the ASAP protected MCP server for NAT Path A."""
    parser = argparse.ArgumentParser(
        description=(
            "ASAP MCP Auth Bridge stdio server for NeMo Agent Toolkit Path A "
            "(env JWT fallback for NAT mcp_client)"
        ),
    )
    parser.add_argument(
        "--no-env-jwt",
        action="store_true",
        help=(f"Do not inject minted demo JWT into {_ENV_JWT_KEY} (negative path / require _meta)"),
    )
    args = parser.parse_args()
    asyncio.run(_run_stdio(inject_env_jwt=not args.no_env_jwt))


if __name__ == "__main__":
    main()
