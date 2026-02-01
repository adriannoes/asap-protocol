# ADR-008: httpx for Client

## Context and Problem Statement

ASAP clients send envelopes over HTTP. We need an async HTTP client with connection pooling, HTTP/2 support, and retry/timeout configuration.

## Decision Drivers

* Async HTTP client
* Connection pooling for high concurrency
* HTTP/2 support for multiplexing
* Timeout, retry, and compression support
* API compatibility with requests for familiarity

## Considered Options

* httpx
* aiohttp
* requests + grequests/threading
* urllib3

## Decision Outcome

Chosen option: "httpx", because it provides async API, connection pooling, HTTP/2 (via httpx[http2]), and a requests-like interface. Used as the transport for ASAPClient.

### Consequences

* Good, because async-native; integrates with asyncio
* Good, because connection pooling and HTTP/2 for throughput
* Good, because timeout, retry, and compression built-in
* Bad, because adds dependency; aiohttp has different API

### Confirmation

ASAPClient uses `httpx.AsyncClient` under the hood. See `asap.transport.client`.

## Pros and Cons of the Options

### httpx

* Good, because async, pooling, HTTP/2
* Good, because requests-like API
* Neutral, because newer than aiohttp

### aiohttp

* Good, because mature async client
* Bad, because different API; less requests familiarity

### requests

* Good, because widely known
* Bad, because sync-only; blocks event loop

## More Information

* `src/asap/transport/client.py`
* Dependencies: `httpx[http2]>=0.28.1`
* Pool limits: DEFAULT_POOL_CONNECTIONS, DEFAULT_POOL_MAXSIZE
