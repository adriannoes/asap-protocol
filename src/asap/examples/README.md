## Overview

The examples demonstrate a minimal end-to-end flow between two agents:
an echo agent and a coordinator agent.

## Running the demo

Run the demo runner module from the repository root:

- `uv run python -m asap.examples.run_demo`

This starts the echo agent on port 8001 and the coordinator agent on port 8000.
The coordinator sends a TaskRequest to the echo agent and logs the response.

## Running agents individually

You can run the agents separately if needed:

- `uv run python -m asap.examples.echo_agent --host 127.0.0.1 --port 8001`
- `uv run python -m asap.examples.coordinator`

## Handler security example

- `asap.examples.secure_handler` provides `create_secure_handler()`: a handler that
  validates payload with `TaskRequest`, validates file parts with `FilePart` (URI checks),
  and logs with `sanitize_for_logging()`. Use it as a reference for input validation
  (see `docs/security.md` Handler Security).

## Notes

- The echo agent exposes `/.well-known/asap/manifest.json` for readiness checks.
- Update ports in `asap.examples.run_demo` if you change the defaults.
- These examples use the basic ASAP API without authentication or advanced security features.
  For production use, consider adding authentication via `manifest.auth` and enabling
  additional security features (see `docs/security.md`).
