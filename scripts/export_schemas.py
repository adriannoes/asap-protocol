#!/usr/bin/env python3
"""Export JSON Schema files for all ASAP models.

This script generates JSON Schema files for all ASAP protocol models,
organizing them by category in the schemas/ directory.

Usage:
    python scripts/export_schemas.py
"""

from pathlib import Path

from asap.schemas import export_all_schemas


def main() -> None:
    """Export all ASAP model schemas."""
    schemas_dir = Path("schemas")
    print("🚀 Exporting ASAP Protocol JSON Schemas...\n")
    written_paths = export_all_schemas(schemas_dir)
    print(f"\n✨ Successfully exported all schemas to {schemas_dir}/")
    print(f"📊 Total schemas: {len(written_paths)}")


if __name__ == "__main__":
    main()
