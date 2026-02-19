"""v1.4.0 End-to-End Showcase: Storage pagination (Usage & SLA history).

Demonstrates v1.4.0 pagination in practice:
1. Seed usage and SLA metrics into in-memory storage
2. GET /usage?limit=2&offset=0 and offset=2 to show page 1 and page 2
3. GET /sla/history?limit=2&offset=0 and show total, count, offset, limit

Run:
    uv run python -m asap.examples.v1_4_0_showcase
"""

from __future__ import annotations

import asyncio
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from asap.economics import (
    InMemoryMeteringStorage,
    InMemorySLAStorage,
    SLAMetrics,
    UsageMetrics,
)
from asap.models.entities import (
    Capability,
    Endpoint,
    Manifest,
    Skill,
)
from asap.transport.handlers import HandlerRegistry, create_echo_handler
from asap.transport.server import create_app

# Constants
AGENT_URN = "urn:asap:agent:v14-showcase"
SHOWCASE_PORT = 8003
BASE_URL = f"http://127.0.0.1:{SHOWCASE_PORT}"
READY_TIMEOUT_SECONDS = 10.0
READY_POLL_INTERVAL_SECONDS = 0.2
PAGE_SIZE = 2
NUM_USAGE_RECORDS = 5
NUM_SLA_RECORDS = 5


def _log(msg: str) -> None:
    print(f"  {msg}")


def _log_step(step: int, title: str) -> None:
    print(f"\n--- Step {step}: {title} ---")


def _create_showcase_app() -> Any:
    manifest = Manifest(
        id=AGENT_URN,
        name="v1.4.0 Pagination Showcase",
        version="1.4.0",
        description="Demonstrates pagination on Usage and SLA history APIs",
        capabilities=Capability(
            asap_version="0.1",
            skills=[Skill(id="echo", description="Echo")],
            state_persistence=False,
        ),
        endpoints=Endpoint(asap=f"{BASE_URL}/asap"),
    )

    metering = InMemoryMeteringStorage()
    sla_storage = InMemorySLAStorage()

    registry = HandlerRegistry()
    registry.register("task.request", create_echo_handler())

    app = create_app(
        manifest,
        registry=registry,
        metering_storage=metering,
        sla_storage=sla_storage,
        rate_limit="999999/minute",
    )

    @app.post("/_demo/seed")
    async def seed_data() -> dict[str, Any]:
        """Seed metering and SLA storage for pagination demo."""
        now = datetime.now(timezone.utc)
        base_ts = now - timedelta(minutes=30)

        for i in range(NUM_USAGE_RECORDS):
            m = UsageMetrics(
                task_id=f"task_{i:03d}",
                agent_id=AGENT_URN,
                consumer_id="urn:asap:agent:consumer",
                tokens_in=100 * (i + 1),
                tokens_out=50 * (i + 1),
                duration_ms=200 + i * 10,
                api_calls=1 + i,
                timestamp=base_ts + timedelta(minutes=i * 2),
            )
            await metering.record(m)

        for i in range(NUM_SLA_RECORDS):
            start = base_ts + timedelta(minutes=i * 5)
            end = start + timedelta(minutes=5)
            s = SLAMetrics(
                agent_id=AGENT_URN,
                period_start=start,
                period_end=end,
                uptime_percent=99.5 - i * 0.1,
                latency_p95_ms=100 + i * 20,
                error_rate_percent=0.1 * i,
                tasks_completed=10 + i,
                tasks_failed=0,
            )
            await sla_storage.record_metrics(s)

        return {
            "usage_seeded": NUM_USAGE_RECORDS,
            "sla_seeded": NUM_SLA_RECORDS,
        }

    return app


def wait_for_ready(url: str, timeout_seconds: float) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(READY_POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Service not ready after {timeout_seconds:.1f}s: {url}")


async def run_showcase() -> None:
    _log_step(1, "Seed usage and SLA metrics")
    seed_resp = httpx.post(f"{BASE_URL}/_demo/seed", timeout=5.0)
    if seed_resp.status_code != 200:
        raise RuntimeError(f"Seed failed: {seed_resp.status_code} {seed_resp.text}")
    data = seed_resp.json()
    _log(f"Seeded {data['usage_seeded']} usage records and {data['sla_seeded']} SLA metrics")

    _log_step(2, "Pagination on GET /usage (limit=2)")
    page1 = httpx.get(f"{BASE_URL}/usage?limit={PAGE_SIZE}&offset=0", timeout=5.0)
    if page1.status_code != 200:
        raise RuntimeError(f"Usage API failed: {page1.status_code}")
    j1 = page1.json()
    _log(f"Page 1: count={j1['count']}, offset=0 — task_ids: {[d['task_id'] for d in j1['data']]}")

    page2 = httpx.get(f"{BASE_URL}/usage?limit={PAGE_SIZE}&offset={PAGE_SIZE}", timeout=5.0)
    if page2.status_code != 200:
        raise RuntimeError(f"Usage API failed: {page2.status_code}")
    j2 = page2.json()
    _log(f"Page 2: count={j2['count']}, offset={PAGE_SIZE} — task_ids: {[d['task_id'] for d in j2['data']]}")

    _log_step(3, "Pagination on GET /sla/history (limit=2, total in response)")
    hist1 = httpx.get(f"{BASE_URL}/sla/history?limit={PAGE_SIZE}&offset=0", timeout=5.0)
    if hist1.status_code != 200:
        raise RuntimeError(f"SLA history failed: {hist1.status_code}")
    h1 = hist1.json()
    _log(
        f"Page 1: count={h1['count']}, total={h1['total']}, offset={h1['offset']}, limit={h1['limit']}"
    )
    _log(f"  First period: {h1['data'][0]['period_start'][:19]} — {h1['data'][0]['period_end'][:19]}")

    hist2 = httpx.get(f"{BASE_URL}/sla/history?limit={PAGE_SIZE}&offset={PAGE_SIZE}", timeout=5.0)
    if hist2.status_code != 200:
        raise RuntimeError(f"SLA history failed: {hist2.status_code}")
    h2 = hist2.json()
    _log(f"Page 2: count={h2['count']}, total={h2['total']}, offset={h2['offset']}")

    print("\n✅ v1.4.0 Showcase complete (pagination demonstrated).\n")


def main() -> None:
    print("\n🚀 ASAP v1.4.0 End-to-End Showcase — Pagination\n")
    print("Demonstrating: Usage API and SLA history API with limit/offset.\n")

    app = _create_showcase_app()
    server_error: Exception | None = None

    def run_server() -> None:
        nonlocal server_error
        import uvicorn

        try:
            uvicorn.run(
                app,
                host="127.0.0.1",
                port=SHOWCASE_PORT,
                log_level="warning",
            )
        except Exception as e:
            server_error = e

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    try:
        wait_for_ready(f"{BASE_URL}/health", READY_TIMEOUT_SECONDS)
        _log("Server ready")
        asyncio.run(run_showcase())
    except Exception as e:
        print(f"\n❌ Showcase failed: {e}\n")
        raise
    finally:
        if server_error:
            print(f"Server error: {server_error}")


if __name__ == "__main__":
    main()
