"""Prometheus metrics export module.

This module provides Prometheus-compatible metrics export for load test data,
supporting both Prometheus scraping and Pushgateway integration.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any


class PrometheusMetric:
    """Base class for Prometheus metrics.

    Handles proper formatting of metric names, labels, and values
    according to Prometheus conventions.
    """

    def __init__(
        self,
        name: str,
        description: str,
        metric_type: str,
        labels: dict[str, str] | None = None,
    ):
        """Initialize a Prometheus metric.

        Args:
            name: Metric name (will be sanitized).
            description: Help text for the metric.
            metric_type: Prometheus type (counter, gauge, histogram, summary).
            labels: Static labels for this metric.
        """
        self.name = self._sanitize_name(name)
        self.description = description
        self.metric_type = metric_type
        self.labels = labels or {}
        self._values: dict[frozenset, float] = {}

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Sanitize metric name for Prometheus.

        Replaces invalid characters with underscores.
        """
        sanitized = []
        for i, char in enumerate(name):
            if char.isalnum() or char == "_" or char == ":":
                sanitized.append(char)
            else:
                sanitized.append("_")

        # Ensure starts with letter or underscore
        result = "".join(sanitized)
        if result and result[0].isdigit():
            result = "_" + result

        return result

    @staticmethod
    def _escape_label_value(value: str) -> str:
        """Escape label value for Prometheus text format."""
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def _format_labels(self, labels: dict[str, str] | None) -> str:
        """Format labels for Prometheus text format."""
        all_labels = {**self.labels, **(labels or {})}
        if not all_labels:
            return ""

        pairs = [f'{k}="{self._escape_label_value(str(v))}"' for k, v in sorted(all_labels.items())]
        return "{" + ",".join(pairs) + "}"

    def render(self) -> str:
        """Render this metric in Prometheus text format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} {self.metric_type}")

        for label_set, value in self._values.items():
            labels = dict(label_set) if label_set else None
            lines.append(f"{self.name}{self._format_labels(labels)} {value}")

        return "\n".join(lines)


class Counter(PrometheusMetric):
    """Prometheus counter metric.

    A counter is a cumulative metric that only increases.

    Example:
        >>> counter = Counter("requests_total", "Total requests")
        >>> counter.inc()
        >>> counter.inc({"status": "200"})
        >>> print(counter.render())
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
    ):
        super().__init__(name, description, "counter", labels)

    def inc(self, labels: dict[str, str] | None = None, value: float = 1) -> None:
        """Increment the counter.

        Args:
            labels: Label values for this increment.
            value: Amount to increment by.
        """
        label_key = frozenset((labels or {}).items())
        self._values[label_key] = self._values.get(label_key, 0) + value

    def set(self, labels: dict[str, str] | None = None, value: float = 0) -> None:
        """Set counter value (use with caution, counters should only increase).

        Args:
            labels: Label values.
            value: Value to set.
        """
        label_key = frozenset((labels or {}).items())
        self._values[label_key] = value


