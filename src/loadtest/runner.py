"""Test execution engine module.

This module provides the TestRunner class for executing scenarios
according to traffic patterns with controlled concurrency.
"""

from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from loadtest.metrics.collector import MetricsCollector

if TYPE_CHECKING:
    from loadtest.generators.constant import ConstantRateGenerator
    from loadtest.scenarios.base import Scenario


class TestRunner:
    """Execution engine for running load test scenarios.
    
    This class manages the concurrent execution of scenarios according to
    a traffic pattern, handling rate limiting and result collection.
    
    Attributes:
        scenarios: List of (scenario, weight) tuples to execute.
        pattern: The traffic pattern generator controlling request rates.
        metrics: The metrics collector for recording results.
        max_concurrent: Maximum number of concurrent scenario executions.
        console_output: Whether to display real-time output.
    """
    
    def __init__(
        self,
        scenarios: list[tuple[Scenario, int]],
        pattern: ConstantRateGenerator,
        metrics: MetricsCollector,
        max_concurrent: int = 1000,
        console_output: bool = True,
    ) -> None:
        """Initialize the TestRunner.
        
        Args:
            scenarios: List of scenarios with their weights.
            pattern: Traffic pattern generator.
            metrics: Metrics collector instance.
            max_concurrent: Maximum concurrent executions.
            console_output: Enable real-time console output.
        """
        self.scenarios = scenarios
        self.pattern = pattern
        self.metrics = metrics
        self.max_concurrent = max_concurrent
        self.console_output = console_output
        
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._stop_event = asyncio.Event()
        self._tasks: set[asyncio.Task] = set()
        self._context: dict = {}
    
    async def run(self) -> None:
        """Run the test until stopped or pattern completes.
        
        This method continuously generates scenario executions according
        to the traffic pattern until the stop event is set.
        """
        self._stop_event.clear()
        
        try:
            async for rate in self.pattern.generate():
                if self._stop_event.is_set():
                    break
                
                await self._execute_at_rate(rate)
                
        except asyncio.CancelledError:
            pass
    
    async def _execute_at_rate(self, rate: float) -> None:
        """Execute scenarios at the specified rate.
        
        Args:
            rate: Target requests per second.
        """
        if rate <= 0:
            await asyncio.sleep(0.1)
            return
        
        interval = 1.0 / rate
        
        # Create tasks for this interval
        tasks = []
        num_requests = max(1, int(rate * 0.1))  # Batch requests in 100ms windows
        
        for _ in range(num_requests):
            if self._stop_event.is_set():
                break
            
            task = asyncio.create_task(self._execute_single())
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            tasks.append(task)
            
            # Small delay between requests within the batch
            await asyncio.sleep(interval / num_requests)
        
        # Wait for the remainder of the interval
        await asyncio.sleep(max(0, interval - (interval / num_requests) * len(tasks)))
    
    async def _execute_single(self) -> None:
        """Execute a single scenario instance.
        
        Selects a scenario based on weights and executes it,
        recording metrics for the result.
        """
        async with self._semaphore:
            scenario = self._select_scenario()
            if scenario is None:
                return
            
            start_time = asyncio.get_event_loop().time()
            
            try:
                context = {
                    "metrics": self.metrics,
                    **self._context,
                }
                
                result = await scenario.execute(context)
                
                elapsed = asyncio.get_event_loop().time() - start_time
                
                # Record success
                self.metrics.record_response_time(elapsed)
                self.metrics.record_success()
                
                if hasattr(result, "status_code"):
                    self.metrics.record_status_code(result.status_code)
                
            except Exception as e:
                elapsed = asyncio.get_event_loop().time() - start_time
                self.metrics.record_response_time(elapsed)
                self.metrics.record_failure(str(e))
    
    def _select_scenario(self) -> Scenario | None:
        """Select a scenario based on configured weights.
        
        Returns:
            The selected scenario or None if no scenarios configured.
        """
        if not self.scenarios:
            return None
        
        total_weight = sum(weight for _, weight in self.scenarios)
        if total_weight == 0:
            return None
        
        r = random.uniform(0, total_weight)  # noqa: S311
        cumulative = 0
        
        for scenario, weight in self.scenarios:
            cumulative += weight
            if r <= cumulative:
                return scenario
        
        return self.scenarios[-1][0]
    
    def stop(self) -> None:
        """Signal the runner to stop execution."""
        self._stop_event.set()
    
    async def cleanup(self) -> None:
        """Clean up resources and cancel pending tasks."""
        self.stop()
        
        # Cancel all pending tasks
        if self._tasks:
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()
