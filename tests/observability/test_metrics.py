"""Tests for ASAP observability metrics module."""

import threading
import time

import pytest

from asap.observability.metrics import (
    Counter,
    Histogram,
    MetricsCollector,
    get_metrics,
    reset_metrics,
)


class TestCounter:
    """Tests for Counter metric."""

    def test_counter_increment_default(self) -> None:
        """Test counter increments by 1 by default."""
        counter = Counter(name="test_counter", help_text="Test counter")
        counter.increment()
        assert counter.get() == 1.0

    def test_counter_increment_custom_value(self) -> None:
        """Test counter increments by custom value."""
        counter = Counter(name="test_counter", help_text="Test counter")
        counter.increment(value=5.0)
        assert counter.get() == 5.0

    def test_counter_increment_with_labels(self) -> None:
        """Test counter with labels."""
        counter = Counter(name="test_counter", help_text="Test counter")
        counter.increment(labels={"status": "success"})
        counter.increment(labels={"status": "error"})
        counter.increment(labels={"status": "success"})

        assert counter.get(labels={"status": "success"}) == 2.0
        assert counter.get(labels={"status": "error"}) == 1.0
        assert counter.get(labels={"status": "unknown"}) == 0.0

    def test_counter_get_nonexistent_returns_zero(self) -> None:
        """Test get returns 0 for nonexistent labels."""
        counter = Counter(name="test_counter", help_text="Test counter")
        assert counter.get(labels={"status": "nonexistent"}) == 0.0


class TestHistogram:
    """Tests for Histogram metric."""

    def test_histogram_observe(self) -> None:
        """Test histogram records observations."""
        histogram = Histogram(
            name="test_histogram",
            help_text="Test histogram",
            buckets=(0.1, 0.5, 1.0),
        )
        histogram.observe(0.25)
        histogram.observe(0.75)

        assert histogram.get_count() == 2.0

    def test_histogram_observe_with_labels(self) -> None:
        """Test histogram with labels."""
        histogram = Histogram(
            name="test_histogram",
            help_text="Test histogram",
            buckets=(0.1, 0.5, 1.0),
        )
        histogram.observe(0.25, labels={"method": "GET"})
        histogram.observe(0.75, labels={"method": "POST"})
        histogram.observe(0.15, labels={"method": "GET"})

        assert histogram.get_count(labels={"method": "GET"}) == 2.0
        assert histogram.get_count(labels={"method": "POST"}) == 1.0

    def test_histogram_bucket_distribution(self) -> None:
        """Test histogram correctly distributes values into buckets."""
        histogram = Histogram(
            name="test_histogram",
            help_text="Test histogram",
            buckets=(0.1, 0.5, 1.0),
        )
        histogram.observe(0.05)  # Should be in 0.1 bucket
        histogram.observe(0.25)  # Should be in 0.5 bucket
        histogram.observe(0.75)  # Should be in 1.0 bucket
        histogram.observe(2.0)  # Should exceed all buckets

        # Verify sum and count
        label_key = ()
        assert label_key in histogram.values
        data = histogram.values[label_key]
        assert data["count"] == 4.0
        assert data["sum"] == 3.05


