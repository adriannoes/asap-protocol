"""Thin starter: invoke the OpenAPI PetStore parent example via subprocess."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure examples/starters is importable when this file is run as a script.
_STARTERS_DIR = Path(__file__).resolve().parents[1]
if str(_STARTERS_DIR) not in sys.path:
    sys.path.insert(0, str(_STARTERS_DIR))

from _forward_smoke import forward_parent  # noqa: E402

# examples/starters/openapi-provider → examples/
_PARENT = Path(__file__).resolve().parents[2] / "openapi_petstore" / "main.py"


def main() -> None:
    """Forward argv to ``examples/openapi_petstore/main.py`` and exit with its code.

    Example::

        uv run python examples/starters/openapi-provider/run.py
    """
    forward_parent(
        _PARENT,
        label="OpenAPI",
        expected_relpath="examples/openapi_petstore/main.py",
    )


if __name__ == "__main__":
    main()
