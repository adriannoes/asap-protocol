"""Stress testing for ASAP protocol to find breaking point.

This module provides stress testing scenarios that gradually increase load
until the system fails, identifying the maximum sustainable throughput.

Goals:
- Identify breaking point (max req/sec before failures)
- Measure degradation curve (latency vs load)
- Find resource exhaustion thresholds

Running stress tests:

1. Start the ASAP server in one terminal:
   ```bash
   uv run uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
   ```

2. Run stress test in another terminal:
   ```bash
   # Step-load stress test (recommended):
   uv run locust -f benchmarks/stress_test.py --headless \
       -u 500 -r 50 -t 5m --host http://localhost:8000 \
       --step-load --step-users 50 --step-time 30s

   # Spike test (sudden high load):
   uv run locust -f benchmarks/stress_test.py --headless \
       -u 1000 -r 500 -t 2m --host http://localhost:8000

   # Web UI mode (interactive):
   uv run locust -f benchmarks/stress_test.py --host http://localhost:8000
   # Then open http://localhost:8089 in browser
   ```

Stress test patterns:
- Step-load: Gradually increase users in steps, hold each level to measure
- Spike: Sudden jump to high load to test burst handling
- Soak: Extended duration at moderate load (use load_test.py with longer duration)

Environment variables:
- ASAP_STRESS_MAX_USERS: Maximum users to scale to (default: 500)
- ASAP_STRESS_STEP_SIZE: Users added per step (default: 50)
- ASAP_STRESS_STEP_TIME: Duration per step in seconds (default: 30)
"""

import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from locust import HttpUser, between, events, task
from locust.env import Environment

# Stress test configuration
DEFAULT_MAX_USERS = 500  # Maximum users to scale to
DEFAULT_STEP_SIZE = 50  # Users added per step
DEFAULT_STEP_TIME = 30  # Seconds per step

# Breaking point thresholds
ERROR_RATE_THRESHOLD = 0.05  # 5% error rate = breaking point
P95_LATENCY_THRESHOLD_MS = 100.0  # 100ms p95 = degraded
P99_LATENCY_THRESHOLD_MS = 500.0  # 500ms p99 = severe degradation


