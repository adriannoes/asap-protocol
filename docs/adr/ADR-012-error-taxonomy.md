# ADR-012: Error Taxonomy

## Context and Problem Statement

ASAP agents and clients need a consistent way to classify and handle errors. We need machine-readable error codes and human-readable messages for debugging and recovery.

## Decision Drivers

* Client retry decisions (transient vs permanent)
* Structured logging and observability
* Clear error messages for developers
* JSON-RPC error compatibility

## Considered Options

* Free-form error strings
* Numeric codes only (JSON-RPC standard)
* Structured errors with code, message, data
* ASAP-specific error hierarchy (ASAPError base)

## Decision Outcome

Chosen option: "Structured errors with ASAP-specific hierarchy", because ASAPError base class and subclasses (InvalidTransitionError, CircuitOpenError, ASAPConnectionError, etc.) provide consistent structure. JSON-RPC errors use code, message, data with ASAP codes (e.g., asap:protocol/invalid_timestamp).

### Consequences

* Good, because clients can match error types for retry logic
* Good, because structured data (e.g., retry_after, envelope_id)
* Good, because consistent with JSON-RPC error format
* Bad, because more classes to maintain

### Confirmation

`asap.errors` module. Tests verify error structure and codes. See [Error Handling](../error-handling.md).

## Pros and Cons of the Options

### Free-form strings

* Good, because simple
* Bad, because no machine-readable classification

### Structured ASAP errors

* Good, because hierarchy; code, message, data
* Good, because JSON-RPC compatibility
* Bad, because more boilerplate

## More Information

* `src/asap/errors.py`
* [Error Handling](../error-handling.md)
* ASAPConnectionError, ASAPTimeoutError, ASAPRemoteError, CircuitOpenError
