# Error Handling

This document describes ASAP error taxonomy and handling patterns.

## Error Taxonomy

ASAP defines structured errors in `asap.errors` with a stable error code format:

```
asap:<domain>/<error>
```

Examples:

- `asap:protocol/invalid_state`
- `asap:protocol/malformed_envelope`
- `asap:task/not_found`

## Core Error Types

- `ASAPError`: base class for all protocol errors
- `InvalidTransitionError`: invalid task state transitions
- `MalformedEnvelopeError`: invalid envelope payloads
- `TaskNotFoundError`: task lookup failures
- `TaskAlreadyCompletedError`: attempted updates to terminal tasks

## Usage Example

```python
from asap.errors import InvalidTransitionError

try:
    raise InvalidTransitionError(from_state="submitted", to_state="completed")
except InvalidTransitionError as exc:
    error_payload = exc.to_dict()
    # error_payload contains code, message, and details
```

## JSON-RPC Mapping

Transport layer errors are surfaced as JSON-RPC error responses:

- `INVALID_REQUEST` for malformed JSON-RPC requests
- `INVALID_PARAMS` for invalid envelope payloads
- `METHOD_NOT_FOUND` for unknown payload types
- `INTERNAL_ERROR` for unexpected exceptions

Use structured logs with `trace_id` and `correlation_id` to debug failures across
agent boundaries.