# Track metrics over time for breaking point detection
class StressMetrics:
    """Collect and analyze stress test metrics over time."""

    def __init__(self) -> None:
        self.samples: list[dict[str, Any]] = []
        self.breaking_point_rps: float | None = None
        self.breaking_point_users: int | None = None
        self.breaking_point_reason: str | None = None
        self._last_sample_time: float = 0
        self._sample_interval: float = 5.0  # Sample every 5 seconds

    def maybe_sample(self, stats: Any, user_count: int) -> None:
        """Sample current stats if enough time has passed."""
        now = time.time()
        if now - self._last_sample_time < self._sample_interval:
            return

        self._last_sample_time = now
        total = stats.total

        if total.num_requests == 0:
            return

        sample = {
            "timestamp": now,
            "user_count": user_count,
            "total_requests": total.num_requests,
            "total_failures": total.num_failures,
            "rps": total.current_rps,
            "error_rate": total.num_failures / total.num_requests,
            "p50_ms": total.get_response_time_percentile(0.50),
            "p95_ms": total.get_response_time_percentile(0.95),
            "p99_ms": total.get_response_time_percentile(0.99),
            "avg_ms": total.avg_response_time,
        }
        self.samples.append(sample)

        # Check for breaking point
        self._check_breaking_point(sample)

    def _check_breaking_point(self, sample: dict[str, Any]) -> None:
        """Check if current sample indicates breaking point."""
        if self.breaking_point_rps is not None:
            return  # Already found

        if sample["error_rate"] >= ERROR_RATE_THRESHOLD:
            self.breaking_point_rps = sample["rps"]
            self.breaking_point_users = sample["user_count"]
            self.breaking_point_reason = (
                f"Error rate {sample['error_rate'] * 100:.1f}% >= {ERROR_RATE_THRESHOLD * 100}%"
            )
            return

        if sample["p99_ms"] >= P99_LATENCY_THRESHOLD_MS:
            self.breaking_point_rps = sample["rps"]
            self.breaking_point_users = sample["user_count"]
            self.breaking_point_reason = (
                f"p99 latency {sample['p99_ms']:.0f}ms >= {P99_LATENCY_THRESHOLD_MS}ms"
            )
            return

    def get_max_sustainable_rps(self) -> float | None:
        """Get the maximum RPS achieved before breaking point."""
        if not self.samples:
            return None

        # If no breaking point, return max RPS seen
        if self.breaking_point_rps is None:
            return max(s["rps"] for s in self.samples)

        # Return RPS just before breaking point
        healthy_samples = [
            s
            for s in self.samples
            if s["error_rate"] < ERROR_RATE_THRESHOLD and s["p99_ms"] < P99_LATENCY_THRESHOLD_MS
        ]
        if healthy_samples:
            return max(s["rps"] for s in healthy_samples)
        return None

    def print_summary(self) -> None:
        """Print stress test summary."""
        if not self.samples:
            print("No samples collected")
            return

        print("\n" + "=" * 60)
        print("STRESS TEST RESULTS")
        print("=" * 60)

        # Find key metrics
        max_rps = max(s["rps"] for s in self.samples)
        max_users = max(s["user_count"] for s in self.samples)
        min_error_rate = min(s["error_rate"] for s in self.samples)
        max_error_rate = max(s["error_rate"] for s in self.samples)

        print(f"\nTest duration: {len(self.samples) * 5} seconds")
        print(f"Max users: {max_users}")
        print(f"Max RPS achieved: {max_rps:.2f}")
        print(f"Error rate range: {min_error_rate * 100:.2f}% - {max_error_rate * 100:.2f}%")

        # Print degradation curve
        print("\n" + "-" * 40)
        print("DEGRADATION CURVE (sampled):")
        print("-" * 40)
        print(f"{'Users':>8} {'RPS':>10} {'p95 (ms)':>12} {'p99 (ms)':>12} {'Errors':>10}")
        print("-" * 52)

        # Group by user count and show representative samples
        by_users: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for s in self.samples:
            by_users[s["user_count"]].append(s)

        for users in sorted(by_users.keys()):
            samples = by_users[users]
            avg_rps = sum(s["rps"] for s in samples) / len(samples)
            avg_p95 = sum(s["p95_ms"] for s in samples) / len(samples)
            avg_p99 = sum(s["p99_ms"] for s in samples) / len(samples)
            avg_errors = sum(s["error_rate"] for s in samples) / len(samples)
            print(
                f"{users:>8} {avg_rps:>10.1f} {avg_p95:>12.1f} {avg_p99:>12.1f} {avg_errors * 100:>9.2f}%"
            )

        # Breaking point analysis
        print("\n" + "-" * 40)
        print("BREAKING POINT ANALYSIS:")
        print("-" * 40)

        if self.breaking_point_rps is not None:
            print("Breaking point detected!")
            print(f"  RPS at break: {self.breaking_point_rps:.2f}")
            print(f"  Users at break: {self.breaking_point_users}")
            print(f"  Reason: {self.breaking_point_reason}")

            max_sustainable = self.get_max_sustainable_rps()
            if max_sustainable:
                print(f"\nMax sustainable RPS: {max_sustainable:.2f}")
                print(f"Recommended capacity: {max_sustainable * 0.8:.2f} RPS (80% of max)")
        else:
            print("No breaking point detected within test parameters")
            print(f"Server sustained {max_rps:.2f} RPS at {max_users} users")
            print("Consider increasing max users for next test")

        print("\n" + "=" * 60)


# Global metrics collector
stress_metrics = StressMetrics()


