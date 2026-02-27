"""Core load test orchestrator module.

This module provides the main LoadTest class for orchestrating load tests,
including scenario management, traffic pattern application, and result collection.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from loadtest.metrics.collector import MetricsCollector
from loadtest.runner import TestRunner

if TYPE_CHECKING:
    from loadtest.generators.constant import ConstantRateGenerator
    from loadtest.scenarios.base import Scenario


@dataclass
class LoadTestConfig:
    """Configuration for a load test.
    
    Attributes:
        name: Name of the load test.
        duration: Duration of the test in seconds.
        warmup_duration: Warmup period before recording metrics (seconds).
        max_concurrent: Maximum number of concurrent executions.
        console_output: Whether to display real-time console output.
    """
    
    name: str = "Load Test"
    duration: float = 60.0
    warmup_duration: float = 5.0
    max_concurrent: int = 1000
    console_output: bool = True


@dataclass
class TestResult:
    """Results from a load test execution.
    
    Attributes:
        config: The test configuration used.
        metrics: Collected metrics from the test.
        start_time: Timestamp when the test started.
        end_time: Timestamp when the test ended.
        total_requests: Total number of requests made.
        successful_requests: Number of successful requests.
        failed_requests: Number of failed requests.
    """
    
    config: LoadTestConfig
    metrics: MetricsCollector
    start_time: float = 0.0
    end_time: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    @property
    def duration(self) -> float:
        """Calculate the total test duration."""
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100


class LoadTest:
    """Main orchestrator for load testing.
    
    This class manages scenarios, traffic patterns, and executes load tests
    with configurable parameters.
    
    Example:
        >>> test = LoadTest(name="API Test", duration=60)
        >>> test.add_scenario(HTTPScenario(...))
        >>> test.set_pattern(ConstantRateGenerator(rate=10))
        >>> results = await test.run()
    
    Attributes:
        config: The test configuration.
        scenarios: List of scenarios with their weights.
        pattern: The traffic pattern generator.
        metrics: The metrics collector instance.
    """
    
    def __init__(
        self,
        name: str = "Load Test",
        duration: float = 60.0,
        warmup_duration: float = 5.0,
        max_concurrent: int = 1000,
        console_output: bool = True,
    ) -> None:
        """Initialize a new LoadTest instance.
        
        Args:
            name: Name of the load test.
            duration: Duration of the test in seconds.
            warmup_duration: Warmup period before recording metrics.
            max_concurrent: Maximum number of concurrent executions.
            console_output: Whether to display real-time console output.
        """
        self.config = LoadTestConfig(
            name=name,
            duration=duration,
            warmup_duration=warmup_duration,
            max_concurrent=max_concurrent,
            console_output=console_output,
        )
        self.scenarios: list[tuple[Scenario, int]] = []
        self.pattern: ConstantRateGenerator | None = None
        self.metrics = MetricsCollector()
        self._runner: TestRunner | None = None
        self._stop_event = asyncio.Event()
    
    def add_scenario(self, scenario: Scenario, weight: int = 1) -> LoadTest:
        """Add a scenario to the load test.
        
        Args:
            scenario: The scenario to add.
            weight: The weight of this scenario relative to others.
                   Higher weights mean the scenario runs more frequently.
        
        Returns:
            Self for method chaining.
            
        Example:
            >>> test.add_scenario(scenario1, weight=2)
            ...       .add_scenario(scenario2, weight=1)
        """
        self.scenarios.append((scenario, weight))
        return self
    
    def set_pattern(self, pattern: ConstantRateGenerator) -> LoadTest:
        """Set the traffic pattern for the load test.
        
        Args:
            pattern: The traffic pattern generator to use.
        
        Returns:
            Self for method chaining.
            
        Example:
            >>> test.set_pattern(ConstantRateGenerator(rate=10))
        """
        self.pattern = pattern
        return self
    
    async def run(self) -> TestResult:
        """Execute the load test.
        
        This method runs all scenarios according to the configured traffic
        pattern and collects metrics throughout the test.
        
        Returns:
            TestResult containing all metrics and test information.
            
        Raises:
            RuntimeError: If no scenarios or no pattern is configured.
        """
        if not self.scenarios:
            raise RuntimeError("No scenarios added to the test")
        if self.pattern is None:
            raise RuntimeError("No traffic pattern set")
        
        result = TestResult(
            config=self.config,
            metrics=self.metrics,
        )
        
        self._stop_event.clear()
        self._runner = TestRunner(
            scenarios=self.scenarios,
            pattern=self.pattern,
            metrics=self.metrics,
            max_concurrent=self.config.max_concurrent,
            console_output=self.config.console_output,
        )
        
        result.start_time = time.time()
        
        try:
            # Warmup phase
            if self.config.warmup_duration > 0:
                await self._run_warmup()
            
            # Main test phase
            await self._run_test(result)
            
        except asyncio.CancelledError:
            pass
        finally:
            result.end_time = time.time()
            if self._runner:
                await self._runner.cleanup()
        
        return result
    
    async def _run_warmup(self) -> None:
        """Run the warmup phase before recording metrics."""
        if self._runner is None or self.pattern is None:
            return
        
        if self.config.console_output:
            print(f"Warming up for {self.config.warmup_duration}s...")
        
        warmup_metrics = MetricsCollector()
        warmup_runner = TestRunner(
            scenarios=self.scenarios,
            pattern=self.pattern,
            metrics=warmup_metrics,
            max_concurrent=self.config.max_concurrent,
            console_output=False,
        )
        
        try:
            await asyncio.wait_for(
                warmup_runner.run(),
                timeout=self.config.warmup_duration,
            )
        except asyncio.TimeoutError:
            pass
        finally:
            await warmup_runner.cleanup()
    
    async def _run_test(self, result: TestResult) -> None:
        """Run the main test phase.
        
        Args:
            result: The TestResult to update with metrics.
        """
        if self._runner is None:
            return
        
        if self.config.console_output:
            print(f"Running test '{self.config.name}' for {self.config.duration}s...")
        
        try:
            await asyncio.wait_for(
                self._runner.run(),
                timeout=self.config.duration,
            )
        except asyncio.TimeoutError:
            pass
        
        # Update result with final metrics
        stats = self.metrics.get_statistics()
        result.total_requests = stats.get("total_requests", 0)
        result.successful_requests = stats.get("successful_requests", 0)
        result.failed_requests = stats.get("failed_requests", 0)
    
    def stop(self) -> None:
        """Signal the load test to stop gracefully."""
        self._stop_event.set()
        if self._runner:
            self._runner.stop()
    
    def report(
        self,
        format: str = "html",  # noqa: A002
        output: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Generate a report from the test results.
        
        Args:
            format: The report format ("html", "json", "console").
            output: Output file path (optional).
            **kwargs: Additional arguments for the report generator.
        
        Returns:
            The generated report as a string.
            
        Example:
            >>> test.report(format="html", output="report.html")
        """
        if format == "html":
            from loadtest.reports.html import HTMLReportGenerator
            generator = HTMLReportGenerator(**kwargs)
        elif format == "console":
            return self._generate_console_report()
        else:
            raise ValueError(f"Unknown report format: {format}")
        
        return generator.generate(self.metrics, output=output)
    
    def _generate_console_report(self) -> str:
        """Generate a console-friendly report.
        
        Returns:
            Formatted report string.
        """
        stats = self.metrics.get_statistics()
        lines = [
            "=" * 60,
            f"Load Test Report: {self.config.name}",
            "=" * 60,
            f"Duration: {stats.get('duration', 0):.2f}s",
            f"Total Requests: {stats.get('total_requests', 0)}",
            f"Successful: {stats.get('successful_requests', 0)}",
            f"Failed: {stats.get('failed_requests', 0)}",
            f"Success Rate: {stats.get('success_rate', 0):.2f}%",
            "",
            "Response Times:",
            f"  Min: {stats.get('min_response_time', 0):.3f}s",
            f"  Max: {stats.get('max_response_time', 0):.3f}s",
            f"  Mean: {stats.get('mean_response_time', 0):.3f}s",
            f"  Median: {stats.get('median_response_time', 0):.3f}s",
            f"  P95: {stats.get('p95_response_time', 0):.3f}s",
            f"  P99: {stats.get('p99_response_time', 0):.3f}s",
            "=" * 60,
        ]
        return "\n".join(lines)
