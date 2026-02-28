"""Spike traffic generator.

This module provides the SpikeGenerator for simulating sudden,
temporary increases in traffic - useful for testing how systems
handle unexpected load bursts.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator


class SpikeGenerator:
    """Generator for spike traffic patterns.

    This generator simulates sudden bursts of traffic superimposed
    on a baseline load. Spikes can occur at regular intervals or
    randomly, testing your system's ability to handle unexpected
    traffic surges.

    Attributes:
        baseline_rate: Normal requests per second between spikes.
        spike_rate: Requests per second during spikes.
        spike_duration: Duration of each spike in seconds.
        interval: Time between spike starts in seconds.
        jitter: Random variation in interval (0-1, as fraction of interval).
        spike_count: Number of spikes to generate (None for infinite).

    Example:
        >>> # Regular spikes every 5 minutes
        >>> generator = SpikeGenerator(
        ...     baseline_rate=10,
        ...     spike_rate=500,
        ...     spike_duration=30,
        ...     interval=300,
        ... )
        >>>
        >>> # Random spikes with 20% timing variation
        >>> generator = SpikeGenerator(
        ...     baseline_rate=20,
        ...     spike_rate=1000,
        ...     spike_duration=60,
        ...     interval=600,
        ...     jitter=0.2,
        ... )
    """

    def __init__(
        self,
        baseline_rate: float = 10.0,
        spike_rate: float = 100.0,
        spike_duration: float = 10.0,
        interval: float = 60.0,
        jitter: float = 0.0,
        spike_count: int | None = None,
    ) -> None:
        """Initialize the spike generator.

        Args:
            baseline_rate: Normal traffic rate.
            spike_rate: Rate during spikes.
            spike_duration: How long each spike lasts.
            interval: Time between spikes.
            jitter: Random variation in timing (0-1).
            spike_count: Number of spikes (None for infinite).

        Raises:
            ValueError: If parameters are invalid.
        """
        if baseline_rate < 0 or spike_rate < 0:
            raise ValueError("Rates must be non-negative")
        if spike_duration <= 0:
            raise ValueError("spike_duration must be positive")
        if interval <= 0:
            raise ValueError("interval must be positive")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")
        if spike_count is not None and spike_count < 0:
            raise ValueError("spike_count must be non-negative")

        self.baseline_rate = baseline_rate
        self.spike_rate = spike_rate
        self.spike_duration = spike_duration
        self.interval = interval
        self.jitter = jitter
        self.spike_count = spike_count

        self._running = False
        self._start_time: float | None = None
        self._spikes_generated = 0
        self._next_spike_time: float | None = None

    async def generate(self) -> AsyncIterator[float]:
        """Generate a spiky traffic pattern.

        Yields:
            The current target rate (baseline or spike).
        """
        import random

        self._running = True
        self._start_time = asyncio.get_event_loop().time()
        self._spikes_generated = 0
        self._schedule_next_spike(random)

        while self._running:
            elapsed = asyncio.get_event_loop().time() - self._start_time

            # Check if we should stop based on spike count
            if self.spike_count is not None:
                if self._spikes_generated >= self.spike_count:
                    # All spikes done, continue at baseline
                    yield self.baseline_rate
                    await asyncio.sleep(0.1)
                    continue

            # Determine if we're in a spike
            if self._next_spike_time is not None:
                if elapsed >= self._next_spike_time:
                    if elapsed < self._next_spike_time + self.spike_duration:
                        # In a spike
                        yield self.spike_rate
                    else:
                        # Spike ended, schedule next
                        self._spikes_generated += 1
                        self._schedule_next_spike(random)
                        yield self.baseline_rate
                else:
                    # Before next spike
                    yield self.baseline_rate
            else:
                yield self.baseline_rate

            await asyncio.sleep(0.1)

    def _schedule_next_spike(self, random_module) -> None:
        """Schedule the next spike time.

        Args:
            random_module: Random module for jitter calculation.
        """
        if self._start_time is None:
            return

        base_interval = self.interval

        if self.jitter > 0:
            # Add random variation to interval
            jitter_amount = base_interval * self.jitter
            variation = random_module.uniform(-jitter_amount, jitter_amount)
            base_interval += variation

        current_time = asyncio.get_event_loop().time() - self._start_time
        self._next_spike_time = current_time + base_interval

    def stop(self) -> None:
        """Stop the generator."""
        self._running = False

    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        return (
            f"SpikeGenerator("
            f"baseline_rate={self.baseline_rate}, "
            f"spike_rate={self.spike_rate}, "
            f"spike_duration={self.spike_duration}, "
            f"interval={self.interval}"
            f")"
        )


class BurstGenerator:
    """Generator for isolated traffic bursts.

    Unlike SpikeGenerator which creates regular spikes, this generator
    produces a single burst of traffic after an initial delay, useful
    for testing specific burst scenarios.

    Attributes:
        initial_rate: Rate before the burst.
        burst_rate: Rate during the burst.
        burst_duration: Duration of the burst.
        delay: Time before the burst starts.
        final_rate: Rate after the burst (defaults to initial_rate).

    Example:
        >>> # 30-second burst after 2 minutes
        >>> generator = BurstGenerator(
        ...     initial_rate=10,
        ...     burst_rate=1000,
        ...     burst_duration=30,
        ...     delay=120,
        ... )
    """

    def __init__(
        self,
        initial_rate: float = 10.0,
        burst_rate: float = 500.0,
        burst_duration: float = 30.0,
        delay: float = 60.0,
        final_rate: float | None = None,
    ) -> None:
        """Initialize the burst generator.

        Args:
            initial_rate: Rate before burst.
            burst_rate: Rate during burst.
            burst_duration: How long the burst lasts.
            delay: Time before burst starts.
            final_rate: Rate after burst (defaults to initial_rate).

        Raises:
            ValueError: If parameters are invalid.
        """
        if initial_rate < 0 or burst_rate < 0:
            raise ValueError("Rates must be non-negative")
        if burst_duration <= 0:
            raise ValueError("burst_duration must be positive")
        if delay < 0:
            raise ValueError("delay must be non-negative")

        self.initial_rate = initial_rate
        self.burst_rate = burst_rate
        self.burst_duration = burst_duration
        self.delay = delay
        self.final_rate = final_rate if final_rate is not None else initial_rate

        self._running = False
        self._start_time: float | None = None

    async def generate(self) -> AsyncIterator[float]:
        """Generate a single burst traffic pattern.

        Yields:
            The current target rate.
        """
        self._running = True
        self._start_time = asyncio.get_event_loop().time()

        while self._running:
            elapsed = asyncio.get_event_loop().time() - self._start_time

            if elapsed < self.delay:
                # Before burst
                yield self.initial_rate
            elif elapsed < self.delay + self.burst_duration:
                # During burst
                yield self.burst_rate
            else:
                # After burst
                yield self.final_rate

            await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop the generator."""
        self._running = False

    def __repr__(self) -> str:
        """Return a string representation of the generator."""
        return (
            f"BurstGenerator("
            f"initial_rate={self.initial_rate}, "
            f"burst_rate={self.burst_rate}, "
            f"burst_duration={self.burst_duration}, "
            f"delay={self.delay}"
            f")"
        )
