"""Thin starter: invoke the OpenAPI PetStore parent example via subprocess."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# examples/starters/openapi-provider → examples/
_PARENT = Path(__file__).resolve().parents[2] / "openapi_petstore" / "main.py"
_SMOKE_TIMEOUT_SEC = 60


def main() -> None:
    """Forward argv to ``examples/openapi_petstore/main.py`` and exit with its code.

    Example::

        uv run python examples/starters/openapi-provider/run.py
    """
    if not _PARENT.is_file():
        print(
            f"Parent example not found at {_PARENT} "
            f"(expected examples/openapi_petstore/main.py relative to repo).",
            file=sys.stderr,
        )
        sys.exit(1)
    cmd = [sys.executable, str(_PARENT), *sys.argv[1:]]
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            timeout=_SMOKE_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired:
        # Log script path only — argv may carry secrets if callers forward flags.
        print(
            f"OpenAPI starter smoke exceeded {_SMOKE_TIMEOUT_SEC}s limit "
            f"(DIST-003 headless bound). Script: {_PARENT.name} "
            f"(arguments omitted)",
            file=sys.stderr,
        )
        sys.exit(124)
    sys.exit(completed.returncode)


if __name__ == "__main__":
    main()
