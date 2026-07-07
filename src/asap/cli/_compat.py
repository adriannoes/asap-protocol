"""Legacy public-symbol re-exports kept for backward compatibility.

These names historically lived on ``asap.cli`` (inline in ``__init__.py``
before the v2.5.1 S3 cli split). New code should import from the owning
submodules directly:

- ``DEFAULT_SCHEMAS_DIR`` → ``asap.cli.schemas``
- ``export_all_schemas`` → ``asap.schemas``
- ``_repl_namespace`` → ``asap.cli.repl``
"""

from __future__ import annotations

from asap.cli.repl import _repl_namespace
from asap.cli.schemas import DEFAULT_SCHEMAS_DIR
from asap.schemas import export_all_schemas

__all__ = ["DEFAULT_SCHEMAS_DIR", "export_all_schemas", "_repl_namespace"]