class TestMetricsCollector:
    """Tests for MetricsCollector."""

    def test_collector_has_default_metrics(self) -> None:
        """Test collector initializes with default metrics."""
        collector = MetricsCollector()

        # Check default counters exist
        assert "asap_requests_total" in collector._counters
        assert "asap_requests_success_total" in collector._counters
        assert "asap_requests_error_total" in collector._counters

        # Check default histogram exists
        assert "asap_request_duration_seconds" in collector._histograms

    def test_collector_increment_counter(self) -> None:
        """Test collector increments counters."""
        collector = MetricsCollector()
        collector.increment_counter("asap_requests_total", {"status": "success"})

        assert collector.get_counter("asap_requests_total", {"status": "success"}) == 1.0

    def test_collector_observe_histogram(self) -> None:
        """Test collector records histogram observations."""
        collector = MetricsCollector()
        collector.observe_histogram(
            "asap_request_duration_seconds",
            0.125,
            {"payload_type": "task.request"},
        )

        count = collector.get_histogram_count(
            "asap_request_duration_seconds",
            {"payload_type": "task.request"},
        )
        assert count == 1.0

    def test_collector_register_custom_counter(self) -> None:
        """Test registering custom counters."""
        collector = MetricsCollector()
        collector.register_counter("custom_counter", "Custom counter for testing")
        collector.increment_counter("custom_counter")

        assert collector.get_counter("custom_counter") == 1.0

    def test_collector_register_custom_histogram(self) -> None:
        """Test registering custom histograms."""
        collector = MetricsCollector()
        collector.register_histogram(
            "custom_histogram",
            "Custom histogram for testing",
            buckets=(0.01, 0.1, 1.0),
        )
        collector.observe_histogram("custom_histogram", 0.05)

        assert collector.get_histogram_count("custom_histogram") == 1.0

    def test_collector_export_prometheus_format(self) -> None:
        """Test exporting metrics in Prometheus format."""
        collector = MetricsCollector()
        collector.increment_counter(
            "asap_requests_total",
            {"payload_type": "task.request", "status": "success"},
        )
        collector.observe_histogram(
            "asap_request_duration_seconds",
            0.125,
            {"payload_type": "task.request"},
        )

        output = collector.export_prometheus()

        # Check format
        assert "# HELP asap_requests_total" in output
        assert "# TYPE asap_requests_total counter" in output
        assert 'asap_requests_total{payload_type="task.request",status="success"} 1' in output

        assert "# HELP asap_request_duration_seconds" in output
        assert "# TYPE asap_request_duration_seconds histogram" in output
        assert "asap_request_duration_seconds_bucket" in output
        assert "asap_request_duration_seconds_sum" in output
        assert "asap_request_duration_seconds_count" in output

        # Check uptime gauge
        assert "asap_process_uptime_seconds" in output

    def test_collector_export_empty_metrics(self) -> None:
        """Test exporting when no data recorded."""
        collector = MetricsCollector()
        output = collector.export_prometheus()

        # Should still have metric definitions
        assert "# HELP asap_requests_total" in output
        assert "asap_requests_total 0" in output

    def test_collector_reset(self) -> None:
        """Test resetting collector clears all data."""
        collector = MetricsCollector()
        collector.increment_counter("asap_requests_total", {"status": "success"})
        collector.observe_histogram("asap_request_duration_seconds", 0.1)

        collector.reset()

        assert collector.get_counter("asap_requests_total", {"status": "success"}) == 0.0
        assert collector.get_histogram_count("asap_request_duration_seconds") == 0.0

    def test_collector_thread_safety(self) -> None:
        """Test collector is thread-safe."""
        collector = MetricsCollector()
        num_threads = 10
        increments_per_thread = 100

        def increment_worker() -> None:
            for _ in range(increments_per_thread):
                collector.increment_counter("asap_requests_total", {"status": "success"})

        threads = [threading.Thread(target=increment_worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        expected = num_threads * increments_per_thread
        assert collector.get_counter("asap_requests_total", {"status": "success"}) == expected


class TestGlobalMetrics:
    """Tests for global metrics functions."""

    def test_get_metrics_returns_singleton(self) -> None:
        """Test get_metrics returns the same instance."""
        reset_metrics()
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_reset_metrics_clears_data(self) -> None:
        """Test reset_metrics clears global collector data."""
        metrics = get_metrics()
        metrics.increment_counter("asap_requests_total", {"status": "test"})

        reset_metrics()

        assert metrics.get_counter("asap_requests_total", {"status": "test"}) == 0.0


class TestPrometheusFormat:
    """Tests for Prometheus output format compliance."""

    def test_label_formatting(self) -> None:
        """Test labels are formatted correctly."""
        collector = MetricsCollector()
        collector.increment_counter(
            "asap_requests_total",
            {"method": "POST", "status": "success"},
        )

        output = collector.export_prometheus()

        # Labels should be sorted and quoted
        assert 'method="POST"' in output
        assert 'status="success"' in output

    def test_histogram_bucket_format(self) -> None:
        """Test histogram buckets follow Prometheus format."""
        collector = MetricsCollector()
        collector.observe_histogram("asap_request_duration_seconds", 0.125)

        output = collector.export_prometheus()

        # Check bucket format with le label
        assert 'le="0.005"' in output
        assert 'le="0.01"' in output
        assert 'le="+Inf"' in output

    def test_uptime_is_positive(self) -> None:
        """Test uptime metric shows positive value."""
        collector = MetricsCollector()
        time.sleep(0.01)  # Small delay to ensure positive uptime

        output = collector.export_prometheus()

        # Find uptime line and verify it's positive
        for line in output.split("\n"):
            if line.startswith("asap_process_uptime_seconds"):
                value = float(line.split()[-1])
                assert value > 0
                break
        else:
            pytest.fail("Uptime metric not found")