class Gauge(PrometheusMetric):
    """Prometheus gauge metric.

    A gauge can go up and down.

    Example:
        >>> gauge = Gauge("active_sessions", "Number of active sessions")
        >>> gauge.set(10)
        >>> gauge.inc()
        >>> gauge.dec()
    """

    def __init__(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
    ):
        super().__init__(name, description, "gauge", labels)

    def set(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Set gauge value.

        Args:
            value: Value to set.
            labels: Label values.
        """
        label_key = frozenset((labels or {}).items())
        self._values[label_key] = value

    def inc(self, labels: dict[str, str] | None = None, value: float = 1) -> None:
        """Increment gauge.

        Args:
            labels: Label values.
            value: Amount to increment by.
        """
        label_key = frozenset((labels or {}).items())
        self._values[label_key] = self._values.get(label_key, 0) + value

    def dec(self, labels: dict[str, str] | None = None, value: float = 1) -> None:
        """Decrement gauge.

        Args:
            labels: Label values.
            value: Amount to decrement by.
        """
        self.inc(labels, -value)


class Histogram(PrometheusMetric):
    """Prometheus histogram metric.

    Samples observations and counts them in buckets.

    Example:
        >>> hist = Histogram("response_time", "Response time", buckets=[0.1, 0.5, 1.0, 5.0])
        >>> hist.observe(0.3)
        >>> hist.observe(0.8)
    """

    DEFAULT_BUCKETS = [
        0.005,
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1.0,
        2.5,
        5.0,
        7.5,
        10.0,
        float("inf"),
    ]

    def __init__(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
        buckets: list[float] | None = None,
    ):
        super().__init__(name, description, "histogram", labels)
        self.buckets = sorted(buckets or self.DEFAULT_BUCKETS)
        if self.buckets[-1] != float("inf"):
            self.buckets.append(float("inf"))

        # Store bucket counts and sum per label set
        self._bucket_counts: dict[frozenset, list[int]] = {}
        self._sums: dict[frozenset, float] = {}
        self._counts: dict[frozenset, int] = {}

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value.

        Args:
            value: Value to observe.
            labels: Label values.
        """
        label_key = frozenset((labels or {}).items())

        if label_key not in self._bucket_counts:
            self._bucket_counts[label_key] = [0] * len(self.buckets)
            self._sums[label_key] = 0
            self._counts[label_key] = 0

        # Update bucket counts
        for i, bucket in enumerate(self.buckets):
            if value <= bucket:
                self._bucket_counts[label_key][i] += 1

        self._sums[label_key] += value
        self._counts[label_key] += 1

    def render(self) -> str:
        """Render histogram in Prometheus format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} histogram")

        for label_key in self._bucket_counts:
            labels = dict(label_key) if label_key else {}

            # Render bucket counts
            for i, bucket in enumerate(self.buckets):
                bucket_labels = {**labels, "le": str(bucket) if bucket != float("inf") else "+Inf"}
                value = self._bucket_counts[label_key][i]
                label_str = self._format_labels(bucket_labels)
                lines.append(f"{self.name}_bucket{label_str} {value}")

            # Render sum
            sum_labels = self._format_labels(labels)
            lines.append(f"{self.name}_sum{sum_labels} {self._sums[label_key]}")

            # Render count
            lines.append(f"{self.name}_count{sum_labels} {self._counts[label_key]}")

        return "\n".join(lines)


class Summary(PrometheusMetric):
    """Prometheus summary metric.

    Similar to histogram but calculates quantiles over a sliding time window.

    Example:
        >>> summary = Summary("response_time", "Response time", quantiles=[0.5, 0.95, 0.99])
        >>> summary.observe(0.1)
        >>> summary.observe(0.2)
    """

    DEFAULT_QUANTILES = [0.5, 0.9, 0.95, 0.99]

    def __init__(
        self,
        name: str,
        description: str,
        labels: dict[str, str] | None = None,
        quantiles: list[float] | None = None,
        max_age: float = 600,  # 10 minutes
        age_buckets: int = 5,
    ):
        super().__init__(name, description, "summary", labels)
        self.quantiles = quantiles or self.DEFAULT_QUANTILES
        self.max_age = max_age
        self.age_buckets = age_buckets

        # Store observations with timestamps
        self._observations: dict[frozenset, list[tuple[float, float]]] = {}

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        """Observe a value.

        Args:
            value: Value to observe.
            labels: Label values.
        """
        label_key = frozenset((labels or {}).items())
        now = time.time()

        if label_key not in self._observations:
            self._observations[label_key] = []

        self._observations[label_key].append((now, value))

        # Clean up old observations
        cutoff = now - self.max_age
        self._observations[label_key] = [
            (t, v) for t, v in self._observations[label_key] if t > cutoff
        ]

    def _calculate_quantile(self, values: list[float], q: float) -> float:
        """Calculate quantile from sorted values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        # Use linear interpolation
        idx = q * (n - 1)
        lower = int(idx)
        upper = min(lower + 1, n - 1)
        frac = idx - lower

        return sorted_values[lower] * (1 - frac) + sorted_values[upper] * frac

    def render(self) -> str:
        """Render summary in Prometheus format."""
        lines = [f"# HELP {self.name} {self.description}"]
        lines.append(f"# TYPE {self.name} summary")

        for label_key, observations in self._observations.items():
            labels = dict(label_key) if label_key else {}
            values = [v for _, v in observations]

            # Render quantiles
            for q in self.quantiles:
                quantile_labels = {**labels, "quantile": str(q)}
                quantile_value = self._calculate_quantile(values, q)
                label_str = self._format_labels(quantile_labels)
                lines.append(f"{self.name}{label_str} {quantile_value}")

            # Render sum
            sum_value = sum(values)
            sum_labels = self._format_labels(labels)
            lines.append(f"{self.name}_sum{sum_labels} {sum_value}")

            # Render count
            count_value = len(values)
            lines.append(f"{self.name}_count{sum_labels} {count_value}")

        return "\n".join(lines)


@dataclass
class PrometheusExporterConfig:
    """Configuration for Prometheus exporter.

    Attributes:
        job_name: Job name for metrics.
        instance: Instance identifier.
        namespace: Optional namespace prefix for metrics.
        subsystem: Optional subsystem prefix for metrics.
        include_timestamp: Whether to include timestamps in metrics.
    """

    job_name: str = "loadtest"
    instance: str = "localhost"
    namespace: str = ""
    subsystem: str = ""
    include_timestamp: bool = False


class PrometheusExporter:
    """Prometheus metrics exporter for load tests.

    Collects metrics during load tests and exports them in Prometheus format.
    Supports both pull (HTTP endpoint) and push (Pushgateway) modes.

    Example:
        >>> exporter = PrometheusExporter()
        >>> exporter.start_collection(metrics_collector)
        >>> # Run load test...
        >>> metrics_text = exporter.render()
        >>>
        >>> # Or start HTTP server for Prometheus to scrape
        >>> await exporter.start_http_server(port=9090)
    """

    def __init__(self, config: PrometheusExporterConfig | None = None):
        """Initialize the Prometheus exporter.

        Args:
            config: Exporter configuration.
        """
        self.config = config or PrometheusExporterConfig()
        self._metrics: dict[str, PrometheusMetric] = {}
        self._collection_task: asyncio.Task | None = None
        self._running = False
        self._metrics_collector: Any = None

        # Initialize standard metrics
        self._init_standard_metrics()

    def _metric_name(self, name: str) -> str:
        """Build full metric name with namespace/subsystem."""
        parts = []
        if self.config.namespace:
            parts.append(self.config.namespace)
        if self.config.subsystem:
            parts.append(self.config.subsystem)
        parts.append(name)
        return "_".join(parts)

    def _init_standard_metrics(self) -> None:
        """Initialize standard load test metrics."""
        base_labels = {
            "job": self.config.job_name,
            "instance": self.config.instance,
        }

        # Request metrics
        self._metrics["requests_total"] = Counter(
            self._metric_name("requests_total"),
            "Total number of requests",
            base_labels.copy(),
        )
        self._metrics["requests_failed_total"] = Counter(
            self._metric_name("requests_failed_total"),
            "Total number of failed requests",
            base_labels.copy(),
        )

        # Response time histogram
        self._metrics["response_time_seconds"] = Histogram(
            self._metric_name("response_time_seconds"),
            "Response time in seconds",
            base_labels.copy(),
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        # Active sessions gauge
        self._metrics["active_sessions"] = Gauge(
            self._metric_name("active_sessions"),
            "Number of currently active sessions",
            base_labels.copy(),
        )

        # Session metrics
        self._metrics["sessions_started_total"] = Counter(
            self._metric_name("sessions_started_total"),
            "Total number of sessions started",
            base_labels.copy(),
        )
        self._metrics["sessions_completed_total"] = Counter(
            self._metric_name("sessions_completed_total"),
            "Total number of sessions completed",
            base_labels.copy(),
        )
        self._metrics["sessions_failed_total"] = Counter(
            self._metric_name("sessions_failed_total"),
            "Total number of sessions failed",
            base_labels.copy(),
        )

        # Step metrics
        self._metrics["steps_total"] = Counter(
            self._metric_name("steps_total"),
            "Total number of steps executed",
            base_labels.copy(),
        )
        self._metrics["step_duration_seconds"] = Histogram(
            self._metric_name("step_duration_seconds"),
            "Step execution duration in seconds",
            base_labels.copy(),
        )

        # Think time metrics
        self._metrics["think_time_seconds"] = Histogram(
            self._metric_name("think_time_seconds"),
            "Think time duration in seconds",
            base_labels.copy(),
        )

        # Error counter
        self._metrics["errors_total"] = Counter(
            self._metric_name("errors_total"),
            "Total number of errors by type",
            base_labels.copy(),
        )

    def record_request(
        self,
        duration: float,
        success: bool,
        status_code: int | None = None,
        scenario: str = "",
    ) -> None:
        """Record a request metric.

        Args:
            duration: Request duration in seconds.
            success: Whether the request succeeded.
            status_code: HTTP status code (if applicable).
            scenario: Scenario name.
        """
        labels = {"scenario": scenario}
        if status_code:
            labels["status"] = str(status_code)

        self._metrics["requests_total"].inc(labels)
        self._metrics["response_time_seconds"].observe(duration, labels)

        if not success:
            self._metrics["requests_failed_total"].inc(labels)

    def record_session_start(self, scenario: str = "") -> None:
        """Record session start.

        Args:
            scenario: Scenario name.
        """
        self._metrics["sessions_started_total"].inc({"scenario": scenario})
        self._metrics["active_sessions"].inc({"scenario": scenario})

    def record_session_complete(self, scenario: str = "") -> None:
        """Record session completion.

        Args:
            scenario: Scenario name.
        """
        self._metrics["sessions_completed_total"].inc({"scenario": scenario})
        self._metrics["active_sessions"].dec({"scenario": scenario})

    def record_session_failed(self, scenario: str = "", error_type: str = "") -> None:
        """Record session failure.

        Args:
            scenario: Scenario name.
            error_type: Type of error.
        """
        self._metrics["sessions_failed_total"].inc({"scenario": scenario})
        self._metrics["active_sessions"].dec({"scenario": scenario})
        if error_type:
            self._metrics["errors_total"].inc({"type": error_type})

    def record_step(
        self,
        step_name: str,
        duration: float,
        success: bool,
        think_time: float = 0,
    ) -> None:
        """Record a step execution.

        Args:
            step_name: Name of the step.
            duration: Step duration in seconds.
            success: Whether the step succeeded.
            think_time: Think time before this step.
        """
        labels = {"step": step_name, "status": "success" if success else "failure"}
        self._metrics["steps_total"].inc(labels)
        self._metrics["step_duration_seconds"].observe(duration, labels)

        if think_time > 0:
            self._metrics["think_time_seconds"].observe(think_time)

    def get_metric(self, name: str) -> PrometheusMetric | None:
        """Get a metric by name.

        Args:
            name: Metric name.

        Returns:
            The metric or None if not found.
        """
        return self._metrics.get(name)

    def add_custom_metric(self, metric: PrometheusMetric) -> None:
        """Add a custom metric.

        Args:
            metric: Custom metric to add.
        """
        self._metrics[metric.name] = metric

    def render(self) -> str:
        """Render all metrics in Prometheus text format.

        Returns:
            Prometheus exposition format string.
        """
        return "\n\n".join(m.render() for m in self._metrics.values())

    async def start_collection(self, metrics_collector: Any, interval: float = 5.0) -> None:
        """Start background metrics collection.

        Args:
            metrics_collector: Source metrics collector to sync from.
            interval: Collection interval in seconds.
        """
        self._metrics_collector = metrics_collector
        self._running = True

        while self._running:
            try:
                self._sync_from_collector()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log but continue on error
                await asyncio.sleep(interval)

    def _sync_from_collector(self) -> None:
        """Sync metrics from the collector."""
        if not self._metrics_collector:
            return

        try:
            stats = self._metrics_collector.get_statistics()

            # Update counters from stats
            total = stats.get("total_requests", 0)
            failed = stats.get("failed_requests", 0)

            # These would need to be cumulative, so we'd need to track deltas
            # For now, we just set them directly
            self._metrics["requests_total"].set({}, total)
            self._metrics["requests_failed_total"].set({}, failed)

        except Exception:
            pass

    def stop_collection(self) -> None:
        """Stop background metrics collection."""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()

    async def start_http_server(self, port: int = 9090, host: str = "0.0.0.0") -> None:
        """Start an HTTP server for Prometheus to scrape.

        Args:
            port: Port to listen on.
            host: Host to bind to.
        """
        from aiohttp import web

        async def metrics_handler(request: web.Request) -> web.Response:
            return web.Response(
                text=self.render(),
                content_type="text/plain; version=0.0.4; charset=utf-8",
            )

        app = web.Application()
        app.router.add_get("/metrics", metrics_handler)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        print(f"Prometheus metrics server started on {host}:{port}/metrics")

        # Keep running
        while True:
            await asyncio.sleep(3600)

    async def push_to_gateway(
        self,
        gateway_url: str,
        job: str | None = None,
        grouping_key: dict[str, str] | None = None,
    ) -> None:
        """Push metrics to a Prometheus Pushgateway.

        Args:
            gateway_url: URL of the Pushgateway.
            job: Job name (defaults to config job_name).
            grouping_key: Optional grouping key.
        """
        import aiohttp

        job = job or self.config.job_name
        url = f"{gateway_url}/metrics/job/{job}"

        if grouping_key:
            for key, value in grouping_key.items():
                url = f"{url}/{key}/{value}"

        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url,
                data=self.render(),
                headers={"Content-Type": "text/plain"},
            ) as response,
        ):
            if response.status not in (200, 202):
                raise RuntimeError(f"Pushgateway returned {response.status}")
