## Overview

The examples demonstrate a minimal end-to-end flow between two agents:
an echo agent and a coordinator agent.

## Running the demo

Run the demo runner script from the repository root:

- `uv run python examples/run_demo.py`

This starts the echo agent on port 8001 and the coordinator agent on port 8000.
The coordinator sends a TaskRequest to the echo agent and logs the response.

## Running agents individually

You can run the agents separately if needed:

- `uv run python examples/echo_agent.py --host 127.0.0.1 --port 8001`
- `uv run python examples/coordinator.py`

## Notes

- The echo agent exposes `/.well-known/asap/manifest.json` for readiness checks.
- Update ports in `examples/run_demo.py` if you change the defaults.
