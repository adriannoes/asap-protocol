"""Load testing for ASAP protocol using Locust.

This module provides load testing scenarios for the ASAP protocol server,
measuring latency percentiles (p50, p95, p99) and error rates under sustained load.

Performance targets:
- Sustained load: 1000 req/sec for 60 seconds
- Latency: < 5ms p95
- Error rate: < 0.1%

Running load tests:

1. Start the ASAP server in one terminal:
   ```bash
   uv run uvicorn asap.transport.server:app --host 0.0.0.0 --port 8000
   ```

2. Run load test in another terminal:
   ```bash
   # Headless mode (CI/automated):
   uv run locust -f benchmarks/load_test.py --headless \
       -u 100 -r 10 -t 60s --host http://localhost:8000

   # Web UI mode (interactive):
   uv run locust -f benchmarks/load_test.py --host http://localhost:8000
   # Then open http://localhost:8089 in browser
   ```

Command-line options:
- `-u 100`: Number of concurrent users (adjust to reach target RPS)
- `-r 10`: Spawn rate (users/second)
- `-t 60s`: Test duration
- `--host`: Target server URL

Environment variables:
- ASAP_LOAD_TEST_USERS: Override number of concurrent users (default: 100)
- ASAP_LOAD_TEST_SPAWN_RATE: Override spawn rate (default: 10)
- ASAP_LOAD_TEST_RUN_TIME: Override run time (default: 60s)

Output:
- Console shows real-time statistics
- Final summary includes latency percentiles and error rates
- Use --html=report.html for HTML report
- Use --csv=results for CSV output
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from locust import HttpUser, between, events, task
from locust.env import Environment
from locust.stats import stats_printer

# Load test configuration constants
DEFAULT_USERS = 100  # Target concurrent users
DEFAULT_SPAWN_RATE = 10  # Users spawned per second
DEFAULT_RUN_TIME = "60s"  # Test duration

# Performance targets
TARGET_RPS = 1000  # Target requests per second
TARGET_P95_MS = 5.0  # Target p95 latency in milliseconds
TARGET_ERROR_RATE = 0.001  # Target error rate (0.1%)


def create_valid_envelope(sender: str, recipient: str, skill_id: str = "echo") -> dict[str, Any]:
    """Create a valid ASAP envelope for load testing.

    Args:
        sender: Sender agent URN
        recipient: Recipient agent URN
        skill_id: Skill ID to invoke (default: "echo")

    Returns:
        Dictionary representing a valid ASAP envelope
    """
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
            "conversation_id": f"conv_{uuid.uuid4().hex[:12]}",
            "skill_id": skill_id,
            "input": {
                "message": "Load test message",
                "timestamp": now,
            },
        },
    }


def create_jsonrpc_request(envelope: dict[str, Any], request_id: str) -> dict[str, Any]:
    """Wrap an envelope in a JSON-RPC 2.0 request.

    Args:
        envelope: ASAP envelope dictionary
        request_id: JSON-RPC request ID

    Returns:
        JSON-RPC 2.0 request dictionary
    """
    return {
        "jsonrpc": "2.0",
        "method": "asap.send",
        "params": {"envelope": envelope},
        "id": request_id,
    }


class ASAPLoadTestUser(HttpUser):
    """Locust user class for ASAP protocol load testing.

    This user simulates an agent sending task requests to an ASAP server.
    It measures response times and tracks errors for latency analysis.

    Attributes:
        wait_time: Time between requests (simulates think time)
        sender: Sender agent URN
        recipient: Recipient agent URN
    """

    # Wait time between requests (0.1-0.5s gives ~2-10 RPS per user)
    # With 100 users and 0.1-0.5s wait: ~200-1000 RPS
    wait_time = between(0.01, 0.05)  # 20-100 RPS per user

    # Agent identifiers
    sender = "urn:asap:agent:loadtest-client"
    recipient = "urn:asap:agent:default-server"

    def on_start(self) -> None:
        """Called when a user starts. Initialize request counter."""
        self.request_count = 0

    @task(weight=10)
    def send_task_request(self) -> None:
        """Send a task.request envelope to the ASAP server.

        This is the primary load test task, simulating normal agent communication.
        Weight of 10 makes this the most common operation.
        """
        self.request_count += 1
        request_id = f"loadtest-{self.request_count}-{uuid.uuid4().hex[:8]}"

        envelope = create_valid_envelope(self.sender, self.recipient)
        jsonrpc_request = create_jsonrpc_request(envelope, request_id)

        with self.client.post(
            "/asap",
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/asap [task.request]",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check for JSON-RPC success response
                    if "result" in data:
                        response.success()
                    elif "error" in data:
                        error = data["error"]
                        response.failure(f"JSON-RPC error: {error.get('message', 'Unknown')}")
                    else:
                        response.failure("Invalid JSON-RPC response format")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            elif response.status_code == 429:
                # Rate limited - mark as failure but log separately
                response.failure("Rate limited (429)")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(weight=2)
    def get_manifest(self) -> None:
        """Fetch the agent manifest.

        Lower weight (2 vs 10) simulates occasional discovery requests.
        """
        with self.client.get(
            "/.well-known/asap/manifest.json",
            name="/manifest [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "id" in data and "capabilities" in data:
                        response.success()
                    else:
                        response.failure("Invalid manifest structure")
                except Exception as e:
                    response.failure(f"Failed to parse manifest: {e}")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(weight=1)
    def get_metrics(self) -> None:
        """Fetch Prometheus metrics.

        Lowest weight (1) simulates occasional monitoring requests.
        """
        with self.client.get(
            "/asap/metrics",
            name="/metrics [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                if "asap_" in response.text:
                    response.success()
                else:
                    response.failure("Missing ASAP metrics prefix")
            else:
                response.failure(f"HTTP {response.status_code}")


class ASAPSustainedLoadUser(HttpUser):
    """Locust user for sustained high-throughput load testing.

    This user class is optimized for maximum throughput with minimal wait time.
    Use this to test the server's maximum capacity.

    Example:
        uv run locust -f benchmarks/load_test.py --headless \
            -u 500 -r 50 -t 60s --host http://localhost:8000 \
            --class-picker ASAPSustainedLoadUser
    """

    # Minimal wait for maximum throughput
    wait_time = between(0.001, 0.01)  # 100-1000 RPS per user

    sender = "urn:asap:agent:sustained-client"
    recipient = "urn:asap:agent:default-server"

    def on_start(self) -> None:
        """Called when a user starts. Initialize request counter."""
        self.request_count = 0

    @task
    def send_minimal_request(self) -> None:
        """Send minimal task request for throughput testing.

        Uses smallest valid payload to maximize throughput.
        """
        self.request_count += 1
        request_id = f"sustained-{self.request_count}"

        envelope = create_valid_envelope(self.sender, self.recipient)
        jsonrpc_request = create_jsonrpc_request(envelope, request_id)

        with self.client.post(
            "/asap",
            json=jsonrpc_request,
            headers={"Content-Type": "application/json"},
            catch_response=True,
            name="/asap [sustained]",
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    response.failure(f"Error: {data['error'].get('message', 'Unknown')}")
                else:
                    response.failure("Invalid response")
            else:
                response.failure(f"HTTP {response.status_code}")


# Event handlers for custom reporting


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs: Any) -> None:
    """Called when load test starts. Log configuration."""
    print("\n" + "=" * 60)
    print("ASAP Protocol Load Test Starting")
    print("=" * 60)
    print(f"Target: {environment.host}")
    print("Performance targets:")
    print(f"  - RPS: {TARGET_RPS} req/sec")
    print(f"  - p95 latency: <{TARGET_P95_MS}ms")
    print(f"  - Error rate: <{TARGET_ERROR_RATE * 100}%")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs: Any) -> None:
    """Called when load test stops. Print summary with percentiles."""
    print("\n" + "=" * 60)
    print("ASAP Protocol Load Test Complete")
    print("=" * 60)

    stats = environment.stats

    # Print summary for each request type
    for name, entry in stats.entries.items():
        if entry.num_requests == 0:
            continue

        print(f"\n{name}:")
        print(f"  Requests: {entry.num_requests:,}")
        print(f"  Failures: {entry.num_failures:,}")
        print(f"  RPS: {entry.current_rps:.2f}")

        # Calculate latency percentiles
        if entry.num_requests > 0:
            p50 = entry.get_response_time_percentile(0.50)
            p95 = entry.get_response_time_percentile(0.95)
            p99 = entry.get_response_time_percentile(0.99)

            print("  Latency percentiles:")
            print(f"    p50: {p50:.2f}ms")
            print(f"    p95: {p95:.2f}ms")
            print(f"    p99: {p99:.2f}ms")
            print(f"  Min: {entry.min_response_time:.2f}ms")
            print(f"  Max: {entry.max_response_time:.2f}ms")
            print(f"  Avg: {entry.avg_response_time:.2f}ms")

    # Print aggregate statistics
    total = stats.total
    if total.num_requests > 0:
        error_rate = total.num_failures / total.num_requests
        p95_total = total.get_response_time_percentile(0.95)

        print("\n" + "-" * 40)
        print("AGGREGATE RESULTS:")
        print("-" * 40)
        print(f"Total requests: {total.num_requests:,}")
        print(f"Total failures: {total.num_failures:,}")
        print(f"Error rate: {error_rate * 100:.3f}%")
        print(f"Aggregate RPS: {total.current_rps:.2f}")
        print(f"Aggregate p95: {p95_total:.2f}ms")

        # Check against targets
        print("\n" + "-" * 40)
        print("TARGET VERIFICATION:")
        print("-" * 40)

        rps_pass = total.current_rps >= TARGET_RPS * 0.8  # 80% of target
        p95_pass = p95_total <= TARGET_P95_MS
        error_pass = error_rate <= TARGET_ERROR_RATE

        print(
            f"RPS >= {TARGET_RPS * 0.8:.0f}: {'PASS' if rps_pass else 'FAIL'} ({total.current_rps:.2f})"
        )
        print(f"p95 <= {TARGET_P95_MS}ms: {'PASS' if p95_pass else 'FAIL'} ({p95_total:.2f}ms)")
        print(
            f"Error rate <= {TARGET_ERROR_RATE * 100}%: {'PASS' if error_pass else 'FAIL'} ({error_rate * 100:.3f}%)"
        )

        if rps_pass and p95_pass and error_pass:
            print("\n✅ ALL TARGETS MET")
        else:
            print("\n❌ SOME TARGETS NOT MET")

    print("\n" + "=" * 60)


# Optional: Custom test configuration from environment


def get_config_from_env() -> dict[str, Any]:
    """Get load test configuration from environment variables.

    Returns:
        Dictionary with configuration values
    """
    return {
        "users": int(os.getenv("ASAP_LOAD_TEST_USERS", str(DEFAULT_USERS))),
        "spawn_rate": int(os.getenv("ASAP_LOAD_TEST_SPAWN_RATE", str(DEFAULT_SPAWN_RATE))),
        "run_time": os.getenv("ASAP_LOAD_TEST_RUN_TIME", DEFAULT_RUN_TIME),
    }


# Programmatic execution support (for pytest integration)


def run_load_test(
    host: str,
    users: int = DEFAULT_USERS,
    spawn_rate: int = DEFAULT_SPAWN_RATE,
    run_time: str = DEFAULT_RUN_TIME,
) -> dict[str, Any]:
    """Run load test programmatically and return results.

    This function allows running load tests from Python code or pytest.

    Args:
        host: Target server URL (e.g., "http://localhost:8000")
        users: Number of concurrent users
        spawn_rate: Users spawned per second
        run_time: Test duration (e.g., "60s", "5m")

    Returns:
        Dictionary with test results including:
        - total_requests: Total requests made
        - total_failures: Total failed requests
        - rps: Requests per second
        - p50_ms: 50th percentile latency
        - p95_ms: 95th percentile latency
        - p99_ms: 99th percentile latency
        - error_rate: Failure rate as decimal

    Example:
        >>> results = run_load_test("http://localhost:8000", users=50, run_time="30s")
        >>> assert results["p95_ms"] < 5.0
        >>> assert results["error_rate"] < 0.001
    """
    import gevent
    from locust.env import Environment
    from locust.runners import LocalRunner

    # Create environment and runner
    env = Environment(user_classes=[ASAPLoadTestUser])
    env.host = host
    runner = LocalRunner(env)

    # Parse run_time
    if run_time.endswith("s"):
        duration_seconds = int(run_time[:-1])
    elif run_time.endswith("m"):
        duration_seconds = int(run_time[:-1]) * 60
    else:
        duration_seconds = int(run_time)

    # Start the test
    runner.start(users, spawn_rate=spawn_rate)

    # Run for specified duration
    gevent.spawn(stats_printer(env.stats)).join(timeout=duration_seconds)

    # Stop the test
    runner.stop()

    # Collect results
    total = env.stats.total
    results: dict[str, Any] = {
        "total_requests": total.num_requests,
        "total_failures": total.num_failures,
        "rps": total.current_rps,
        "p50_ms": total.get_response_time_percentile(0.50) if total.num_requests > 0 else 0,
        "p95_ms": total.get_response_time_percentile(0.95) if total.num_requests > 0 else 0,
        "p99_ms": total.get_response_time_percentile(0.99) if total.num_requests > 0 else 0,
        "error_rate": (total.num_failures / total.num_requests if total.num_requests > 0 else 0),
        "min_ms": total.min_response_time if total.num_requests > 0 else 0,
        "max_ms": total.max_response_time if total.num_requests > 0 else 0,
        "avg_ms": total.avg_response_time if total.num_requests > 0 else 0,
    }

    return results
