"""ASAP Protocol Metrics Collection.

This module provides Prometheus-compatible metrics collection for ASAP servers.
Metrics are collected during request processing and exposed via the /asap/metrics endpoint.

Supported metric types:
- Counter: Monotonically increasing values (e.g., total requests)
- Histogram: Distribution of values with configurable buckets (e.g., latency)

Example:
    >>> from asap.observability.metrics import MetricsCollector, get_metrics
    >>> collector = MetricsCollector()
    >>> collector.increment_counter("asap_requests_total", {"payload_type": "task.request"})
    >>> collector.observe_histogram("asap_request_duration_seconds", 0.125, {"status": "success"})
    >>> print(collector.export_prometheus())
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class Counter:
    """A monotonically increasing counter metric.

    Attributes:
        name: Metric name
        help_text: Human-readable description
        values: Dictionary mapping label combinations to counts
    """

    name: str
    help_text: str
    values: dict[tuple[tuple[str, str], ...], float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def increment(self, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self.values[label_key] = self.values.get(label_key, 0.0) + value

    def get(self, labels: dict[str, str] | None = None) -> float:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            return self.values.get(label_key, 0.0)


# Default histogram buckets for latency (in seconds)
DEFAULT_LATENCY_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)


@dataclass
class Histogram:
    """A histogram metric for measuring distributions.

    Attributes:
        name: Metric name
        help_text: Human-readable description
        buckets: Upper bounds for histogram buckets
        values: Dictionary mapping label combinations to bucket counts and sum
    """

    name: str
    help_text: str
    buckets: tuple[float, ...] = DEFAULT_LATENCY_BUCKETS
    # values[label_key] = {"buckets": {bound: count}, "sum": total, "count": n}
    values: dict[tuple[tuple[str, str], ...], dict[str, float | dict[float, float]]] = field(
        default_factory=dict
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            if label_key not in self.values:
                self.values[label_key] = {
                    "buckets": dict.fromkeys(self.buckets, 0.0),
                    "sum": 0.0,
                    "count": 0.0,
                }

            data = self.values[label_key]
            buckets = data["buckets"]
            if isinstance(buckets, dict):
                for bound in self.buckets:
                    if value <= bound:
                        buckets[bound] += 1.0

            if isinstance(data["sum"], float):
                data["sum"] += value
            if isinstance(data["count"], float):
                data["count"] += 1.0

    def get_count(self, labels: dict[str, str] | None = None) -> float:
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            if label_key not in self.values:
                return 0.0
            count = self.values[label_key].get("count", 0.0)
            return count if isinstance(count, float) else 0.0


class MetricsCollector:
    """Collects and exports metrics in Prometheus format.

    This class provides thread-safe metric collection with support for
    counters and histograms. Metrics are exported in Prometheus text format.

    Example:
        >>> collector = MetricsCollector()
        >>> collector.increment_counter(
        ...     "asap_requests_total",
        ...     {"payload_type": "task.request", "status": "success"}
        ... )
        >>> collector.observe_histogram(
        ...     "asap_request_duration_seconds",
        ...     0.125,
        ...     {"payload_type": "task.request"}
        ... )
        >>> print(collector.export_prometheus())
    """

    # Default metric definitions (20+ for observability)
    DEFAULT_COUNTERS: ClassVar[dict[str, str]] = {
        "asap_requests_total": "Total number of ASAP requests received",
        "asap_requests_success_total": "Total number of successful ASAP requests",
        "asap_requests_error_total": "Total number of failed ASAP requests",
        "asap_thread_pool_exhausted_total": "Total number of thread pool exhaustion events",
        "asap_handler_executions_total": "Total number of handler executions",
        "asap_handler_errors_total": "Total number of handler execution failures",
        "asap_state_transitions_total": "Total number of state machine transitions",
        "asap_transport_send_total": "Total number of transport send attempts",
        "asap_transport_send_errors_total": "Total number of transport send errors",
        "asap_transport_retries_total": "Total number of transport retries",
        "asap_parse_errors_total": "Total number of JSON-RPC parse errors",
        "asap_auth_failures_total": "Total number of authentication failures",
        "asap_validation_errors_total": "Total number of envelope validation errors",
        "asap_invalid_timestamp_total": "Total number of invalid timestamp rejections",
        "asap_invalid_nonce_total": "Total number of invalid nonce rejections",
        "asap_sender_mismatch_total": "Total number of sender identity mismatches",
    }

    DEFAULT_HISTOGRAMS: ClassVar[dict[str, str]] = {
        "asap_request_duration_seconds": "Request processing duration in seconds",
        "asap_handler_duration_seconds": "Handler execution duration in seconds",
        "asap_transport_send_duration_seconds": "Transport send duration in seconds",
    }

    def __init__(self) -> None:
        """Initialize the metrics collector with default metrics."""
        self._lock = threading.Lock()
        self._counters: dict[str, Counter] = {}
        self._histograms: dict[str, Histogram] = {}
        self._start_time = time.time()

        # Initialize default metrics
        for name, help_text in self.DEFAULT_COUNTERS.items():
            self._counters[name] = Counter(name=name, help_text=help_text)

        for name, help_text in self.DEFAULT_HISTOGRAMS.items():
            self._histograms[name] = Histogram(name=name, help_text=help_text)

    def register_counter(self, name: str, help_text: str) -> None:
        """Register a new counter metric.

        Args:
            name: Metric name (should follow Prometheus naming conventions)
            help_text: Human-readable description
        """
        with self._lock:
            if name not in self._counters:
                self._counters[name] = Counter(name=name, help_text=help_text)

    def register_histogram(
        self, name: str, help_text: str, buckets: tuple[float, ...] = DEFAULT_LATENCY_BUCKETS
    ) -> None:
        """Register a new histogram metric.

        Args:
            name: Metric name (should follow Prometheus naming conventions)
            help_text: Human-readable description
            buckets: Upper bounds for histogram buckets
        """
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = Histogram(name=name, help_text=help_text, buckets=buckets)

    def increment_counter(
        self, name: str, labels: dict[str, str] | None = None, value: float = 1.0
    ) -> None:
        with self._lock:
            if name in self._counters:
                self._counters[name].increment(labels, value)

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str] | None = None
    ) -> None:
        with self._lock:
            if name in self._histograms:
                self._histograms[name].observe(value, labels)

    def get_counter(self, name: str, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            if name in self._counters:
                return self._counters[name].get(labels)
            return 0.0

    def get_histogram_count(self, name: str, labels: dict[str, str] | None = None) -> float:
        with self._lock:
            if name in self._histograms:
                return self._histograms[name].get_count(labels)
            return 0.0

    def _format_labels(self, labels: tuple[tuple[str, str], ...]) -> str:
        if not labels:
            return ""

        def escape_label_value(value: str) -> str:
            """Escape label value per Prometheus specification."""
            # Escape backslashes first (to avoid double-escaping)
            value = value.replace("\\", "\\\\")
            # Escape double quotes
            return value.replace('"', '\\"')

        parts = [f'{k}="{escape_label_value(v)}"' for k, v in labels]
        return "{" + ",".join(parts) + "}"

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text format.

        Returns:
            Metrics in Prometheus exposition format

        Example:
            >>> collector = MetricsCollector()
            >>> collector.increment_counter("asap_requests_total", {"status": "success"})
            >>> output = collector.export_prometheus()
            >>> "asap_requests_total" in output
            True
        """
        lines: list[str] = []

        with self._lock:
            # Export counters
            for counter in self._counters.values():
                lines.append(f"# HELP {counter.name} {counter.help_text}")
                lines.append(f"# TYPE {counter.name} counter")
                if not counter.values:
                    # Export zero value if no data
                    lines.append(f"{counter.name} 0")
                else:
                    for label_key, value in counter.values.items():
                        label_str = self._format_labels(label_key)
                        lines.append(f"{counter.name}{label_str} {value}")

            # Export histograms
            for histogram in self._histograms.values():
                lines.append(f"# HELP {histogram.name} {histogram.help_text}")
                lines.append(f"# TYPE {histogram.name} histogram")
                if not histogram.values:
                    # Export zero values if no data
                    for bound in histogram.buckets:
                        lines.append(f'{histogram.name}_bucket{{le="{bound}"}} 0')
                    lines.append(f'{histogram.name}_bucket{{le="+Inf"}} 0')
                    lines.append(f"{histogram.name}_sum 0")
                    lines.append(f"{histogram.name}_count 0")
                else:
                    for label_key, data in histogram.values.items():
                        base_labels = self._format_labels(label_key)

                        # Bucket values
                        buckets = data["buckets"]
                        cumulative = 0.0
                        if isinstance(buckets, dict):
                            for bound in histogram.buckets:
                                cumulative += buckets.get(bound, 0.0)
                                if base_labels:
                                    # Insert le before closing brace
                                    label_str = base_labels[:-1] + f',le="{bound}"' + "}"
                                else:
                                    label_str = f'{{le="{bound}"}}'
                                lines.append(f"{histogram.name}_bucket{label_str} {cumulative}")

                        # +Inf bucket (total count)
                        count = data.get("count", 0.0)
                        if base_labels:
                            label_str = base_labels[:-1] + ',le="+Inf"}'
                        else:
                            label_str = '{le="+Inf"}'
                        lines.append(f"{histogram.name}_bucket{label_str} {count}")

                        # Sum and count
                        sum_val = data.get("sum", 0.0)
                        lines.append(f"{histogram.name}_sum{base_labels} {sum_val}")
                        lines.append(f"{histogram.name}_count{base_labels} {count}")

            # Add process uptime
            uptime = time.time() - self._start_time
            lines.append("# HELP asap_process_uptime_seconds Time since server start")
            lines.append("# TYPE asap_process_uptime_seconds gauge")
            lines.append(f"asap_process_uptime_seconds {uptime:.3f}")

        return "\n".join(lines) + "\n"

    def reset(self) -> None:
        """Reset all metrics to zero. Useful for testing."""
        with self._lock:
            for counter in self._counters.values():
                counter.values.clear()
            for histogram in self._histograms.values():
                histogram.values.clear()


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None
_collector_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        The global MetricsCollector singleton

    Example:
        >>> metrics = get_metrics()
        >>> metrics.increment_counter("asap_requests_total")
    """
    global _metrics_collector
    with _collector_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector. Useful for testing."""
    global _metrics_collector
    with _collector_lock:
        if _metrics_collector is not None:
            _metrics_collector.reset()
