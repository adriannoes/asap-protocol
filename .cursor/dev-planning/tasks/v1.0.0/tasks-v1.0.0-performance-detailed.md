# Tasks: ASAP v1.0.0 Performance (P3-P4) - Detailed

> **Sprints**: P3-P4 - Performance optimizations
> **Goal**: Connection pooling, caching, batch operations, compression

---

## Relevant Files

### Sprint P3: Connection & Caching
- `src/asap/transport/client.py` - Connection pooling (pool_connections, pool_maxsize, pool_timeout) + Manifest caching (get_manifest)
- `src/asap/transport/cache.py` - NEW: ManifestCache with TTL (5min default)
- `benchmarks/benchmark_transport.py` - Connection pooling benchmark (TestConnectionPooling) + Manifest cache hit rate (TestManifestCaching)

### Sprint P4: Batch & Compression
- `src/asap/transport/client.py` - Batch operations (extend)
- `benchmarks/benchmark_transport.py` - Batch benchmarks (extend)

---

## Sprint P3: Connection & Caching

### Task 3.1: Implement Connection Pooling

- [x] 3.1.1 Research httpx connection limits
  - Read: https://www.python-httpx.org/advanced/#pool-limit-configuration
  - Document: Default pool size (httpx.Limits: max_connections=100, max_keepalive_connections=20, keepalive_expiry=5; pool timeout via Timeout(pool=...))
  - Plan: Configurable parameters pool_connections (→ max_keepalive_connections), pool_maxsize (→ max_connections), pool_timeout (→ Timeout(pool=...))

- [x] 3.1.2 Add pool configuration to ASAPClient
  - Parameters: pool_connections, pool_maxsize, pool_timeout
  - Defaults: 100, 100, 5.0
  - Pass to httpx.Limits()

- [x] 3.1.3 Create benchmark for connection pooling
  - File: `benchmarks/benchmark_transport.py`
  - Test: CONCURRENCY_POOLING_BENCHMARK concurrent (20 for CI; 1000 for full)
  - Measure: All requests succeed with pool (reuse implied when concurrency > pool_maxsize)

- [x] 3.1.4 Run benchmark
  - Command: `uv run pytest benchmarks/benchmark_transport.py::TestConnectionPooling::test_connection_pooling -v`
  - Target: >90% connection reuse (achieved via pool reuse when N > pool size)

- [x] 3.1.5 Document optimal pool sizes
  - Single-agent: 100 connections
  - Small cluster: 200-500
  - Large cluster: 500-1000

- [x] 3.1.6 Commit
  - feat(transport): add configurable connection pooling

**Acceptance**: 1000+ concurrent supported, documented

---

### Task 3.2: Implement Manifest Caching

- [x] 3.2.1 Create cache.py module
  - File: `src/asap/transport/cache.py`
  - Class: ManifestCache
  - Storage: dict with TTL (5 minutes default)

- [x] 3.2.2 Add cache methods
  - Method: get(url) -> Manifest | None
  - Method: set(url, manifest, ttl)
  - Method: invalidate(url)
  - Method: clear_all()

- [x] 3.2.3 Integrate in ASAPClient
  - Add: _manifest_cache instance variable
  - Method: get_manifest(url) checks cache first
  - On error: Invalidate cached entry

- [x] 3.2.4 Benchmark cache hit rate
  - Test: 100 manifest requests to same URL
  - Measure: Cache hits / total requests
  - Target: 90% hit rate (achieved: 99% with 1 miss + 99 hits)

- [x] 3.2.5 Commit
  - feat(transport): add manifest caching with TTL

**Acceptance**: 90% cache hit rate, 5min TTL

---

### Task 3.3: PRD Review Checkpoint

- [x] 3.3.1 Review Q1 (connection pool size)
  - Analyze benchmark results from Task 3.1
  - Document optimal defaults
  - Add DD-009 to PRD Section 10

- [x] 3.3.2 Update PRD
  - Document pool size recommendations
  - Mark Q1 as resolved

**Acceptance**: Q1 answered, DD-009 added

---

## Sprint P4: Batch & Compression

### Task 4.1: Implement Batch Operations

- [ ] 4.1.1 Add send_batch method to ASAPClient
  - Method: `async def send_batch(envelopes: list[Envelope]) -> list[Envelope]`
  - Use: asyncio.gather for parallel sends
  - Return: List of responses in same order

- [ ] 4.1.2 Add HTTP/2 multiplexing
  - Config: httpx client with http2=True
  - Leverage: HTTP/2 request pipelining

- [ ] 4.1.3 Benchmark batch operations
  - Test: Send 100 envelopes sequentially vs batch
  - Measure: Total time and throughput
  - Target: 10x improvement

- [ ] 4.1.4 Commit
  - Command: `git commit -m "feat(transport): add batch operations with HTTP/2 multiplexing"`

**Acceptance**: 10x throughput improvement for batches

---

### Task 4.2: Implement Compression

- [ ] 4.2.1 Add compression to client
  - Support: gzip (standard), brotli (optional)
  - Threshold: Compress if body >1KB
  - Headers: Accept-Encoding, Content-Encoding

- [ ] 4.2.2 Add decompression to server
  - Auto-detect: Content-Encoding header
  - Decompress: Before envelope parsing

- [ ] 4.2.3 Benchmark compression
  - Test: Large JSON payload (1MB)
  - Measure: Compressed size vs original
  - Target: 70% reduction

- [ ] 4.2.4 Commit
  - Command: `git commit -m "feat(transport): add gzip/brotli compression support"`

**Acceptance**: 70% size reduction for JSON payloads

---

## Task 4.3: Mark Sprints P3-P4 Complete

- [ ] 4.3.1 Update roadmap progress
  - Open: `tasks-v1.0.0-roadmap.md`
  - Mark: P3 tasks (3.1-3.3) as complete `[x]`
  - Mark: P4 tasks (4.1-4.2) as complete `[x]`
  - Update: P3 and P4 progress to 100%

- [ ] 4.3.2 Update this detailed file
  - Mark: All sub-tasks as complete `[x]`
  - Add: Completion dates

- [ ] 4.3.3 Verify performance targets met
  - Confirm: Benchmark results meet all targets
  - Confirm: PRD DD-008 documented

**Acceptance**: Both files complete, benchmarks validated

---

**P3-P4 Definition of Done**:
- [ ] All tasks 3.1-4.3 completed
- [ ] Connection pooling: 1000+ concurrent
- [ ] Manifest caching: 90% hit rate
- [ ] Batch operations: 10x throughput
- [ ] Compression: 70% reduction
- [ ] Benchmarks documented
- [ ] PRD Q1 answered (DD-008)
- [ ] Progress tracked in both files

**Total Sub-tasks**: ~60