def create_valid_envelope(sender: str, recipient: str) -> dict[str, Any]:
    """Create a valid ASAP envelope for stress testing."""
    now = datetime.now(timezone.utc).isoformat()
    envelope_id = str(uuid.uuid4())

    return {
        "id": envelope_id,
        "asap_version": "0.1",
        "timestamp": now,
        "sender": sender,
        "recipient": recipient,
        "payload_type": "task.request",
        "payload": {
            "conversation_id": f"stress_{uuid.uuid4().hex[:8]}",
            "skill_id": "echo",
            "input": {"data": "stress test"},
        },
    }


def create_jsonrpc_request(envelope: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Wrap an envelope in a JSON-RPC 2.0 request."""
    return {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": envelope},
        "id": request_id,
    }


class StressTestUser(HttpUser):
    """Locust user class for stress testing.

    This user is optimized for maximum throughput to find the server's
    breaking point. Minimal wait time between requests.
    """

    wait_time = between(0.001, 0.005)

    sender = "urn:asap:agent:stress-client"
    recipient = "urn:asap:agent:default-server"

    def on_start(self) -> None:
        """Initialize request counter."""
        self.request_count = 0

    @task
    def stress_request(self) -> None:
        """Send task request at maximum rate."""
        self.request_count += 1
        request_id = f"stress-{self.request_count}"

        envelope = create_valid_envelope(self.sender, self.recipient)
        jsonrpc_request = create_jsonrpc_request(envelope, request_id)

        with self.client.post(
            "/asap",
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/asap [stress]",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "result" in data:
                        response.success()
                    elif "error" in data:
                        response.failure(f"Error: {data['error'].get('message', 'Unknown')}")
                    else:
                        response.failure("Invalid response")
                except Exception as e:
                    response.failure(f"Parse error: {e}")
            elif response.status_code == 429:
                response.failure("Rate limited")
            elif response.status_code == 503:
                response.failure("Service unavailable")
            else:
                response.failure(f"HTTP {response.status_code}")


class BurstTestUser(HttpUser):
    """User class for burst/spike testing.

    Simulates sudden bursts of traffic followed by quiet periods.
    Useful for testing auto-scaling and recovery behavior.
    """

    wait_time = between(0.0, 0.001)

    sender = "urn:asap:agent:burst-client"
    recipient = "urn:asap:agent:default-server"

    def on_start(self) -> None:
        """Initialize burst state."""
        self.request_count = 0
        self.burst_start = time.time()
        self.burst_duration = 5.0
        self.rest_duration = 2.0
        self.in_burst = True

    @task
    def burst_request(self) -> None:
        """Send requests in bursts."""
        now = time.time()
        elapsed = now - self.burst_start

        if self.in_burst and elapsed > self.burst_duration:
            self.in_burst = False
            self.burst_start = now
            time.sleep(self.rest_duration)
            self.in_burst = True
            self.burst_start = time.time()
            return

        self.request_count += 1
        request_id = f"burst-{self.request_count}"

        envelope = create_valid_envelope(self.sender, self.recipient)
        jsonrpc_request = create_jsonrpc_request(envelope, request_id)

        with self.client.post(
            "/asap",
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/asap [burst]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                else:
                    response.failure("Error response")
            else:
                response.failure(f"HTTP {response.status_code}")


# Event handlers


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs: Any) -> None:
    """Called when stress test starts."""
    global stress_metrics
    stress_metrics = StressMetrics()

    print("\n" + "=" * 60)
    print("ASAP Protocol Stress Test Starting")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print("Breaking point thresholds:")
    print(f"  - Error rate: >= {ERROR_RATE_THRESHOLD * 100}%")
    print(f"  - p95 latency: >= {P95_LATENCY_THRESHOLD_MS}ms (degraded)")
    print(f"  - p99 latency: >= {P99_LATENCY_THRESHOLD_MS}ms (breaking)")
    print("=" * 60 + "\n")


@events.request.add_listener
def on_request(
    request_type: str,
    name: str,
    response_time: float,
    response_length: int,
    response: Any,
    context: Any,
    exception: Any,
    **kwargs: Any,
) -> None:
    """Called on each request. Sample metrics periodically."""
    # Get environment from context if available
    env = kwargs.get("environment") or getattr(context, "environment", None)
    if env is None:
        return

    user_count = env.runner.user_count if env.runner else 0
    stress_metrics.maybe_sample(env.stats, user_count)


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs: Any) -> None:
    """Called when stress test stops. Print breaking point analysis."""
    # Final sample
    user_count = environment.runner.user_count if environment.runner else 0
    stress_metrics.maybe_sample(environment.stats, user_count)

    # Print summary
    stress_metrics.print_summary()

    # Also print Locust's standard summary
    stats = environment.stats
    total = stats.total

    if total.num_requests > 0:
        print("\n" + "-" * 40)
        print("FINAL STATISTICS:")
        print("-" * 40)
        print(f"Total requests: {total.num_requests:,}")
        print(f"Total failures: {total.num_failures:,}")
        print(f"Final RPS: {total.current_rps:.2f}")
        print(f"Final p95: {total.get_response_time_percentile(0.95):.2f}ms")
        print(f"Final p99: {total.get_response_time_percentile(0.99):.2f}ms")
        print(f"Final error rate: {total.num_failures / total.num_requests * 100:.3f}%")


# Programmatic execution support


def find_breaking_point(
    host: str,
    max_users: int = DEFAULT_MAX_USERS,
    step_size: int = DEFAULT_STEP_SIZE,
    step_time: int = DEFAULT_STEP_TIME,
) -> dict[str, Any]:
    """Run stress test programmatically to find breaking point.

    Gradually increases load until breaking point is detected.

    Args:
        host: Target server URL
        max_users: Maximum users to scale to
        step_size: Users added per step
        step_time: Duration per step in seconds

    Returns:
        Dictionary with breaking point analysis:
        - breaking_point_rps: RPS at which system broke (or None)
        - breaking_point_users: Users at which system broke (or None)
        - breaking_point_reason: Why system broke
        - max_sustainable_rps: Maximum healthy RPS
        - samples: All collected samples

    Example:
        >>> results = find_breaking_point("http://localhost:8000", max_users=200)
        >>> if results["breaking_point_rps"]:
        ...     print(f"System breaks at {results['breaking_point_rps']:.0f} RPS")
        >>> else:
        ...     print(f"System sustained {results['max_sustainable_rps']:.0f} RPS")
    """
    import gevent
    from locust.runners import LocalRunner

    global stress_metrics
    stress_metrics = StressMetrics()

    # Create environment
    env = Environment(user_classes=[StressTestUser])
    env.host = host
    runner = LocalRunner(env)

    # Run step-load test
    current_users = 0
    steps = max_users // step_size

    for step in range(1, steps + 1):
        current_users = min(step * step_size, max_users)
        print(f"\n--- Step {step}/{steps}: {current_users} users ---")

        # Spawn users
        runner.start(current_users, spawn_rate=step_size)

        # Run for step_time
        start = time.time()
        while time.time() - start < step_time:
            stress_metrics.maybe_sample(env.stats, runner.user_count)
            gevent.sleep(1)

        # Check if we hit breaking point
        if stress_metrics.breaking_point_rps is not None:
            print(f"\nBreaking point detected at {current_users} users!")
            break

    runner.stop()

    return {
        "breaking_point_rps": stress_metrics.breaking_point_rps,
        "breaking_point_users": stress_metrics.breaking_point_users,
        "breaking_point_reason": stress_metrics.breaking_point_reason,
        "max_sustainable_rps": stress_metrics.get_max_sustainable_rps(),
        "samples": stress_metrics.samples,
    }


# Configuration from environment
def get_stress_config() -> dict[str, Any]:
    """Get stress test configuration from environment variables."""
    return {
        "max_users": int(os.getenv("ASAP_STRESS_MAX_USERS", str(DEFAULT_MAX_USERS))),
        "step_size": int(os.getenv("ASAP_STRESS_STEP_SIZE", str(DEFAULT_STEP_SIZE))),
        "step_time": int(os.getenv("ASAP_STRESS_STEP_TIME", str(DEFAULT_STEP_TIME))),
    }
