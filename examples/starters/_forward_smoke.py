"""Shared subprocess forwarder for thin starter smoke scripts (DIST-003)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEFAULT_SMOKE_TIMEOUT_SEC = 60


def forward_parent(
    parent: Path,
    *,
    label: str,
    expected_relpath: str,
    timeout_sec: int = DEFAULT_SMOKE_TIMEOUT_SEC,
) -> None:
    """Run ``parent`` with the caller's argv and exit with its return code.

    On timeout, logs the script basename only (argv may carry secrets) and
    exits with 124.

    Example::

        forward_parent(
            Path("examples/openapi_petstore/main.py"),
            label="OpenAPI",
            expected_relpath="examples/openapi_petstore/main.py",
        )
    """
    if not parent.is_file():
        print(
            f"Parent example not found at {parent} (expected {expected_relpath} relative to repo).",
            file=sys.stderr,
        )
        sys.exit(1)
    cmd = [sys.executable, str(parent), *sys.argv[1:]]
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired:
        # Log script path only — argv may carry secrets if callers forward flags.
        print(
            f"{label} starter smoke exceeded {timeout_sec}s limit "
            f"(DIST-003 headless bound). Script: {parent.name} "
            f"(arguments omitted)",
            file=sys.stderr,
        )
        sys.exit(124)
    sys.exit(completed.returncode)
