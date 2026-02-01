# ADR-002: Async-First API Design

## Context and Problem Statement

ASAP agents communicate over the network. Synchronous blocking calls would block the event loop and limit throughput. We need an API design that scales for high concurrency and integrates with modern Python async ecosystems.

## Decision Drivers

* Network I/O is the primary bottleneck
* Support for high concurrency (1000+ connections per client)
* Compatibility with asyncio, FastAPI, and async HTTP clients
* Non-blocking handlers for scalable server processing

## Considered Options

* Sync-only API
* Async-only API
* Sync with optional async wrapper

## Decision Outcome

Chosen option: "Async-only API", because ASAP's primary operations (send envelope, receive response) are I/O-bound and benefit from async/await. Clients use `async with ASAPClient(...)` and handlers run in async context.

### Consequences

* Good, because single-threaded concurrency scales for many connections
* Good, because aligns with FastAPI and httpx async patterns
* Bad, because callers must use `asyncio.run()` or be in async context
* Neutral, because sync handlers are supported via bounded executor in HandlerRegistry

### Confirmation

ASAPClient and server handlers use async signatures. Tests use pytest-asyncio.

## Pros and Cons of the Options

### Sync-only API

* Good, because simpler for basic scripts
* Bad, because blocks event loop; poor scalability

### Async-only API

* Good, because non-blocking; high throughput
* Good, because matches FastAPI/uvicorn model
* Bad, because steeper learning curve for sync-only developers

## More Information

* Client: `asap.transport.client.ASAPClient`
* Server: `asap.transport.server.create_app` (FastAPI/ASGI)
* Sync handlers: `HandlerRegistry(executor=...)` for sync callables
