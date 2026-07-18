# OpenAPI provider starter

Thin wrapper around the PetStore OpenAPI → ASAP demo. The parent owns
`openapi-fragment.json` and the full script; this starter only re-invokes it.

## Prerequisites

- Python 3.13+
- `uv`

```bash
uv sync --extra openapi
```

## Smoke (default: bundled fragment + mock upstream)

From the repository root:

```bash
uv run python examples/starters/openapi-provider/run.py
```

## Live public PetStore (optional)

Requires network access over **HTTPS**. The remote API may return errors; prefer the default mock smoke for CI and offline checks.

```bash
uv run python examples/starters/openapi-provider/run.py --live
```

## Related

- Parent: [`examples/openapi_petstore/`](../../openapi_petstore/)
- Adapter guide: [`docs/adapters/openapi.md`](../../../docs/adapters/openapi.md)
- Starters index: [`../README.md`](../README.md)
