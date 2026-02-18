"""SLA (Service Level Agreement) definitions and types (v1.3).

This module provides the SLA schema used in the manifest (SLADefinition),
plus SLAMetrics and SLABreach for tracking and breach detection.
Helpers for metrics collection (uptime, latency p95, error rate) and
rolling windows (1h, 24h, 7d, 30d) are included for use with health and metering.
Breach conditions (availability, latency, error rate) are defined and evaluated
against SLADefinition and SLAMetrics.

Example:
    >>> from asap.economics.sla import SLADefinition
    >>> sla = SLADefinition(
    ...     availability="99.5%",
    ...     max_latency_p95_ms=500,
    ...     max_error_rate="1%",
    ...     support_hours="24/7",
    ... )
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Literal, Protocol, runtime_checkable

from pydantic import Field

from asap.models.base import ASAPBaseModel
from asap.models.entities import SLADefinition


@runtime_checkable
class SLAStorageProtocol(Protocol):
    """Minimal protocol for recording breaches (avoids circular import with sla_storage)."""

    async def record_breach(self, breach: "SLABreach") -> None: ...


# Breach type identifiers (align with SLABreach.breach_type).
BREACH_TYPE_AVAILABILITY: Literal["availability"] = "availability"
BREACH_TYPE_LATENCY: Literal["latency"] = "latency"
BREACH_TYPE_ERROR_RATE: Literal["error_rate"] = "error_rate"
BREACH_TYPES: tuple[str, ...] = (
    BREACH_TYPE_AVAILABILITY,
    BREACH_TYPE_LATENCY,
    BREACH_TYPE_ERROR_RATE,
)

# Severity levels for breaches.
SEVERITY_WARNING: Literal["warning"] = "warning"
SEVERITY_CRITICAL: Literal["critical"] = "critical"
SEVERITIES: tuple[str, ...] = (SEVERITY_WARNING, SEVERITY_CRITICAL)

# Thresholds for severity: critical when breach is severe enough.
AVAILABILITY_CRITICAL_BELOW_PERCENT = 95.0
LATENCY_CRITICAL_MULTIPLIER = 2.0
ERROR_RATE_CRITICAL_PERCENT = 5.0
ERROR_RATE_CRITICAL_MULTIPLIER = 2.0

# Rolling window names for metrics aggregation.
ROLLING_WINDOW_1H: Literal["1h"] = "1h"
ROLLING_WINDOW_24H: Literal["24h"] = "24h"
ROLLING_WINDOW_7D: Literal["7d"] = "7d"
ROLLING_WINDOW_30D: Literal["30d"] = "30d"
ROLLING_WINDOWS = ("1h", "24h", "7d", "30d")


class SLAMetrics(ASAPBaseModel):
    """Aggregated SLA metrics for an agent over a time period.

    Used to compare actual performance vs SLADefinition (availability,
    latency, error rate). Computed from health checks and metering data.

    Attributes:
        agent_id: Agent URN.
        period_start: Start of the measurement period (UTC).
        period_end: End of the measurement period (UTC).
        uptime_percent: Uptime percentage (0–100) from health checks.
        latency_p95_ms: 95th percentile latency in milliseconds.
        error_rate_percent: Error rate as percentage (0–100).
        tasks_completed: Number of tasks completed in the period.
        tasks_failed: Number of tasks failed in the period.
    """

    agent_id: str = Field(..., description="Agent URN")
    period_start: datetime = Field(..., description="Period start (UTC)")
    period_end: datetime = Field(..., description="Period end (UTC)")
    uptime_percent: float = Field(..., ge=0, le=100, description="Uptime percentage")
    latency_p95_ms: int = Field(..., ge=0, description="P95 latency in ms")
    error_rate_percent: float = Field(..., ge=0, le=100, description="Error rate percentage")
    tasks_completed: int = Field(..., ge=0, description="Tasks completed in period")
    tasks_failed: int = Field(..., ge=0, description="Tasks failed in period")


class SLABreach(ASAPBaseModel):
    """Record of an SLA breach (threshold exceeded).

    Attributes:
        id: Unique breach identifier.
        agent_id: Agent URN that breached.
        breach_type: One of "availability", "latency", "error_rate".
        threshold: Promised threshold (e.g. "99.5%").
        actual: Actual value observed (e.g. "98.2%").
        severity: "warning" or "critical".
        detected_at: When the breach was detected (UTC).
        resolved_at: When the breach was resolved, if any (UTC).
    """

    id: str = Field(..., description="Unique breach identifier")
    agent_id: str = Field(..., description="Agent URN")
    breach_type: str = Field(..., description="availability | latency | error_rate")
    threshold: str = Field(..., description="Promised threshold")
    actual: str = Field(..., description="Actual value observed")
    severity: str = Field(..., description="warning | critical")
    detected_at: datetime = Field(..., description="When breach was detected (UTC)")
    resolved_at: datetime | None = Field(default=None, description="When resolved (UTC)")


class BreachConditionResult(ASAPBaseModel):
    """Result of evaluating one breach condition (no id/agent/dates; used by detector).

    Attributes:
        breach_type: One of "availability", "latency", "error_rate".
        threshold: Promised threshold as string (e.g. "99.5%", "500ms").
        actual: Actual value observed as string.
        severity: "warning" or "critical".
    """

    breach_type: Literal["availability", "latency", "error_rate"] = Field(
        ..., description="Type of breach"
    )
    threshold: str = Field(..., description="Promised threshold")
    actual: str = Field(..., description="Actual value observed")
    severity: Literal["warning", "critical"] = Field(..., description="Severity level")


def parse_percentage(s: str) -> float:
    """Parse a percentage string (e.g. '99.5%', '1%') to a float in 0–100.

    Args:
        s: String like "99.5%" or "1%".

    Returns:
        Float value in [0, 100].

    Raises:
        ValueError: If string does not match expected pattern.
    """
    s = s.strip()
    match = re.match(r"^(-?[\d.]+)\s*%?\s*$", s, re.IGNORECASE)
    if not match:
        raise ValueError(f"Invalid percentage string: {s!r}")
    value = float(match.group(1))
    return min(100.0, max(0.0, value))


def evaluate_breach_conditions(
    sla: SLADefinition | None,
    metrics: SLAMetrics,
) -> list[BreachConditionResult]:
    """Evaluate SLA breach conditions: availability, latency, error rate.

    - Availability breach: uptime_percent below SLA availability threshold.
    - Latency breach: latency_p95_ms above SLA max_latency_p95_ms.
    - Error rate breach: error_rate_percent above SLA max_error_rate.

    Severity is "critical" when the breach is severe (e.g. availability < 95%,
    latency > 2x limit, error rate > 5% or > 2x limit); otherwise "warning".

    Args:
        sla: Agent SLA definition (from manifest). If None, no breaches.
        metrics: Observed metrics for the agent.

    Returns:
        List of breach condition results (one per violated threshold).
    """
    if sla is None:
        return []

    results: list[BreachConditionResult] = []

    # 1. Availability: breach when uptime is below promised.
    if sla.availability is not None:
        try:
            required_uptime = parse_percentage(sla.availability)
            if metrics.uptime_percent < required_uptime:
                severity = (
                    SEVERITY_CRITICAL
                    if metrics.uptime_percent < AVAILABILITY_CRITICAL_BELOW_PERCENT
                    else SEVERITY_WARNING
                )
                results.append(
                    BreachConditionResult(
                        breach_type=BREACH_TYPE_AVAILABILITY,
                        threshold=f"{required_uptime}%",
                        actual=f"{metrics.uptime_percent}%",
                        severity=severity,
                    )
                )
        except ValueError:
            pass

    # 2. Latency: breach when p95 is above promised max.
    if sla.max_latency_p95_ms is not None and metrics.latency_p95_ms > sla.max_latency_p95_ms:
        severity = (
            SEVERITY_CRITICAL
            if metrics.latency_p95_ms >= sla.max_latency_p95_ms * LATENCY_CRITICAL_MULTIPLIER
            else SEVERITY_WARNING
        )
        results.append(
            BreachConditionResult(
                breach_type=BREACH_TYPE_LATENCY,
                threshold=f"{sla.max_latency_p95_ms}ms",
                actual=f"{metrics.latency_p95_ms}ms",
                severity=severity,
            )
        )

    # 3. Error rate: breach when error rate is above promised max.
    if sla.max_error_rate is not None:
        try:
            max_allowed = parse_percentage(sla.max_error_rate)
            if metrics.error_rate_percent > max_allowed:
                severity = (
                    SEVERITY_CRITICAL
                    if (
                        metrics.error_rate_percent >= ERROR_RATE_CRITICAL_PERCENT
                        or metrics.error_rate_percent
                        >= max_allowed * ERROR_RATE_CRITICAL_MULTIPLIER
                    )
                    else SEVERITY_WARNING
                )
                results.append(
                    BreachConditionResult(
                        breach_type=BREACH_TYPE_ERROR_RATE,
                        threshold=f"{max_allowed}%",
                        actual=f"{metrics.error_rate_percent}%",
                        severity=severity,
                    )
                )
        except ValueError:
            pass

    return results


# --- Breach detector and alert hooks (Task 3.3.2, 3.3.3) ---


def _default_breach_alert(breach: SLABreach) -> None:
    """Default alert hook: log a warning when an SLA breach is detected."""
    from asap.observability import get_logger

    logger = get_logger(__name__)
    logger.warning(
        "asap.sla.breach",
        breach_id=breach.id,
        agent_id=breach.agent_id,
        breach_type=breach.breach_type,
        threshold=breach.threshold,
        actual=breach.actual,
        severity=breach.severity,
    )


BreachAlertCallback = Callable[[SLABreach], Awaitable[None] | None]


class BreachDetector:
    """Compares actual metrics to SLA definition and records breaches.

    When a threshold is crossed, the breach is stored via SLAStorage and
    the optional on_breach callback is invoked (default: log warning).
    """

    def __init__(
        self,
        storage: SLAStorageProtocol,
        *,
        on_breach: BreachAlertCallback | None = None,
    ) -> None:
        self._storage = storage
        self._on_breach: BreachAlertCallback = on_breach or _default_breach_alert

    async def check_and_record(
        self,
        agent_id: str,
        sla: SLADefinition | None,
        metrics: SLAMetrics,
    ) -> list[SLABreach]:
        """Evaluate breach conditions, record breaches, and invoke alert callback.

        Args:
            agent_id: Agent URN.
            sla: SLA definition from manifest (or None).
            metrics: Observed metrics for the period.

        Returns:
            List of newly recorded breaches (may be empty).
        """
        conditions = evaluate_breach_conditions(sla, metrics)
        if not conditions:
            return []

        now = datetime.now(timezone.utc)
        recorded: list[SLABreach] = []
        for cond in conditions:
            breach = SLABreach(
                id=f"breach_{uuid.uuid4().hex}",
                agent_id=agent_id,
                breach_type=cond.breach_type,
                threshold=cond.threshold,
                actual=cond.actual,
                severity=cond.severity,
                detected_at=now,
                resolved_at=None,
            )
            await self._storage.record_breach(breach)
            recorded.append(breach)
            result = self._on_breach(breach)
            if result is not None:
                await result  # Awaitable[None] from async callback
        return recorded


# --- Metrics collection helpers (use with health checks + MeteringStorage) ---


def compute_uptime_percent(ok_count: int, total_count: int) -> float:
    """Compute uptime percentage from health check success count.

    Args:
        ok_count: Number of successful health checks.
        total_count: Total health checks in the period.

    Returns:
        Uptime 0–100. Returns 100.0 if total_count is 0.
    """
    if total_count <= 0:
        return 100.0
    return min(100.0, max(0.0, 100.0 * ok_count / total_count))


def compute_latency_p95_ms(durations_ms: list[int]) -> int:
    """Compute 95th percentile latency from a list of durations in ms.

    Args:
        durations_ms: List of task durations in milliseconds.

    Returns:
        P95 latency in ms. Returns 0 if list is empty.
    """
    if not durations_ms:
        return 0
    sorted_d = sorted(durations_ms)
    idx = int(0.95 * (len(sorted_d) - 1)) if len(sorted_d) > 1 else 0
    return sorted_d[min(idx, len(sorted_d) - 1)]


def compute_error_rate_percent(tasks_completed: int, tasks_failed: int) -> float:
    """Compute error rate percentage from completed and failed task counts.

    Args:
        tasks_completed: Number of tasks that completed successfully.
        tasks_failed: Number of tasks that failed.

    Returns:
        Error rate 0–100. Returns 0.0 if no tasks.
    """
    total = tasks_completed + tasks_failed
    if total <= 0:
        return 0.0
    return min(100.0, max(0.0, 100.0 * tasks_failed / total))


def rolling_window_bounds(
    window: Literal["1h", "24h", "7d", "30d"],
    end: datetime | None = None,
) -> tuple[datetime, datetime]:
    """Return (start, end) for a rolling window ending at end (or now).

    Args:
        window: One of "1h", "24h", "7d", "30d".
        end: End of the window (UTC). Defaults to now.

    Returns:
        (period_start, period_end) in UTC.
    """
    from datetime import timedelta

    end = end or datetime.now(timezone.utc)
    if window == "1h":
        delta = timedelta(hours=1)
    elif window == "24h":
        delta = timedelta(hours=24)
    elif window == "7d":
        delta = timedelta(days=7)
    elif window == "30d":
        delta = timedelta(days=30)
    else:
        raise ValueError(f"window must be one of {ROLLING_WINDOWS}; got {window!r}")
    start = end - delta
    return (start, end)


def aggregate_sla_metrics(metrics: list[SLAMetrics]) -> SLAMetrics | None:
    """Aggregate multiple SLAMetrics (same agent) into one.

    Uptime and error rate are weighted by task volume; latency is p95 of
    the reported latency_p95_ms values (approximation). Period is min start
    to max end.

    Args:
        metrics: Non-empty list of SLAMetrics for the same agent.

    Returns:
        Single SLAMetrics, or None if metrics is empty.
    """
    if not metrics:
        return None
    agent_id = metrics[0].agent_id
    period_start = min(m.period_start for m in metrics)
    period_end = max(m.period_end for m in metrics)
    total_completed = sum(m.tasks_completed for m in metrics)
    total_failed = sum(m.tasks_failed for m in metrics)
    total_tasks = total_completed + total_failed
    if total_tasks > 0:
        uptime_weighted = (
            sum(m.uptime_percent * (m.tasks_completed + m.tasks_failed) for m in metrics)
            / total_tasks
        )
        error_weighted = (
            sum(m.error_rate_percent * (m.tasks_completed + m.tasks_failed) for m in metrics)
            / total_tasks
        )
    else:
        uptime_weighted = sum(m.uptime_percent for m in metrics) / len(metrics)
        error_weighted = sum(m.error_rate_percent for m in metrics) / len(metrics)
    latencies = [m.latency_p95_ms for m in metrics]
    latency_p95 = compute_latency_p95_ms(latencies)
    return SLAMetrics(
        agent_id=agent_id,
        period_start=period_start,
        period_end=period_end,
        uptime_percent=round(uptime_weighted, 2),
        latency_p95_ms=latency_p95,
        error_rate_percent=round(error_weighted, 2),
        tasks_completed=total_completed,
        tasks_failed=total_failed,
    )


__all__ = [
    "SLADefinition",
    "SLAMetrics",
    "SLABreach",
    "BreachConditionResult",
    "BreachDetector",
    "BreachAlertCallback",
    "SLAStorageProtocol",
    "BREACH_TYPE_AVAILABILITY",
    "BREACH_TYPE_LATENCY",
    "BREACH_TYPE_ERROR_RATE",
    "BREACH_TYPES",
    "SEVERITY_WARNING",
    "SEVERITY_CRITICAL",
    "SEVERITIES",
    "parse_percentage",
    "evaluate_breach_conditions",
    "ROLLING_WINDOW_1H",
    "ROLLING_WINDOW_24H",
    "ROLLING_WINDOW_7D",
    "ROLLING_WINDOW_30D",
    "ROLLING_WINDOWS",
    "compute_uptime_percent",
    "compute_latency_p95_ms",
    "compute_error_rate_percent",
    "rolling_window_bounds",
    "aggregate_sla_metrics",
]
