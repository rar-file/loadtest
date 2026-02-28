"""Tests for the core loadtest module."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest.core import LoadTest, LoadTestConfig, TestResult
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.base import Scenario


class MockScenario(Scenario):
    """Mock scenario for testing."""

    def __init__(
        self,
        name: str | None = None,
        success: bool = True,
        delay: float = 0.0,
    ) -> None:
        """Initialize mock scenario.

        Args:
            name: Scenario name.
            success: Whether the scenario should succeed.
            delay: Delay in seconds before returning.
        """
        super().__init__(name)
        self.success = success
        self.delay = delay
        self.call_count = 0

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute mock scenario."""
        self.call_count += 1
        if self.delay:
            await asyncio.sleep(self.delay)
        if not self.success:
            raise RuntimeError("Mock failure")
        return {"status": "success", "name": self.name}


class TestLoadTestConfig:
    """Tests for LoadTestConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LoadTestConfig()
        assert config.name == "Load Test"
        assert config.duration == 60.0
        assert config.warmup_duration == 5.0
        assert config.max_concurrent == 1000
        assert config.console_output is True

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = LoadTestConfig(
            name="Custom Test",
            duration=120.0,
            warmup_duration=10.0,
            max_concurrent=500,
            console_output=False,
        )
        assert config.name == "Custom Test"
        assert config.duration == 120.0
        assert config.warmup_duration == 10.0
        assert config.max_concurrent == 500
        assert config.console_output is False


class TestTestResult:
    """Tests for TestResult."""

    def test_duration_calculation(self) -> None:
        """Test duration calculation."""
        from loadtest.metrics.collector import MetricsCollector

        result = TestResult(
            config=LoadTestConfig(),
            metrics=MetricsCollector(),
            start_time=100.0,
            end_time=150.0,
        )
        assert result.duration == 50.0

    def test_success_rate_calculation(self) -> None:
        """Test success rate calculation."""
        from loadtest.metrics.collector import MetricsCollector

        result = TestResult(
            config=LoadTestConfig(),
            metrics=MetricsCollector(),
            total_requests=100,
            successful_requests=95,
            failed_requests=5,
        )
        assert result.success_rate == 95.0

    def test_success_rate_zero_requests(self) -> None:
        """Test success rate with zero requests."""
        from loadtest.metrics.collector import MetricsCollector

        result = TestResult(
            config=LoadTestConfig(),
            metrics=MetricsCollector(),
            total_requests=0,
        )
        assert result.success_rate == 0.0


class TestLoadTest:
    """Tests for LoadTest."""

    def test_init_default(self) -> None:
        """Test default initialization."""
        test = LoadTest()
        assert test.config.name == "Load Test"
        assert len(test.scenarios) == 0
        assert test.pattern is None

    def test_init_custom(self) -> None:
        """Test custom initialization."""
        test = LoadTest(
            name="My Test",
            duration=120,
            warmup_duration=10,
            max_concurrent=500,
        )
        assert test.config.name == "My Test"
        assert test.config.duration == 120
        assert test.config.max_concurrent == 500

    def test_add_scenario(self) -> None:
        """Test adding scenarios."""
        test = LoadTest()
        scenario = MockScenario(name="Test")

        result = test.add_scenario(scenario, weight=2)

        assert len(test.scenarios) == 1
        assert test.scenarios[0] == (scenario, 2)
        assert result is test  # Test chaining

    def test_set_pattern(self) -> None:
        """Test setting traffic pattern."""
        test = LoadTest()
        pattern = ConstantRateGenerator(rate=10)

        result = test.set_pattern(pattern)

        assert test.pattern is pattern
        assert result is test  # Test chaining

    def test_run_without_scenarios(self) -> None:
        """Test that running without scenarios raises error."""
        test = LoadTest()
        test.set_pattern(ConstantRateGenerator(rate=1))

        with pytest.raises(RuntimeError, match="No scenarios"):
            asyncio.run(test.run())

    def test_run_without_pattern(self) -> None:
        """Test that running without pattern raises error."""
        test = LoadTest()
        test.add_scenario(MockScenario())

        with pytest.raises(RuntimeError, match="No traffic pattern"):
            asyncio.run(test.run())

    @pytest.mark.asyncio
    async def test_run_short_test(self) -> None:
        """Test running a short test."""
        test = LoadTest(
            name="Short Test",
            duration=0.5,
            warmup_duration=0,
            console_output=False,
        )
        test.add_scenario(MockScenario(name="Success", delay=0.01))
        test.set_pattern(ConstantRateGenerator(rate=10))

        result = await test.run()

        assert result.config.name == "Short Test"
        assert result.duration >= 0.5
        assert result.total_requests > 0

    @pytest.mark.asyncio
    async def test_run_with_failures(self) -> None:
        """Test running test with failing scenarios."""
        test = LoadTest(
            name="Failure Test",
            duration=0.5,
            warmup_duration=0,
            console_output=False,
        )
        test.add_scenario(MockScenario(name="Fail", success=False))
        test.set_pattern(ConstantRateGenerator(rate=5))

        result = await test.run()

        assert result.failed_requests > 0
        assert result.success_rate < 100

    def test_console_report(self) -> None:
        """Test console report generation."""
        from loadtest.metrics.collector import MetricsCollector

        test = LoadTest(name="Test Report")
        test.metrics.record_response_time(0.1)
        test.metrics.record_success()
        test.metrics.record_status_code(200)

        report = test.report(format="console")

        assert "Load Test Report" in report
        assert "Test Report" in report
        assert "Total Requests" in report

    def test_html_report(self, tmp_path: Path) -> None:
        """Test HTML report generation."""
        test = LoadTest(name="HTML Test")
        test.metrics.record_response_time(0.1)
        test.metrics.record_success()
        test.metrics.record_status_code(200)

        output_file = tmp_path / "report.html"
        report = test.report(format="html", output=str(output_file))

        assert output_file.exists()
        assert "<!DOCTYPE html>" in report
        assert "HTML Test" in report

    def test_stop(self) -> None:
        """Test stopping a test."""
        test = LoadTest()
        test.stop()
        assert test._stop_event.is_set()


class TestChaining:
    """Tests for method chaining."""

    @pytest.mark.asyncio
    async def test_fluent_interface(self) -> None:
        """Test fluent interface for configuration."""
        test = (
            LoadTest(name="Chained Test", duration=0.5, console_output=False)
            .add_scenario(MockScenario(name="S1"), weight=1)
            .add_scenario(MockScenario(name="S2"), weight=2)
            .set_pattern(ConstantRateGenerator(rate=5))
        )

        result = await test.run()

        assert result.config.name == "Chained Test"
        assert len(test.scenarios) == 2
