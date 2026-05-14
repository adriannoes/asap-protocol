#!/usr/bin/env python3
"""Enforce D4: forbid growing public surface on transport server/client monolith files.

Compares the set of public function/method names in ``server.py`` and ``client.py``
against ``scripts/_transport_baseline_v2.3.0.json``. New public symbols fail CI;
removed symbols are allowed.

Design rationale:
    AST inspection avoids importing ASAP dependencies when emitting/checking.

Exit codes:
    0 — current exports ⊆ baseline (no growth).
    1 — baseline violated or invalid invocation."""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Final

_REPO_ROOT: Final = Path(__file__).resolve().parent.parent
_BASELINE_REL_PATH: Final = Path("scripts/_transport_baseline_v2.3.0.json")
_TRANSPORT_REL_PATHS: Final[tuple[str, ...]] = (
    "src/asap/transport/server.py",
    "src/asap/transport/client.py",
)


def _is_public_symbol(name: str) -> bool:
    """Return True if this AST-defined callable should count toward D4 surface."""
    return not name.startswith("_")


def _symbols_from_class_body(class_node: ast.ClassDef, prefix: str) -> set[str]:
    """Collect ``Prefix.method`` symbols from class body (recursive for nested classes)."""
    found: set[str] = set()
    for item in class_node.body:
        if isinstance(item, ast.ClassDef):
            nested_prefix = f"{prefix}.{item.name}"
            found |= _symbols_from_class_body(item, nested_prefix)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_symbol(item.name):
                found.add(f"{prefix}.{item.name}")
    return found


def extract_public_symbols(py_path: Path) -> list[str]:
    """Parse *py_path* and list public module-level functions plus class methods."""
    source = py_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    symbols: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _is_public_symbol(node.name):
                symbols.add(node.name)
        elif isinstance(node, ast.ClassDef):
            symbols |= _symbols_from_class_body(node, node.name)

    return sorted(symbols)


def emit_baseline(repo_root: Path) -> dict[str, object]:
    """Build baseline payload with sorted symbol lists."""
    files_payload: dict[str, list[str]] = {}
    for rel in _TRANSPORT_REL_PATHS:
        abs_path = repo_root / rel
        if not abs_path.is_file():
            msg = f"Expected transport file missing: {rel}"
            raise FileNotFoundError(msg)
        files_payload[rel] = extract_public_symbols(abs_path)

    return {
        "_meta": {
            "description": (
                "Frozen public callable surface for D4 transport monolith lint "
                "(see docs/maintainers/transport-evolution.md)."
            ),
            "frozen_at_release": "v2.3.0",
        },
        "files": files_payload,
    }


def load_baseline(path: Path) -> dict[str, list[str]]:
    """Load and validate baseline JSON; return the ``files`` mapping."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Baseline root must be a JSON object")
    files_obj = raw.get("files")
    if not isinstance(files_obj, dict):
        raise ValueError("Baseline must contain a 'files' object")

    files_payload: dict[str, list[str]] = {}
    for key, value in files_obj.items():
        if key not in _TRANSPORT_REL_PATHS:
            raise ValueError(f"Unexpected baseline key {key!r}")
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise ValueError(f"Baseline entry for {key!r} must be a list of strings")
        files_payload[str(key)] = list(value)

    expected = set(_TRANSPORT_REL_PATHS)
    if set(files_payload.keys()) != expected:
        missing = expected - set(files_payload.keys())
        raise ValueError(f"Baseline 'files' missing entries: {sorted(missing)}")

    return files_payload


def check_no_growth(repo_root: Path, baseline_path: Path) -> list[str]:
    """Return human-readable errors (empty list means success)."""
    errors: list[str] = []
    try:
        baseline_files = load_baseline(baseline_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"Cannot load baseline {baseline_path}: {exc}"]

    for rel in _TRANSPORT_REL_PATHS:
        abs_path = repo_root / rel
        if not abs_path.is_file():
            errors.append(f"Missing transport module {rel}")
            continue

        current = set(extract_public_symbols(abs_path))
        allowed = set(baseline_files[rel])
        added = sorted(current - allowed)
        if added:
            joined = ", ".join(added)
            errors.append(
                f"D4 violation: new public symbols in {rel} "
                f"(move routes/helpers to a dedicated module): {joined}"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--emit-baseline",
        action="store_true",
        help="Print baseline JSON to stdout (redirect to scripts/_transport_baseline_v2.3.0.json).",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=None,
        help=f"Override baseline JSON path (default: repo / {_BASELINE_REL_PATH.as_posix()}).",
    )
    args = parser.parse_args(argv)

    baseline_default = _REPO_ROOT / _BASELINE_REL_PATH
    baseline_path = args.baseline_path if args.baseline_path is not None else baseline_default

    if args.emit_baseline:
        try:
            payload = emit_baseline(_REPO_ROOT)
        except FileNotFoundError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    errors = check_no_growth(_REPO_ROOT, baseline_path.resolve())
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
