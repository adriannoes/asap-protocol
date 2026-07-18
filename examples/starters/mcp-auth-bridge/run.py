"""Thin starter: invoke the MCP Auth Bridge parent client via subprocess."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure examples/starters is importable when this file is run as a script.
_STARTERS_DIR = Path(__file__).resolve().parents[1]
if str(_STARTERS_DIR) not in sys.path:
    sys.path.insert(0, str(_STARTERS_DIR))

from _forward_smoke import forward_parent  # noqa: E402

# examples/starters/mcp-auth-bridge → examples/
_PARENT = Path(__file__).resolve().parents[2] / "mcp_auth_bridge" / "client.py"


def main() -> None:
    """Forward argv to ``examples/mcp_auth_bridge/client.py`` and exit with its code.

    Example::

        uv run python examples/starters/mcp-auth-bridge/run.py
    """
    forward_parent(
        _PARENT,
        label="MCP Auth Bridge",
        expected_relpath="examples/mcp_auth_bridge/client.py",
    )


if __name__ == "__main__":
    main()
