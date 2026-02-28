"""Constant rate traffic generator.

This module provides the ConstantRateGenerator for generating a steady,
predictable stream of traffic at a fixed rate.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class ConstantRateGenerator:
    """Generator for constant rate traffic.

    This generator produces a steady stream of requests at a fixed rate
    (requests per second) throughout the test duration. This is useful
    for baseline testing and establishing performance characteristics
    under stable load.

    Attributes:
        rate: Target requests per second.
        interval: Time between request batches.

    Example:
        >>> generator = ConstantRateGenerator(rate=10)
        >>> async for current_rate in generator.generate():
        ...     # Execute requests at current_rate per second
        ...     pass
    """

    def __init__(self, rate: float = 1.0) -> None:
        """Initialize the constant rate generator.

        Args:
            rate: Target requests per second. Must be positive.

        Raises:
            ValueError: If rate is not positive.
        """
        if rate <= 0:
            raise ValueError("Rate must be positive")

        self.rate = rate
        self._running = False

    async def generate(self) -> AsyncIterator[float]:
        """Generate a constant rate of traffic.

        Yields:
            The current target rate (constant).
        """
        self._running = True

        while self._running:
            yield self.rate
            await asyncio.sleep(0.1)  # Update every 100ms

    def stop(self) -> None:
        """Stop the generator."""
        self._running = False

    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        return f"ConstantRateGenerator(rate={self.rate})"


class VariableRateGenerator:
    """Generator for variable but controlled traffic patterns.

    This generator produces traffic that varies between a minimum and
    maximum rate, useful for simulating changing load conditions.

    Attributes:
        min_rate: Minimum requests per second.
        max_rate: Maximum requests per second.
        period: Duration of one complete cycle in seconds.
        waveform: Shape of the variation ('sine', 'square', 'sawtooth').

    Example:
        >>> generator = VariableRateGenerator(
        ...     min_rate=10,
        ...     max_rate=50,
        ...     period=60,
        ...     waveform='sine',
        ... )
    """

    def __init__(
        self,
        min_rate: float = 1.0,
        max_rate: float = 10.0,
        period: float = 60.0,
        waveform: str = "sine",
    ) -> None:
        """Initialize the variable rate generator.

        Args:
            min_rate: Minimum requests per second.
            max_rate: Maximum requests per second.
            period: Duration of one cycle in seconds.
            waveform: Variation pattern ('sine', 'square', 'sawtooth').

        Raises:
            ValueError: If rates are invalid or waveform unknown.
        """
        if min_rate < 0 or max_rate < 0:
            raise ValueError("Rates must be non-negative")
        if min_rate > max_rate:
            raise ValueError("min_rate must be <= max_rate")
        if period <= 0:
            raise ValueError("Period must be positive")
        if waveform not in ("sine", "square", "sawtooth"):
            raise ValueError(f"Unknown waveform: {waveform}")

        self.min_rate = min_rate
        self.max_rate = max_rate
        self.period = period
        self.waveform = waveform
        self._running = False
        self._start_time: float | None = None

    async def generate(self) -> AsyncIterator[float]:
        """Generate a variable rate of traffic.

        Yields:
            The current target rate based on the waveform.
        """
        import math

        self._running = True
        self._start_time = asyncio.get_event_loop().time()

        while self._running:
            elapsed = asyncio.get_event_loop().time() - self._start_time
            rate = self._calculate_rate(elapsed, math)
            yield rate
            await asyncio.sleep(0.1)

    def _calculate_rate(self, elapsed: float, math_module) -> float:
        """Calculate the current rate based on elapsed time.

        Args:
            elapsed: Time elapsed since start.
            math_module: Math module for calculations.

        Returns:
            The current target rate.
        """
        phase = (elapsed % self.period) / self.period

        if self.waveform == "sine":
            # Sine wave: varies smoothly between min and max
            value = (math_module.sin(phase * 2 * math_module.pi) + 1) / 2
            return self.min_rate + value * (self.max_rate - self.min_rate)

        elif self.waveform == "square":
            # Square wave: alternates between min and max
            return self.max_rate if phase < 0.5 else self.min_rate

        elif self.waveform == "sawtooth":
            # Sawtooth: ramps from min to max then resets
            return self.min_rate + phase * (self.max_rate - self.min_rate)

        return self.min_rate

    def stop(self) -> None:
        """Stop the generator."""
        self._running = False

    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        return (
            f"VariableRateGenerator("
            f"min_rate={self.min_rate}, "
            f"max_rate={self.max_rate}, "
            f"period={self.period}, "
            f"waveform='{self.waveform}'"
            f")"
        )
