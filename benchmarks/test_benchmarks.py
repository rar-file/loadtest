"""Performance benchmarks for loadtest."""

import asyncio
import pytest
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.generators.ramp import RampGenerator
from loadtest.generators.spike import SpikeGenerator


class TestLoadTestBenchmarks:
    """Benchmarks for core LoadTest functionality."""

    @pytest.mark.asyncio
    async def test_scenario_creation(self, benchmark):
        """Benchmark scenario creation."""
        def create_scenarios():
            return [
                HTTPScenario(
                    name=f"Scenario{i}",
                    method="GET",
                    url=f"https://api.example.com/endpoint{i}",
                )
                for i in range(100)
            ]

        scenarios = benchmark(create_scenarios)
        assert len(scenarios) == 100

    def test_add_scenarios(self, benchmark):
        """Benchmark adding scenarios to test."""
        test = LoadTest(name="Benchmark")
        scenario = HTTPScenario(name="Test", method="GET", url="https://api.example.com")

        def add_scenarios():
            t = LoadTest(name="Benchmark")
            for i in range(100):
                t.add_scenario(scenario, weight=1)
            return t

        result = benchmark(add_scenarios)
        assert len(result.scenarios) == 100


class TestGeneratorBenchmarks:
    """Benchmarks for traffic generators."""

    def test_constant_generator_creation(self, benchmark):
        """Benchmark constant generator creation."""
        def create_generators():
            return [ConstantRateGenerator(rate=i) for i in range(1, 1000)]

        generators = benchmark(create_generators)
        assert len(generators) == 999

    def test_ramp_generator_creation(self, benchmark):
        """Benchmark ramp generator creation."""
        def create_generators():
            return [
                RampGenerator(
                    start_rate=10,
                    end_rate=100 + i * 10,
                    ramp_duration=60
                )
                for i in range(100)
            ]

        generators = benchmark(create_generators)
        assert len(generators) == 100

    def test_spike_generator_creation(self, benchmark):
        """Benchmark spike generator creation."""
        def create_generators():
            return [
                SpikeGenerator(
                    baseline_rate=10,
                    spike_rate=100 + i * 50,
                    spike_duration=30,
                    interval=300
                )
                for i in range(100)
            ]

        generators = benchmark(create_generators)
        assert len(generators) == 100


class TestMetricsBenchmarks:
    """Benchmarks for metrics collection."""

    def test_metrics_recording(self, benchmark):
        """Benchmark metrics recording."""
        from loadtest.metrics.collector import MetricsCollector

        metrics = MetricsCollector()

        def record_metrics():
            for i in range(1000):
                metrics.record("response_time", 0.1 + i * 0.001)

        benchmark(record_metrics)
        stats = metrics.get_statistics()
        assert stats["custom_metrics"]["response_time"]["count"] == 1000

    def test_statistics_calculation(self, benchmark):
        """Benchmark statistics calculation."""
        from loadtest.metrics.collector import MetricsCollector

        metrics = MetricsCollector()
        for i in range(10000):
            metrics.record("response_time", 0.1 + i * 0.0001)

        def calculate_stats():
            return metrics.get_statistics()

        stats = benchmark(calculate_stats)
        custom_stats = stats["custom_metrics"]["response_time"]
        assert "mean" in custom_stats
        assert "p95" in custom_stats
        assert "p99" in custom_stats


class TestReportBenchmarks:
    """Benchmarks for report generation."""

    def test_console_report_generation(self, benchmark):
        """Benchmark console report generation."""
        from loadtest.metrics.collector import MetricsCollector

        test = LoadTest(name="Report Test")

        # Add sample metrics
        for i in range(1000):
            test.metrics.record("response_time", 0.1 + i * 0.001)

        def generate_report():
            return test._generate_console_report()

        report = benchmark(generate_report)
        assert "Load Test Report" in report


class TestScenarioBenchmarks:
    """Benchmarks for scenario execution."""

    @pytest.mark.asyncio
    async def test_http_scenario_creation(self, benchmark):
        """Benchmark HTTP scenario creation."""
        def create_scenarios():
            return [
                HTTPScenario(
                    name=f"Scenario{i}",
                    method="GET",
                    url=f"https://api.example.com/{i}",
                    headers={"Authorization": "Bearer token"},
                )
                for i in range(1000)
            ]

        scenarios = benchmark(create_scenarios)
        assert len(scenarios) == 1000

    @pytest.mark.asyncio
    async def test_scenario_with_dynamic_data(self, benchmark):
        """Benchmark scenario with dynamic data generation."""
        from phoney import Phoney

        phoney = Phoney()

        def create_scenarios():
            return [
                HTTPScenario(
                    name=f"Scenario{i}",
                    method="POST",
                    url="https://api.example.com/users",
                    data_factory=lambda: {
                        "name": phoney.full_name(),
                        "email": phoney.email(),
                    },
                )
                for i in range(100)
            ]

        scenarios = benchmark(create_scenarios)
        assert len(scenarios) == 100


class TestMemoryBenchmarks:
    """Memory usage benchmarks."""

    def test_memory_with_many_scenarios(self):
        """Test memory efficiency with many scenarios."""
        import tracemalloc

        tracemalloc.start()

        # Take memory snapshot before
        snapshot1 = tracemalloc.take_snapshot()

        # Create test with many scenarios
        test = LoadTest(name="Memory Test")
        for i in range(1000):
            scenario = HTTPScenario(
                name=f"Scenario{i}",
                method="GET",
                url=f"https://api.example.com/{i}",
            )
            test.add_scenario(scenario, weight=1)

        # Take memory snapshot after
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory usage
        stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_memory = sum(stat.size_diff for stat in stats if stat.size_diff > 0)

        # Should use less than 10MB for 1000 scenarios
        assert total_memory < 10 * 1024 * 1024

        tracemalloc.stop()

    def test_memory_with_many_metrics(self):
        """Test memory efficiency with many metrics."""
        import tracemalloc

        tracemalloc.start()

        from loadtest.metrics.collector import MetricsCollector

        # Take memory snapshot before
        snapshot1 = tracemalloc.take_snapshot()

        # Record many metrics
        metrics = MetricsCollector()
        for i in range(100000):
            metrics.record("response_time", 0.1 + (i % 100) * 0.001)

        # Take memory snapshot after
        snapshot2 = tracemalloc.take_snapshot()

        # Calculate memory usage
        stats = snapshot2.compare_to(snapshot1, 'lineno')
        total_memory = sum(stat.size_diff for stat in stats if stat.size_diff > 0)

        # Should use less than 50MB for 100k metrics
        assert total_memory < 50 * 1024 * 1024

        tracemalloc.stop()


class TestConcurrentBenchmarks:
    """Concurrency benchmarks."""

    @pytest.mark.asyncio
    async def test_concurrent_scenario_creation(self, benchmark):
        """Benchmark concurrent scenario operations."""
        async def create_scenarios_concurrent():
            tasks = [
                asyncio.create_task(
                    asyncio.to_thread(
                        lambda i: HTTPScenario(
                            name=f"Scenario{i}",
                            method="GET",
                            url=f"https://api.example.com/{i}",
                        ),
                        i
                    )
                )
                for i in range(100)
            ]
            return await asyncio.gather(*tasks)

        scenarios = await benchmark(create_scenarios_concurrent)
        assert len(scenarios) == 100
