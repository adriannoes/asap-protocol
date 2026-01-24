# ASAP Protocol Performance Benchmarks

This directory contains performance benchmarks for the ASAP protocol implementation.

## Prerequisites

Install pytest-benchmark (included in dev dependencies):

```bash
uv sync --extra dev
```

## Running Benchmarks

### Run All Benchmarks

```bash
uv run pytest benchmarks/ --benchmark-only -v
```

### Run Specific Benchmark File

```bash
# Model serialization benchmarks
uv run pytest benchmarks/benchmark_models.py --benchmark-only -v

# Transport layer benchmarks
uv run pytest benchmarks/benchmark_transport.py --benchmark-only -v
```

### Run Specific Benchmark Class

```bash
uv run pytest benchmarks/benchmark_models.py::TestEnvelopeCreation --benchmark-only -v
```

## Benchmark Categories

### Model Benchmarks (`benchmark_models.py`)

| Category | Description | Target |
|----------|-------------|--------|
| Envelope Creation | Create envelopes with auto-generated fields | < 100μs |
| JSON Serialization | Convert models to JSON dict/string | < 50μs |
| JSON Deserialization | Parse JSON into validated models | < 100μs |
| Entity Creation | Create various entity types | < 50μs |
| Batch Operations | Process 100 items in sequence | < 10ms |

### Transport Benchmarks (`benchmark_transport.py`)

| Category | Description | Target |
|----------|-------------|--------|
| JSON-RPC Processing | Create/serialize JSON-RPC messages | < 1ms |
| Manifest Endpoint | GET manifest discovery | < 1ms |
| Metrics Endpoint | GET Prometheus metrics | < 2ms |
| ASAP Endpoint | POST message processing | < 5ms |
| Throughput | Sequential request batches | > 100 req/s |
| Payload Sizes | Small/medium/large payloads | Linear scaling |

## Output Options

### Compare Against Baseline

Save a baseline for future comparisons:

```bash
# Save baseline
uv run pytest benchmarks/ --benchmark-only --benchmark-save=baseline

# Compare against baseline
uv run pytest benchmarks/ --benchmark-only --benchmark-compare=baseline
```

### Generate Reports

```bash
# JSON report
uv run pytest benchmarks/ --benchmark-only --benchmark-json=benchmark-results.json

# Histogram output
uv run pytest benchmarks/ --benchmark-only --benchmark-histogram=benchmark-hist
```

### Calibration Options

```bash
# More iterations for stability
uv run pytest benchmarks/ --benchmark-only --benchmark-min-rounds=100

# Disable warmup (for quick checks)
uv run pytest benchmarks/ --benchmark-only --benchmark-warmup=off

# Quick run (fewer iterations)
uv run pytest benchmarks/ --benchmark-only --benchmark-disable-gc --benchmark-min-rounds=5
```

## Interpreting Results

The benchmark output shows:

- **min**: Minimum time observed
- **max**: Maximum time observed  
- **mean**: Average time
- **stddev**: Standard deviation
- **median**: Middle value
- **ops**: Operations per second

Example output:

```
-------------------------------- benchmark: 5 tests --------------------------------
Name                              Min      Max     Mean   StdDev   Median     OPS
test_envelope_creation_minimal   45μs    120μs    55μs     8μs     52μs   18,181
test_envelope_to_json            12μs     35μs    15μs     3μs     14μs   66,666
test_manifest_endpoint          0.8ms    2.1ms   1.0ms   0.2ms   0.9ms    1,000
```

## Performance Targets

The following targets represent acceptable performance for production use:

| Operation | Target | Rationale |
|-----------|--------|-----------|
| Envelope creation | < 100μs | Should not add noticeable latency |
| JSON serialization | < 50μs | Fast serialization enables high throughput |
| HTTP round-trip | < 10ms | Local processing overhead only |
| Throughput | > 100 req/s | Minimum for low-traffic agents |

## CI Integration

Benchmarks can be integrated into CI to detect performance regressions:

```yaml
# .github/workflows/benchmark.yml
- name: Run benchmarks
  run: |
    uv run pytest benchmarks/ --benchmark-only \
      --benchmark-json=benchmark-results.json
    
- name: Store benchmark results
  uses: actions/upload-artifact@v4
  with:
    name: benchmark-results
    path: benchmark-results.json
```

## Troubleshooting

### High Variance in Results

If results show high variance:

1. Close other applications to reduce system load
2. Increase `--benchmark-min-rounds` for more samples
3. Use `--benchmark-disable-gc` to eliminate GC pauses
4. Run on a quiet machine (not during heavy CI load)

### Slow Benchmark Runs

For faster feedback during development:

```bash
uv run pytest benchmarks/ --benchmark-only \
  --benchmark-warmup=off \
  --benchmark-min-rounds=3 \
  -x  # Stop on first failure
```
