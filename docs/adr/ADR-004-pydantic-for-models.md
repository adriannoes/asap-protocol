# ADR-004: Pydantic for Models

## Context and Problem Statement

ASAP defines structured message types (Envelope, TaskRequest, TaskResponse, Manifest, etc.). We need validation, serialization, and type safety for these models.

## Decision Drivers

* Strong typing and runtime validation
* JSON serialization/deserialization
* Clear error messages for invalid payloads
* Integration with FastAPI (Pydantic-native)

## Considered Options

* dataclasses + manual validation
* Pydantic v2
* attrs
* Marshmallow

## Decision Outcome

Chosen option: "Pydantic v2", because it provides validation, serialization, and type hints out of the box. FastAPI uses Pydantic for request/response models, so the stack is consistent.

### Consequences

* Good, because automatic validation on parse; clear ValidationError messages
* Good, because `model_dump()` and `model_validate()` for JSON round-trip
* Good, because IDE support and mypy compatibility
* Bad, because Pydantic adds dependency and learning curve

### Confirmation

All models in `asap.models` use Pydantic BaseModel. Tests verify validation and serialization.

## Pros and Cons of the Options

### dataclasses + manual validation

* Good, because stdlib; no extra dep
* Bad, because no built-in validation or JSON schema

### Pydantic v2

* Good, because validation, serialization, performance (Rust core)
* Good, because FastAPI integration
* Bad, because external dependency

### attrs

* Good, because lightweight
* Bad, because less ecosystem for OpenAPI/JSON schema

## More Information

* Models: `src/asap/models/`
* Base: `asap.models.base.ASAPBaseModel`
* Requires: `pydantic>=2.12.5`
