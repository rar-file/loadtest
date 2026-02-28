"""Metrics collection module.

This module provides the MetricsCollector class for gathering and
analyzing performance metrics during load tests.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricSnapshot:
    """Snapshot of metrics at a point in time.

    Attributes:
        timestamp: When the snapshot was taken.
        response_times: List of response times since last snapshot.
        request_count: Number of requests.
        success_count: Number of successful requests.
        error_count: Number of failed requests.
        status_codes: Distribution of HTTP status codes.
    """

    timestamp: float
    response_times: list[float] = field(default_factory=list)
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    status_codes: dict[int, int] = field(default_factory=dict)


class MetricsCollector:
    """Collector for load test metrics.

    This class collects and aggregates metrics during a load test,
    including response times, throughput, error rates, and status
    code distributions. It is thread-safe for concurrent updates.

    Attributes:
        response_times: List of all response times.
        total_requests: Total number of requests made.
        successful_requests: Number of successful requests.
        failed_requests: Number of failed requests.
        status_codes: Count of each HTTP status code.
        errors: Count of each error type.
        start_time: When collection started.

    Example:
        >>> metrics = MetricsCollector()
        >>> metrics.record_response_time(0.123)
        >>> metrics.record_success()
        >>> stats = metrics.get_statistics()
    """

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._lock = threading.Lock()

        self.response_times: list[float] = []
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.failed_requests: int = 0
        self.status_codes: dict[int, int] = defaultdict(int)
        self.errors: dict[str, int] = defaultdict(int)
        self.start_time: float = time.time()
        self._custom_metrics: dict[str, list[float]] = defaultdict(list)

    def record_response_time(self, elapsed: float) -> None:
        """Record a response time measurement.

        Args:
            elapsed: Response time in seconds.
        """
        with self._lock:
            self.response_times.append(elapsed)

    def record_success(self) -> None:
        """Record a successful request."""
        with self._lock:
            self.total_requests += 1
            self.successful_requests += 1

    def record_failure(self, error: str | None = None) -> None:
        """Record a failed request.

        Args:
            error: Optional error message or type.
        """
        with self._lock:
            self.total_requests += 1
            self.failed_requests += 1
            if error:
                error_type = error.split(":")[0] if ":" in error else error
                self.errors[error_type] += 1

    def record_status_code(self, code: int) -> None:
        """Record an HTTP status code.

        Args:
            code: HTTP status code.
        """
        with self._lock:
            self.status_codes[code] += 1

    def record(self, metric_name: str, value: float) -> None:
        """Record a custom metric value.

        Args:
            metric_name: Name of the custom metric.
            value: Metric value to record.
        """
        with self._lock:
            self._custom_metrics[metric_name].append(value)

    def get_statistics(self) -> dict[str, Any]:
        """Calculate and return statistics for all collected metrics.

        Returns:
            Dictionary containing various statistics:
            - total_requests: Total number of requests
            - successful_requests: Number of successful requests
            - failed_requests: Number of failed requests
            - success_rate: Percentage of successful requests
            - error_rate: Percentage of failed requests
            - duration: Total time period of data collection
            - throughput: Requests per second
            - min_response_time: Minimum response time
            - max_response_time: Maximum response time
            - mean_response_time: Average response time
            - median_response_time: Median response time
            - p50, p95, p99, p999: Response time percentiles
            - status_codes: Distribution of status codes
            - errors: Distribution of error types
        """
        with self._lock:
            stats = {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "success_rate": 0.0,
                "error_rate": 0.0,
                "duration": time.time() - self.start_time,
                "throughput": 0.0,
                "min_response_time": 0.0,
                "max_response_time": 0.0,
                "mean_response_time": 0.0,
                "median_response_time": 0.0,
                "p50_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0,
                "p999_response_time": 0.0,
                "status_codes": dict(self.status_codes),
                "errors": dict(self.errors),
                "custom_metrics": {},
            }

            # Calculate success/error rates
            if self.total_requests > 0:
                stats["success_rate"] = (self.successful_requests / self.total_requests) * 100
                stats["error_rate"] = (self.failed_requests / self.total_requests) * 100

            # Calculate throughput
            if stats["duration"] > 0:
                stats["throughput"] = self.total_requests / stats["duration"]

            # Calculate response time statistics
            if self.response_times:
                sorted_times = sorted(self.response_times)
                n = len(sorted_times)

                stats["min_response_time"] = sorted_times[0]
                stats["max_response_time"] = sorted_times[-1]
                stats["mean_response_time"] = sum(sorted_times) / n
                stats["median_response_time"] = self._percentile(sorted_times, 50)
                stats["p50_response_time"] = self._percentile(sorted_times, 50)
                stats["p95_response_time"] = self._percentile(sorted_times, 95)
                stats["p99_response_time"] = self._percentile(sorted_times, 99)
                stats["p999_response_time"] = self._percentile(sorted_times, 99.9)

            # Custom metrics
            for name, values in self._custom_metrics.items():
                if values:
                    sorted_values = sorted(values)
                    stats["custom_metrics"][name] = {
                        "count": len(values),
                        "min": sorted_values[0],
                        "max": sorted_values[-1],
                        "mean": sum(sorted_values) / len(values),
                        "median": self._percentile(sorted_values, 50),
                        "p95": self._percentile(sorted_values, 95),
                        "p99": self._percentile(sorted_values, 99),
                    }

            return stats

    def _percentile(self, sorted_data: list[float], p: float) -> float:
        """Calculate the percentile of sorted data.

        Args:
            sorted_data: Sorted list of values.
            p: Percentile to calculate (0-100).

        Returns:
            The percentile value.
        """
        if not sorted_data:
            return 0.0

        k = (len(sorted_data) - 1) * (p / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f

        if f == c:
            return sorted_data[f]

        return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)

    def get_snapshot(self) -> MetricSnapshot:
        """Get a snapshot of current metrics and reset counters.

        Returns:
            MetricSnapshot with current values.
        """
        with self._lock:
            snapshot = MetricSnapshot(
                timestamp=time.time(),
                response_times=self.response_times.copy(),
                request_count=self.total_requests,
                success_count=self.successful_requests,
                error_count=self.failed_requests,
                status_codes=dict(self.status_codes),
            )

            # Reset for next snapshot
            self.response_times = []

            return snapshot

    def reset(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self.response_times = []
            self.total_requests = 0
            self.successful_requests = 0
            self.failed_requests = 0
            self.status_codes = defaultdict(int)
            self.errors = defaultdict(int)
            self.start_time = time.time()
            self._custom_metrics = defaultdict(list)

    def merge(self, other: MetricsCollector) -> None:
        """Merge another collector's metrics into this one.

        Args:
            other: Another MetricsCollector instance.
        """
        with self._lock:
            other_stats = other.get_statistics()

            self.response_times.extend(other.response_times)
            self.total_requests += other_stats["total_requests"]
            self.successful_requests += other_stats["successful_requests"]
            self.failed_requests += other_stats["failed_requests"]

            for code, count in other_stats["status_codes"].items():
                self.status_codes[code] += count

            for error, count in other_stats["errors"].items():
                self.errors[error] += count
