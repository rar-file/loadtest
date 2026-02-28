"""Simple API for loadtest - Get started in 3 lines.

This module provides a dead-simple API for the most common load testing scenarios.
For advanced use cases, use the core API directly.

Examples:
    # Simplest possible test
    from loadtest import loadtest
    test = loadtest("https://api.example.com")
    test.run()

    # With options
    test = loadtest("https://api.example.com",
                    pattern="ramp", rps=100, duration=60)
    test.add("GET /users")
    test.add("POST /orders", weight=0.3)
    test.run()

    # Full control
    test = loadtest("https://api.example.com")
    test.pattern("spike", base_rps=10, peak_rps=1000, duration=120)
    test.add("GET /api/products", headers={"Accept": "application/json"})
    test.add("POST /api/cart", json={"product_id": 123})
    test.run()
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from loadtest.core import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.generators.ramp import RampGenerator
from loadtest.generators.spike import SpikeGenerator
from loadtest.scenarios.http import HTTPScenario


@dataclass
class Endpoint:
    """Simple endpoint configuration.

    Attributes:
        method: HTTP method (GET, POST, etc.)
        path: URL path
        weight: Relative frequency of this endpoint
        headers: HTTP headers
        json: JSON body for POST/PUT
        data: Form data
    """

    method: str
    path: str
    weight: float = 1.0
    headers: dict | None = None
    json: dict | None = None
    data: dict | None = None


class SimpleLoadTest:
    """Simplified load test interface.

    This class provides a simplified API for common load testing
    scenarios. It wraps the core LoadTest API with sensible defaults.

    Example:
        >>> test = loadtest("https://api.example.com")
        >>> test.add("GET /users")
        >>> test.add("POST /orders", weight=0.5)
        >>> test.run()
    """

    def __init__(
        self,
        target: str,
        pattern: str = "constant",
        rps: float = 10,
        duration: float = 60,
        **pattern_kwargs,
    ) -> None:
        """Create a simple load test.

        Args:
            target: Base URL to test (e.g., "https://api.example.com")
            pattern: Traffic pattern - "constant", "ramp", "spike", "burst"
            rps: Requests per second (or base RPS for variable patterns)
            duration: Test duration in seconds
            **pattern_kwargs: Pattern-specific options:
                - ramp: target_rps, warmup
                - spike: peak_rps, spike_duration
                - burst: burst_rps, burst_duration, delay

        Example:
            >>> test = loadtest("https://api.example.com")
            >>> test = loadtest("https://api.example.com",
            ...                 pattern="ramp", rps=10, target_rps=100)
        """
        self.target = target.rstrip("/")
        self._endpoints: list[Endpoint] = []
        self._pattern_type = pattern
        self._rps = rps
        self._duration = duration
        self._pattern_kwargs = pattern_kwargs
        self._global_headers: dict[str, str] = {}
        self._test: LoadTest | None = None
        self._results: Any = None

    def add(
        self,
        endpoint: str,
        weight: float = 1.0,
        headers: dict | None = None,
        json: dict | None = None,  # noqa: A002
        data: dict | None = None,
    ) -> SimpleLoadTest:
        """Add an endpoint to test.

        Args:
            endpoint: Endpoint spec like "GET /users" or just "/users" (defaults to GET)
            weight: Relative frequency (1.0 = normal, 0.5 = half as often, 2.0 = twice as often)
            headers: HTTP headers for this endpoint
            json: JSON body for POST/PUT
            data: Form data for POST/PUT

        Returns:
            Self for method chaining

        Example:
            >>> test.add("GET /users")
            >>> test.add("POST /orders", weight=0.5, json={"item": "widget"})
        """
        # Parse endpoint spec
        parts = endpoint.split(None, 1)
        if len(parts) == 2:
            method, path = parts
        else:
            method = "GET"
            path = parts[0]

        # Merge with global headers
        merged_headers = {**self._global_headers, **(headers or {})}

        self._endpoints.append(
            Endpoint(
                method=method.upper(),
                path=path,
                weight=weight,
                headers=merged_headers or None,
                json=json,
                data=data,
            )
        )
        return self

    def headers(self, headers: dict[str, str]) -> SimpleLoadTest:
        """Set global headers for all requests.

        Args:
            headers: Headers to add to all requests

        Returns:
            Self for method chaining
        """
        self._global_headers.update(headers)
        return self

    def auth(
        self, token: str, header: str = "Authorization", prefix: str = "Bearer "
    ) -> SimpleLoadTest:
        """Set authentication token.

        Args:
            token: Auth token
            header: Header name (default: Authorization)
            prefix: Token prefix (default: "Bearer ")

        Returns:
            Self for method chaining
        """
        self._global_headers[header] = f"{prefix}{token}"
        return self

    def pattern(self, pattern: str, rps: float | None = None, **kwargs) -> SimpleLoadTest:
        """Change the traffic pattern.

        Args:
            pattern: Pattern type - "constant", "ramp", "spike", "burst"
            rps: Base requests per second
            **kwargs: Pattern-specific options

        Returns:
            Self for method chaining
        """
        self._pattern_type = pattern
        if rps is not None:
            self._rps = rps
        self._pattern_kwargs.update(kwargs)
        return self

    def _create_pattern(self):
        """Create the traffic pattern generator."""
        if self._pattern_type == "constant":
            return ConstantRateGenerator(rate=self._rps)

        elif self._pattern_type == "ramp":
            return RampGenerator(
                start_rate=self._rps,
                end_rate=self._pattern_kwargs.get("target_rps", self._rps * 10),
                ramp_duration=self._duration,
            )

        elif self._pattern_type == "spike":
            return SpikeGenerator(
                baseline_rate=self._rps,
                spike_rate=self._pattern_kwargs.get("peak_rps", self._rps * 10),
                spike_duration=self._pattern_kwargs.get("spike_duration", 10),
                interval=self._duration,  # Time between spikes
            )

        elif self._pattern_type == "burst":
            from loadtest.generators.spike import BurstGenerator

            return BurstGenerator(
                initial_rate=self._rps,
                burst_rate=self._pattern_kwargs.get("burst_rps", self._rps * 50),
                burst_duration=self._pattern_kwargs.get("burst_duration", 30),
                delay=self._pattern_kwargs.get("delay", 30),
            )

        else:
            raise ValueError(
                f"Unknown pattern: {self._pattern_type}. Use: constant, ramp, spike, burst"
            )

    def _build_scenarios(self) -> list[tuple[HTTPScenario, int]]:
        """Build HTTP scenarios from endpoints."""
        if not self._endpoints:
            # Auto-add root if no endpoints specified
            self.add("/")

        scenarios = []
        for ep in self._endpoints:
            url = f"{self.target}{ep.path}"
            scenario = HTTPScenario(
                name=f"{ep.method} {ep.path}",
                method=ep.method,
                url=url,
                headers=ep.headers,
                data=ep.json or ep.data,
            )
            # Convert float weight to int (multiply by 10 for precision)
            weight = max(1, int(ep.weight * 10))
            scenarios.append((scenario, weight))

        return scenarios

    async def run_async(self) -> Any:
        """Run the load test asynchronously.

        Returns:
            Test results
        """
        self._test = LoadTest(
            name=f"Load Test - {self.target}",
            duration=self._duration,
            console_output=True,
        )

        # Add scenarios
        for scenario, weight in self._build_scenarios():
            self._test.add_scenario(scenario, weight=weight)

        # Set pattern
        self._test.set_pattern(self._create_pattern())

        # Run the test
        self._results = await self._test.run()

        # Print report
        print(self._test.report(format="console"))

        return self._results

    def run(self) -> Any:
        """Run the load test.

        Returns:
            Test results

        Example:
            >>> test = loadtest("https://api.example.com")
            >>> test.add("GET /users")
            >>> results = test.run()
            >>> print(f"Success rate: {results.success_rate}%")
        """
        return asyncio.run(self.run_async())

    def report(self, format: str = "html", output: str | None = None) -> str:  # noqa: A002
        """Generate a test report.

        Args:
            format: Report format ("html", "json", "console")
            output: Output file path (optional)

        Returns:
            Report as string
        """
        if self._test is None:
            raise RuntimeError("No test has been run yet. Call run() first.")
        return self._test.report(format=format, output=output)

    def dry_run(self) -> dict:
        """Preview the test configuration without running.

        Returns:
            Test configuration summary
        """
        scenarios = self._build_scenarios()

        return {
            "target": self.target,
            "pattern": {
                "type": self._pattern_type,
                "base_rps": self._rps,
                "duration": self._duration,
                "options": self._pattern_kwargs,
            },
            "endpoints": (
                [
                    {
                        "method": ep.method,
                        "path": ep.path,
                        "weight": ep.weight,
                        "url": f"{self.target}{ep.path}",
                    }
                    for ep in self._endpoints
                ]
                if self._endpoints
                else [{"method": "GET", "path": "/", "url": self.target}]
            ),
            "total_scenarios": len(scenarios),
            "estimated_requests": int(self._rps * self._duration),
        }


def loadtest(
    target: str, pattern: str = "constant", rps: float = 10, duration: float = 60, **pattern_kwargs
) -> SimpleLoadTest:
    """Create a simple load test.

    This is the main entry point for the simple API.

    Args:
        target: Base URL to test (e.g., "https://api.example.com")
        pattern: Traffic pattern - "constant", "ramp", "spike", "burst"
        rps: Requests per second (base rate)
        duration: Test duration in seconds
        **pattern_kwargs: Pattern-specific options

    Returns:
        SimpleLoadTest instance ready to configure and run

    Examples:
        # Simplest test
        >>> test = loadtest("https://api.example.com")
        >>> test.run()

        # With pattern
        >>> test = loadtest("https://api.example.com",
        ...                 pattern="ramp", rps=10, target_rps=100)
        >>> test.run()

        # Full configuration
        >>> test = loadtest("https://api.example.com")
        >>> test.add("GET /users")
        >>> test.add("POST /orders", weight=0.3)
        >>> test.run()
    """
    return SimpleLoadTest(
        target=target, pattern=pattern, rps=rps, duration=duration, **pattern_kwargs
    )
