"""Thin starter: invoke the MCP Auth Bridge parent client via subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# examples/starters/mcp-auth-bridge → examples/
_PARENT = Path(__file__).resolve().parents[2] / "mcp_auth_bridge" / "client.py"


def main() -> None:
    """Forward argv to ``examples/mcp_auth_bridge/client.py`` and exit with its code.

    Example::

        uv run python examples/starters/mcp-auth-bridge/run.py
    """
    if not _PARENT.is_file():
        print(
            f"Parent example not found at {_PARENT} "
            f"(expected examples/mcp_auth_bridge/client.py relative to repo).",
            file=sys.stderr,
        )
        sys.exit(1)
    completed = subprocess.run(
        [sys.executable, str(_PARENT), *sys.argv[1:]],
        check=False,
    )
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
