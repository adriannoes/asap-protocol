# ADR-007: FastAPI for Server

## Context and Problem Statement

ASAP needs an HTTP server for the `/asap` endpoint and manifest discovery. We need async support, JSON handling, and OpenAPI/docs for developer experience.

## Decision Drivers

* Async ASGI server
* Automatic JSON parsing/validation
* OpenAPI/Swagger for API exploration
* Widely adopted and maintained
* Performance for high concurrency

## Considered Options

* FastAPI
* Starlette (raw)
* aiohttp
* Django ASGI

## Decision Outcome

Chosen option: "FastAPI", because it provides async routing, Pydantic integration, automatic OpenAPI docs, and is built on Starlette/Uvicorn. Aligns with Pydantic models and JSON-RPC handling.

### Consequences

* Good, because Pydantic request/response validation
* Good, because OpenAPI at `/docs` for debugging
* Good, because middleware support (rate limit, auth, CORS)
* Bad, because adds dependency; Starlette alone would be lighter

### Confirmation

`asap.transport.server.create_app()` returns a FastAPI app. Runs with Uvicorn.

## Pros and Cons of the Options

### FastAPI

* Good, because async, Pydantic, OpenAPI
* Good, because ecosystem and community
* Bad, because heavier than Starlette alone

### Starlette

* Good, because minimal
* Bad, because no built-in validation or OpenAPI

### aiohttp

* Good, because async
* Bad, because different request model; less Pydantic integration

## More Information

* `src/asap/transport/server.py`
* `create_app(manifest, registry)`
* Uvicorn for ASGI serving
