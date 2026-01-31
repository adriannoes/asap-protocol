"""Memory leak detection for ASAP protocol.

This module provides long-duration memory profiling to detect memory leaks
in the ASAP protocol server and client components.

Goals:
- Detect memory leaks in long-running scenarios
- Monitor memory usage trend over time
- Identify memory growth patterns

Running memory tests:

1. Quick memory test (5 minutes):
   ```bash
   uv run python benchmarks/memory_test.py --duration 300
   ```

2. Full memory test (1 hour):
   ```bash
   uv run python benchmarks/memory_test.py --duration 3600
   ```

3. Profile specific function with memory_profiler:
   ```bash
   uv run python -m memory_profiler benchmarks/memory_test.py --profile
   ```

Environment variables:
- ASAP_MEMORY_TEST_DURATION: Test duration in seconds (default: 3600)
- ASAP_MEMORY_TEST_INTERVAL: Sample interval in seconds (default: 10)
- ASAP_MEMORY_TEST_RPS: Requests per second (default: 100)

Output:
- Memory usage samples over time
- Growth rate analysis
- Leak detection verdict
"""

import argparse
import asyncio
import gc
import os
import sys
import time
import uuid
from dataclasses import dataclass, field

import httpx
from memory_profiler import memory_usage

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from asap.models.entities import Capability, Endpoint, Manifest, Skill
from asap.models.envelope import Envelope
from asap.transport.client import ASAPClient
from asap.transport.handlers import create_default_registry
from asap.transport.server import create_app

# Configuration constants
DEFAULT_DURATION_SECONDS = 3600  # 1 hour
DEFAULT_SAMPLE_INTERVAL = 10  # seconds
DEFAULT_RPS = 100  # requests per second

# Memory leak detection thresholds
LEAK_THRESHOLD_MB_PER_HOUR = 50.0  # More than 50MB/hour = likely leak
ACCEPTABLE_GROWTH_MB_PER_HOUR = 10.0  # Less than 10MB/hour = normal


@dataclass
class MemorySample:
    """Single memory usage sample."""

    timestamp: float
    memory_mb: float
    requests_sent: int
    gc_count: tuple[int, int, int]


@dataclass
class MemoryProfile:
    """Memory profile collected over time."""

    samples: list[MemorySample] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_requests: int = 0

    @property
    def duration_seconds(self) -> float:
        """Total duration in seconds."""
        return self.end_time - self.start_time

    @property
    def duration_hours(self) -> float:
        """Total duration in hours."""
        return self.duration_seconds / 3600

    @property
    def initial_memory_mb(self) -> float:
        """Memory at start of test."""
        return self.samples[0].memory_mb if self.samples else 0.0

    @property
    def final_memory_mb(self) -> float:
        """Memory at end of test."""
        return self.samples[-1].memory_mb if self.samples else 0.0

    @property
    def peak_memory_mb(self) -> float:
        """Peak memory during test."""
        return max(s.memory_mb for s in self.samples) if self.samples else 0.0

    @property
    def memory_growth_mb(self) -> float:
        """Total memory growth."""
        return self.final_memory_mb - self.initial_memory_mb

    @property
    def growth_rate_mb_per_hour(self) -> float:
        """Memory growth rate in MB/hour."""
        if self.duration_hours == 0:
            return 0.0
        return self.memory_growth_mb / self.duration_hours

    def has_leak(self) -> bool:
        """Check if memory growth indicates a leak."""
        return self.growth_rate_mb_per_hour > LEAK_THRESHOLD_MB_PER_HOUR

    def get_trend(self) -> str:
        """Get memory trend description."""
        rate = self.growth_rate_mb_per_hour
        if rate < 0:
            return "decreasing (GC effective)"
        if rate < ACCEPTABLE_GROWTH_MB_PER_HOUR:
            return "stable (no leak detected)"
        if rate < LEAK_THRESHOLD_MB_PER_HOUR:
            return "slight growth (monitor)"
        return "LEAK DETECTED (investigate)"

    def print_summary(self) -> None:
        """Print memory profile summary."""
        print("\n" + "=" * 60)
        print("MEMORY PROFILE SUMMARY")
        print("=" * 60)

        print(f"\nTest Duration: {self.duration_seconds:.0f}s ({self.duration_hours:.2f} hours)")
        print(f"Total Requests: {self.total_requests:,}")

        print("\n" + "-" * 40)
        print("MEMORY USAGE:")
        print("-" * 40)
        print(f"Initial: {self.initial_memory_mb:.2f} MB")
        print(f"Final: {self.final_memory_mb:.2f} MB")
        print(f"Peak: {self.peak_memory_mb:.2f} MB")
        print(f"Growth: {self.memory_growth_mb:+.2f} MB")
        print(f"Growth Rate: {self.growth_rate_mb_per_hour:+.2f} MB/hour")

        print("\n" + "-" * 40)
        print("ANALYSIS:")
        print("-" * 40)
        print(f"Trend: {self.get_trend()}")

        if self.has_leak():
            print("\n⚠️  MEMORY LEAK DETECTED!")
            print(f"    Growth rate {self.growth_rate_mb_per_hour:.2f} MB/hour")
            print(f"    exceeds threshold {LEAK_THRESHOLD_MB_PER_HOUR} MB/hour")
        else:
            print("\n✅ No memory leak detected")

        # Print sample summary
        if len(self.samples) > 5:
            print("\n" + "-" * 40)
            print("SAMPLE HISTORY (subset):")
            print("-" * 40)
            print(f"{'Time (s)':>10} {'Memory (MB)':>12} {'Requests':>12}")

            # Show first 3 and last 2 samples
            for sample in self.samples[:3]:
                elapsed = sample.timestamp - self.start_time
                print(f"{elapsed:>10.0f} {sample.memory_mb:>12.2f} {sample.requests_sent:>12,}")

            print("         ... ... ...")

            for sample in self.samples[-2:]:
                elapsed = sample.timestamp - self.start_time
                print(f"{elapsed:>10.0f} {sample.memory_mb:>12.2f} {sample.requests_sent:>12,}")

        print("\n" + "=" * 60)


