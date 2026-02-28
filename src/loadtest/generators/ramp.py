"""Ramp up/down traffic generator.

This module provides the RampGenerator for gradually increasing or
decreasing traffic load, useful for finding system limits and testing
scaling behavior.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class RampGenerator:
    """Generator for ramping traffic up and/or down.

    This generator gradually changes the request rate over time,
    allowing you to test how your system handles increasing load
    (ramp up) or decreasing load (ramp down). It supports:

    - Simple ramp: Linear increase from start to end rate
    - Sawtooth: Ramp up, sustain, then ramp down
    - Stair-step: Discrete steps between rates

    Attributes:
        start_rate: Initial requests per second.
        end_rate: Final requests per second (for simple ramp).
        peak_rate: Maximum rate (for sawtooth pattern).
        ramp_duration: Duration of the ramp phase in seconds.
        sustain_duration: Duration to sustain peak rate.
        ramp_down_duration: Duration of the ramp down phase.
        steps: Number of discrete steps (0 for smooth ramp).

    Example:
        >>> # Simple ramp from 10 to 100 rps over 5 minutes
        >>> generator = RampGenerator(
        ...     start_rate=10,
        ...     end_rate=100,
        ...     ramp_duration=300,
        ... )
        >>>
        >>> # Sawtooth pattern
        >>> generator = RampGenerator(
        ...     start_rate=10,
        ...     peak_rate=200,
        ...     ramp_up_duration=180,
        ...     sustain_duration=60,
        ...     ramp_down_duration=180,
        ... )
    """

    def __init__(
        self,
        start_rate: float = 1.0,
        end_rate: float | None = None,
        peak_rate: float | None = None,
        ramp_duration: float = 60.0,
        ramp_up_duration: float | None = None,
        sustain_duration: float = 0.0,
        ramp_down_duration: float | None = None,
        steps: int = 0,
    ) -> None:
        """Initialize the ramp generator.

        Args:
            start_rate: Initial requests per second.
            end_rate: Final rate for simple ramp.
            peak_rate: Maximum rate for sawtooth pattern.
            ramp_duration: Duration of ramp (for simple ramp).
            ramp_up_duration: Duration to ramp up to peak.
            sustain_duration: Duration to sustain peak rate.
            ramp_down_duration: Duration to ramp down.
            steps: Number of discrete steps (0 for smooth).

        Raises:
            ValueError: If configuration is invalid.
        """
        if start_rate < 0:
            raise ValueError("start_rate must be non-negative")

        self.start_rate = start_rate
        self.end_rate = end_rate
        self.peak_rate = peak_rate
        self.ramp_duration = ramp_duration
        self.ramp_up_duration = ramp_up_duration or ramp_duration
        self.sustain_duration = sustain_duration
        self.ramp_down_duration = ramp_down_duration
        self.steps = steps

        self._running = False
        self._start_time: float | None = None

        # Determine pattern type
        if peak_rate is not None and ramp_down_duration is not None:
            self._pattern = "sawtooth"
            self._total_duration = self.ramp_up_duration + sustain_duration + ramp_down_duration
        else:
            self._pattern = "simple"
            self.end_rate = end_rate or start_rate
            self._total_duration = ramp_duration

    async def generate(self) -> AsyncIterator[float]:
        """Generate a ramping rate of traffic.

        Yields:
            The current target rate based on the ramp pattern.
        """
        self._running = True
        self._start_time = asyncio.get_event_loop().time()

        while self._running:
            elapsed = asyncio.get_event_loop().time() - self._start_time

            if elapsed >= self._total_duration:
                # Hold at final rate
                if self._pattern == "simple":
                    yield self.end_rate
                else:
                    yield self.start_rate
            else:
                rate = self._calculate_rate(elapsed)
                yield rate

            await asyncio.sleep(0.1)

    def _calculate_rate(self, elapsed: float) -> float:
        """Calculate the current rate based on elapsed time.

        Args:
            elapsed: Time elapsed since start.

        Returns:
            The current target rate.
        """
        if self._pattern == "simple":
            return self._calculate_simple_ramp(elapsed)
        else:
            return self._calculate_sawtooth_ramp(elapsed)

    def _calculate_simple_ramp(self, elapsed: float) -> float:
        """Calculate rate for simple ramp pattern.

        Args:
            elapsed: Time elapsed.

        Returns:
            Current rate.
        """
        if elapsed >= self.ramp_duration:
            return self.end_rate

        progress = elapsed / self.ramp_duration

        if self.steps > 0:
            # Stair-step pattern
            step = int(progress * self.steps) / self.steps
            progress = step

        return self.start_rate + progress * (self.end_rate - self.start_rate)

    def _calculate_sawtooth_ramp(self, elapsed: float) -> float:
        """Calculate rate for sawtooth pattern.

        Args:
            elapsed: Time elapsed.

        Returns:
            Current rate.
        """
        peak_rate = self.peak_rate or self.start_rate

        if elapsed < self.ramp_up_duration:
            # Ramp up phase
            progress = elapsed / self.ramp_up_duration

            if self.steps > 0:
                step = int(progress * self.steps) / self.steps
                progress = step

            return self.start_rate + progress * (peak_rate - self.start_rate)

        elif elapsed < self.ramp_up_duration + self.sustain_duration:
            # Sustain phase
            return peak_rate

        else:
            # Ramp down phase
            down_elapsed = elapsed - self.ramp_up_duration - self.sustain_duration
            progress = down_elapsed / self.ramp_down_duration

            if self.steps > 0:
                step = int(progress * self.steps) / self.steps
                progress = step

            return peak_rate - progress * (peak_rate - self.start_rate)

    def stop(self) -> None:
        """Stop the generator."""
        self._running = False

    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        if self._pattern == "simple":
            return (
                f"RampGenerator("
                f"start_rate={self.start_rate}, "
                f"end_rate={self.end_rate}, "
                f"ramp_duration={self.ramp_duration}"
                f")"
            )
        return (
            f"RampGenerator("
            f"start_rate={self.start_rate}, "
            f"peak_rate={self.peak_rate}, "
            f"ramp_up={self.ramp_up_duration}, "
            f"sustain={self.sustain_duration}, "
            f"ramp_down={self.ramp_down_duration}"
            f")"
        )
