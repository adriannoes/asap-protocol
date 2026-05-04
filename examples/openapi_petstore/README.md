# OpenAPI PetStore reference example

Runnable demo: builds an ASAP app from a **PetStore-shaped** OpenAPI fragment (bundled under `openapi-fragment.json`), runs **Compliance Harness v2** (expects score **1.0**), and invokes `findPetsByStatus` in-process. By default the upstream API is **mocked** so the script works offline and is not affected when the public PetStore service misbehaves.

## Prerequisites

- Python 3.13+
- `uv`

Install the OpenAPI extra:

```bash
uv sync --extra openapi
```

## Run (default: bundled fragment + mock upstream)

From the repository root:

```bash
uv run python examples/openapi_petstore/main.py
```

## Live public PetStore spec (optional)

To load the real OpenAPI document from the network and call the live host (requires connectivity; the remote API may return errors):

```bash
uv run python examples/openapi_petstore/main.py --live
```

Equivalent: `ASAP_PETSTORE_LIVE=1`.

## Notes

- **Identity / approval**: This example does not configure `FreshSessionConfig` or `approval_strength` on the app; see `src/asap/adapters/openapi/approval.py` for OA-008 wiring in production.