def get_memory_mb() -> float:
    """Get current memory usage in MB."""
    # memory_usage returns list of memory samples, take first
    mem = memory_usage(-1, interval=0.1, max_iterations=1)
    return mem[0] if mem else 0.0


def create_test_manifest() -> Manifest:
    """Create a manifest for memory testing."""
    return Manifest(
        id="urn:asap:agent:memory-test-server",
        name="Memory Test Server",
        version="1.0.0",
        description="Server for memory leak testing",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo skill")],
            state_persistence=False,
            streaming=False,
        ),
        endpoints=Endpoint(asap="http://testserver/asap"),
    )


def create_test_envelope() -> Envelope:
    """Create a test envelope for memory testing."""
    return Envelope(
        asap_version="0.1",
        sender="urn:asap:agent:memory-client",
        recipient="urn:asap:agent:memory-test-server",
        payload_type="task.request",
        payload={
            "conversation_id": f"mem_{uuid.uuid4().hex[:8]}",
            "skill_id": "echo",
            "input": {"data": "memory test"},
        },
    )


async def run_memory_test(
    duration_seconds: int = DEFAULT_DURATION_SECONDS,
    sample_interval: int = DEFAULT_SAMPLE_INTERVAL,
    target_rps: int = DEFAULT_RPS,
) -> MemoryProfile:
    """Run memory leak detection test.

    Creates an in-process ASAP server and client, then sends requests
    at the target RPS while monitoring memory usage.

    Args:
        duration_seconds: Test duration in seconds
        sample_interval: How often to sample memory (seconds)
        target_rps: Target requests per second

    Returns:
        MemoryProfile with collected samples and analysis
    """
    print("\n" + "=" * 60)
    print("ASAP Memory Leak Detection Test")
    print("=" * 60)
    print(f"Duration: {duration_seconds}s ({duration_seconds / 3600:.2f} hours)")
    print(f"Sample interval: {sample_interval}s")
    print(f"Target RPS: {target_rps}")
    print("=" * 60 + "\n")

    # Create test server and client
    manifest = create_test_manifest()
    registry = create_default_registry()
    app = create_app(manifest, registry, rate_limit="100000/minute")
    transport = httpx.ASGITransport(app=app)

    profile = MemoryProfile()
    profile.start_time = time.time()

    # Force initial GC and get baseline memory
    gc.collect()
    gc.get_count()

    async with ASAPClient(
        "http://testserver",
        transport=transport,
        require_https=False,
    ) as client:
        # Track requests and timing
        requests_sent = 0
        last_sample_time = time.time()
        end_time = time.time() + duration_seconds

        # Calculate delay between requests
        delay = 1.0 / target_rps if target_rps > 0 else 0.01

        print("Starting test loop...")
        print(f"{'Elapsed':>10} {'Memory (MB)':>12} {'Requests':>12} {'RPS':>8}")
        print("-" * 46)

        while time.time() < end_time:
            # Send request
            try:
                envelope = create_test_envelope()
                await client.send(envelope)
                requests_sent += 1
            except Exception as e:
                # Log but continue
                if requests_sent % 1000 == 0:
                    print(f"Error at request {requests_sent}: {e}")

            # Sample memory periodically
            now = time.time()
            if now - last_sample_time >= sample_interval:
                gc_count = gc.get_count()
                memory_mb = get_memory_mb()

                sample = MemorySample(
                    timestamp=now,
                    memory_mb=memory_mb,
                    requests_sent=requests_sent,
                    gc_count=gc_count,
                )
                profile.samples.append(sample)

                elapsed = now - profile.start_time
                current_rps = requests_sent / elapsed if elapsed > 0 else 0

                print(
                    f"{elapsed:>10.0f} {memory_mb:>12.2f} {requests_sent:>12,} {current_rps:>8.1f}"
                )

                last_sample_time = now

            # Rate limiting delay
            await asyncio.sleep(delay)

        # Final sample
        gc.collect()
        profile.samples.append(
            MemorySample(
                timestamp=time.time(),
                memory_mb=get_memory_mb(),
                requests_sent=requests_sent,
                gc_count=gc.get_count(),
            )
        )

    profile.end_time = time.time()
    profile.total_requests = requests_sent

    return profile


async def run_component_memory_test() -> dict[str, MemoryProfile]:
    """Run memory tests on individual components.

    Tests memory usage of:
    - Envelope creation and serialization
    - Client send operations
    - Server request handling

    Returns:
        Dictionary of component name to MemoryProfile
    """
    results: dict[str, MemoryProfile] = {}

    print("\n" + "=" * 60)
    print("COMPONENT MEMORY TESTS")
    print("=" * 60)

    # Test 1: Envelope creation
    print("\n--- Envelope Creation Test ---")
    profile = MemoryProfile()
    profile.start_time = time.time()

    gc.collect()
    get_memory_mb()

    envelopes = []
    for i in range(10000):
        envelopes.append(create_test_envelope())
        if i % 2000 == 0:
            profile.samples.append(
                MemorySample(
                    timestamp=time.time(),
                    memory_mb=get_memory_mb(),
                    requests_sent=i,
                    gc_count=gc.get_count(),
                )
            )

    profile.end_time = time.time()
    profile.total_requests = 10000
    results["envelope_creation"] = profile

    # Clean up
    del envelopes
    gc.collect()

    print(f"Envelope creation: {profile.memory_growth_mb:+.2f} MB for 10k envelopes")

    # Test 2: Serialization
    print("\n--- Serialization Test ---")
    profile = MemoryProfile()
    profile.start_time = time.time()

    gc.collect()

    json_outputs = []
    for i in range(10000):
        envelope = create_test_envelope()
        json_outputs.append(envelope.model_dump_json())
        if i % 2000 == 0:
            profile.samples.append(
                MemorySample(
                    timestamp=time.time(),
                    memory_mb=get_memory_mb(),
                    requests_sent=i,
                    gc_count=gc.get_count(),
                )
            )

    profile.end_time = time.time()
    profile.total_requests = 10000
    results["serialization"] = profile

    del json_outputs
    gc.collect()

    print(f"Serialization: {profile.memory_growth_mb:+.2f} MB for 10k serializations")

    return results


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ASAP Protocol Memory Leak Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick test (5 minutes)
  python benchmarks/memory_test.py --duration 300

  # Full test (1 hour)
  python benchmarks/memory_test.py --duration 3600

  # Custom RPS
  python benchmarks/memory_test.py --duration 600 --rps 200

  # Component test only
  python benchmarks/memory_test.py --components-only
        """,
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=int(os.getenv("ASAP_MEMORY_TEST_DURATION", str(DEFAULT_DURATION_SECONDS))),
        help=f"Test duration in seconds (default: {DEFAULT_DURATION_SECONDS})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("ASAP_MEMORY_TEST_INTERVAL", str(DEFAULT_SAMPLE_INTERVAL))),
        help=f"Sample interval in seconds (default: {DEFAULT_SAMPLE_INTERVAL})",
    )
    parser.add_argument(
        "--rps",
        type=int,
        default=int(os.getenv("ASAP_MEMORY_TEST_RPS", str(DEFAULT_RPS))),
        help=f"Target requests per second (default: {DEFAULT_RPS})",
    )
    parser.add_argument(
        "--components-only",
        action="store_true",
        help="Run component tests only (faster)",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run with memory_profiler line-by-line profiling",
    )
    return parser.parse_args()


async def main_async() -> int:
    """Async main entry point."""
    args = parse_args()

    if args.components_only:
        # Run component tests only
        results = await run_component_memory_test()
        print("\n" + "=" * 60)
        print("COMPONENT TEST SUMMARY")
        print("=" * 60)
        for name, profile in results.items():
            print(f"{name}: {profile.memory_growth_mb:+.2f} MB growth")
        return 0

    # Run full memory test
    profile = await run_memory_test(
        duration_seconds=args.duration,
        sample_interval=args.interval,
        target_rps=args.rps,
    )

    profile.print_summary()

    # Return non-zero if leak detected
    if profile.has_leak():
        return 1
    return 0


def main() -> None:
    """Main entry point."""
    exit_code = asyncio.run(main_async())
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
