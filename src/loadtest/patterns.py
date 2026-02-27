"""Enhanced traffic pattern engine for load testing.

This module provides advanced traffic pattern generation with support
for pattern composition, events/hooks, and smooth transitions.
"""

from __future__ import annotations

import asyncio
import math
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, AsyncIterator, Callable

if TYPE_CHECKING:
    pass


class PatternEventType(Enum):
    """Traffic pattern event types."""
    START = auto()
    RAMP_START = auto()
    RAMP_END = auto()
    SPIKE_START = auto()
    SPIKE_END = auto()
    BURST_START = auto()
    BURST_END = auto()
    STOP = auto()


@dataclass
class PatternEvent:
    """Traffic pattern event.
    
    Attributes:
        event_type: Type of event.
        timestamp: Event timestamp.
        rate: Current rate at event time.
        metadata: Additional event data.
    """
    event_type: PatternEventType
    timestamp: float = field(default_factory=time.time)
    rate: float = 0.0
    metadata: dict = field(default_factory=dict)


class TrafficPattern(ABC):
    """Abstract base class for traffic patterns.
    
    All traffic patterns must implement this interface to be
    usable by the load test engine.
    
    Attributes:
        name: Pattern name.
        _running: Whether pattern is running.
        _event_handlers: Event handlers by type.
    """
    
    def __init__(self, name: str = "") -> None:
        """Initialize traffic pattern.
        
        Args:
            name: Pattern name.
        """
        self.name = name or self.__class__.__name__
        self._running = False
        self._event_handlers: dict[
            PatternEventType,
            list[Callable[[PatternEvent], None]],
        ] = {event_type: [] for event_type in PatternEventType}
    
    @abstractmethod
    async def generate(self) -> AsyncIterator[float]:
        """Generate traffic rates.
        
        Yields:
            Current target rate (requests per second).
        """
        pass
    
    def on(
        self,
        event_type: PatternEventType,
        handler: Callable[[PatternEvent], None] | None = None,
    ) -> Callable[[PatternEvent], None] | Callable[[Callable[[PatternEvent], None]], Callable[[PatternEvent], None]]:
        """Register an event handler.
        
        Can be used as a decorator or direct call:
            @generator.on(PatternEventType.START)
            def handler(event): pass
            
            # Or:
            generator.on(PatternEventType.START, handler)
        
        Args:
            event_type: Event type to listen for.
            handler: Handler function (optional when used as decorator).
        
        Returns:
            The handler function, or a wrapper when used as decorator.
        """
        def _register(h: Callable[[PatternEvent], None]) -> Callable[[PatternEvent], None]:
            self._event_handlers[event_type].append(h)
            return h
        
        if handler is not None:
            # Direct call: generator.on(EVENT, handler)
            return _register(handler)
        else:
            # Decorator: @generator.on(EVENT)
            return _register
    
    def _emit(self, event_type: PatternEventType, rate: float = 0.0, **kwargs) -> None:
        """Emit an event to registered handlers.
        
        Args:
            event_type: Type of event.
            rate: Current rate.
            **kwargs: Additional event data.
        """
        event = PatternEvent(
            event_type=event_type,
            rate=rate,
            metadata=kwargs,
        )
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass  # Don't let event handlers break the pattern
    
    def stop(self) -> None:
        """Stop the pattern."""
        self._running = False
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"


class BurstGenerator(TrafficPattern):
    """Generator for isolated traffic bursts.
    
    Produces a single high-intensity burst of traffic after an
    initial delay, useful for testing specific burst scenarios.
    
    Attributes:
        initial_rate: Rate before the burst.
        burst_rate: Peak rate during burst.
        burst_duration: Duration of the burst.
        delay: Time before burst starts.
        final_rate: Rate after burst.
        pre_burst_hold: Duration to hold initial rate before burst.
    """
    
    def __init__(
        self,
        initial_rate: float = 10.0,
        burst_rate: float = 1000.0,
        burst_duration: float = 30.0,
        delay: float = 60.0,
        final_rate: float | None = None,
        pre_burst_hold: float = 0.0,
        name: str = "",
    ) -> None:
        """Initialize burst generator.
        
        Args:
            initial_rate: Rate before burst.
            burst_rate: Peak rate during burst.
            burst_duration: How long burst lasts.
            delay: Time before burst.
            final_rate: Rate after burst (defaults to initial_rate).
            pre_burst_hold: Time to hold at initial rate.
            name: Pattern name.
        """
        super().__init__(name or "Burst")
        
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
        self.pre_burst_hold = pre_burst_hold
        
        self._total_duration = delay + burst_duration + pre_burst_hold
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate burst traffic pattern.
        
        Yields:
            Current target rate.
        """
        self._running = True
        start_time = asyncio.get_event_loop().time()
        
        self._emit(PatternEventType.START, self.initial_rate)
        burst_emitted = False
        burst_ended = False
        
        while self._running:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed < self.delay:
                rate = self.initial_rate
            elif elapsed < self.delay + self.burst_duration:
                if not burst_emitted:
                    self._emit(PatternEventType.BURST_START, self.burst_rate)
                    burst_emitted = True
                rate = self.burst_rate
            else:
                if burst_emitted and not burst_ended:
                    self._emit(PatternEventType.BURST_END, self.final_rate)
                    burst_ended = True
                rate = self.final_rate
            
            yield rate
            await asyncio.sleep(0.1)
    
    def __repr__(self) -> str:
        return (
            f"BurstGenerator("
            f"initial_rate={self.initial_rate}, "
            f"burst_rate={self.burst_rate}, "
            f"burst_duration={self.burst_duration}, "
            f"delay={self.delay}"
            f")"
        )


class SteadyStateGenerator(TrafficPattern):
    """Generator for steady-state traffic with jitter.
    
    Maintains a target rate with optional random variation to
    simulate more realistic traffic patterns.
    
    Attributes:
        target_rate: Base requests per second.
        jitter: Random variation as fraction of target (0-1).
        jitter_distribution: Distribution type ('uniform', 'gaussian').
    """
    
    def __init__(
        self,
        target_rate: float = 100.0,
        jitter: float = 0.1,
        jitter_distribution: str = "uniform",
        name: str = "",
    ) -> None:
        """Initialize steady-state generator.
        
        Args:
            target_rate: Base rate.
            jitter: Variation fraction (0-1).
            jitter_distribution: 'uniform' or 'gaussian'.
            name: Pattern name.
        """
        super().__init__(name or "SteadyState")
        
        if target_rate < 0:
            raise ValueError("target_rate must be non-negative")
        if not 0 <= jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")
        if jitter_distribution not in ("uniform", "gaussian"):
            raise ValueError("jitter_distribution must be 'uniform' or 'gaussian'")
        
        self.target_rate = target_rate
        self.jitter = jitter
        self.jitter_distribution = jitter_distribution
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate steady-state traffic with jitter.
        
        Yields:
            Current target rate with jitter applied.
        """
        self._running = True
        self._emit(PatternEventType.START, self.target_rate)
        
        while self._running:
            if self.jitter_distribution == "uniform":
                variation = random.uniform(-self.jitter, self.jitter)
            else:  # gaussian
                variation = random.gauss(0, self.jitter / 3)
                variation = max(-self.jitter, min(self.jitter, variation))
            
            rate = self.target_rate * (1 + variation)
            rate = max(0, rate)  # Never negative
            
            yield rate
            await asyncio.sleep(0.1)
    
    def __repr__(self) -> str:
        return (
            f"SteadyStateGenerator("
            f"target_rate={self.target_rate}, "
            f"jitter={self.jitter}, "
            f"distribution={self.jitter_distribution}"
            f")"
        )


class CustomCurveGenerator(TrafficPattern):
    """Generator for user-defined curve patterns.
    
    Allows specifying a custom function that determines the
    rate based on elapsed time.
    
    Attributes:
        curve_function: Function that takes elapsed time and returns rate.
        duration: Total duration (None for infinite).
    """
    
    def __init__(
        self,
        curve_function: Callable[[float], float],
        duration: float | None = None,
        name: str = "",
    ) -> None:
        """Initialize custom curve generator.
        
        Args:
            curve_function: Function(elapsed_time) -> rate.
            duration: Optional total duration.
            name: Pattern name.
        """
        super().__init__(name or "CustomCurve")
        self.curve_function = curve_function
        self.duration = duration
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate custom curve traffic.
        
        Yields:
            Current target rate from curve function.
        """
        self._running = True
        start_time = asyncio.get_event_loop().time()
        
        self._emit(PatternEventType.START, self.curve_function(0))
        
        while self._running:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if self.duration is not None and elapsed >= self.duration:
                rate = self.curve_function(self.duration)
            else:
                rate = self.curve_function(elapsed)
            
            yield max(0, rate)
            await asyncio.sleep(0.1)
    
    def __repr__(self) -> str:
        return f"CustomCurveGenerator(duration={self.duration})"


class StepLadderGenerator(TrafficPattern):
    """Generator for step ladder traffic patterns.
    
    Increases load in discrete steps, holding each step for
    a specified duration. Useful for capacity testing.
    
    Attributes:
        start_rate: Initial rate.
        end_rate: Final rate.
        steps: Number of steps.
        step_duration: Duration of each step.
        direction: 'up', 'down', or 'updown'.
    """
    
    def __init__(
        self,
        start_rate: float = 10.0,
        end_rate: float = 100.0,
        steps: int = 5,
        step_duration: float = 60.0,
        direction: str = "up",
        name: str = "",
    ) -> None:
        """Initialize step ladder generator.
        
        Args:
            start_rate: Starting rate.
            end_rate: Ending rate.
            steps: Number of steps.
            step_duration: Seconds per step.
            direction: 'up', 'down', or 'updown'.
            name: Pattern name.
        """
        super().__init__(name or "StepLadder")
        
        if start_rate < 0 or end_rate < 0:
            raise ValueError("Rates must be non-negative")
        if steps < 1:
            raise ValueError("steps must be at least 1")
        if step_duration <= 0:
            raise ValueError("step_duration must be positive")
        if direction not in ("up", "down", "updown"):
            raise ValueError("direction must be 'up', 'down', or 'updown'")
        
        self.start_rate = start_rate
        self.end_rate = end_rate
        self.steps = steps
        self.step_duration = step_duration
        self.direction = direction
        
        # Calculate step values
        if direction == "up":
            self._step_values = [
                start_rate + (end_rate - start_rate) * i / (steps - 1)
                for i in range(steps)
            ]
        elif direction == "down":
            self._step_values = [
                end_rate + (start_rate - end_rate) * i / (steps - 1)
                for i in range(steps)
            ]
        else:  # updown
            mid = (start_rate + end_rate) / 2
            up_steps = steps // 2
            down_steps = steps - up_steps
            up_vals = [
                start_rate + (end_rate - start_rate) * i / max(up_steps - 1, 1)
                for i in range(up_steps)
            ]
            down_vals = [
                end_rate - (end_rate - mid) * i / max(down_steps - 1, 1)
                for i in range(1, down_steps + 1)
            ]
            self._step_values = up_vals + down_vals
        
        self._total_duration = steps * step_duration
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate step ladder traffic.
        
        Yields:
            Current step's target rate.
        """
        self._running = True
        start_time = asyncio.get_event_loop().time()
        
        self._emit(PatternEventType.START, self._step_values[0])
        
        while self._running:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            step_index = int(elapsed / self.step_duration)
            if step_index >= self.steps:
                rate = self._step_values[-1]
            else:
                rate = self._step_values[step_index]
            
            yield rate
            await asyncio.sleep(0.1)
    
    def __repr__(self) -> str:
        return (
            f"StepLadderGenerator("
            f"start_rate={self.start_rate}, "
            f"end_rate={self.end_rate}, "
            f"steps={self.steps}, "
            f"step_duration={self.step_duration}"
            f")"
        )


class ChaosGenerator(TrafficPattern):
    """Generator for chaotic/random traffic patterns.
    
    Produces unpredictable traffic useful for stress testing
    and finding edge cases.
    
    Attributes:
        min_rate: Minimum rate.
        max_rate: Maximum rate.
        change_interval: How often to change rate.
        distribution: Random distribution type.
    """
    
    def __init__(
        self,
        min_rate: float = 10.0,
        max_rate: float = 500.0,
        change_interval: float = 5.0,
        distribution: str = "uniform",
        name: str = "",
    ) -> None:
        """Initialize chaos generator.
        
        Args:
            min_rate: Minimum rate.
            max_rate: Maximum rate.
            change_interval: Seconds between rate changes.
            distribution: 'uniform', 'gaussian', or 'exponential'.
            name: Pattern name.
        """
        super().__init__(name or "Chaos")
        
        if min_rate < 0 or max_rate < 0:
            raise ValueError("Rates must be non-negative")
        if min_rate > max_rate:
            raise ValueError("min_rate must be <= max_rate")
        if change_interval <= 0:
            raise ValueError("change_interval must be positive")
        
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.change_interval = change_interval
        self.distribution = distribution
        
        self._current_rate = min_rate
        self._last_change = 0.0
    
    def _generate_rate(self) -> float:
        """Generate a random rate."""
        if self.distribution == "uniform":
            return random.uniform(self.min_rate, self.max_rate)
        elif self.distribution == "gaussian":
            mean = (self.min_rate + self.max_rate) / 2
            std = (self.max_rate - self.min_rate) / 6
            rate = random.gauss(mean, std)
            return max(self.min_rate, min(self.max_rate, rate))
        elif self.distribution == "exponential":
            scale = (self.max_rate - self.min_rate) / 5
            rate = self.min_rate + random.expovariate(1 / scale)
            return min(rate, self.max_rate)
        else:
            return random.uniform(self.min_rate, self.max_rate)
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate chaotic traffic.
        
        Yields:
            Current random rate.
        """
        self._running = True
        start_time = asyncio.get_event_loop().time()
        self._last_change = start_time
        self._current_rate = self._generate_rate()
        
        self._emit(PatternEventType.START, self._current_rate)
        
        while self._running:
            now = asyncio.get_event_loop().time()
            
            # Change rate at intervals
            if now - self._last_change >= self.change_interval:
                self._current_rate = self._generate_rate()
                self._last_change = now
                self._emit(PatternEventType.SPIKE_START, self._current_rate)
            
            yield self._current_rate
            await asyncio.sleep(0.1)
    
    def __repr__(self) -> str:
        return (
            f"ChaosGenerator("
            f"min_rate={self.min_rate}, "
            f"max_rate={self.max_rate}, "
            f"change_interval={self.change_interval}"
            f")"
        )


class CompositePattern(TrafficPattern):
    """Composite pattern that combines multiple patterns.
    
    Allows sequential or blended composition of patterns for
    complex traffic scenarios.
    
    Attributes:
        patterns: List of (pattern, duration) tuples.
        mode: 'sequential' or 'blend'.
    """
    
    def __init__(
        self,
        patterns: list[tuple[TrafficPattern, float | None]],
        mode: str = "sequential",
        name: str = "",
    ) -> None:
        """Initialize composite pattern.
        
        Args:
            patterns: List of (pattern, duration) tuples.
                     Duration None means use pattern's full duration.
            mode: 'sequential' to run patterns in order,
                  'blend' to average their rates.
            name: Pattern name.
        """
        super().__init__(name or "Composite")
        self.patterns = patterns
        self.mode = mode
    
    async def generate(self) -> AsyncIterator[float]:
        """Generate composite traffic.
        
        Yields:
            Combined rate from constituent patterns.
        """
        self._running = True
        self._emit(PatternEventType.START, 0)
        
        if self.mode == "sequential":
            async for rate in self._generate_sequential():
                if not self._running:
                    break
                yield rate
        else:  # blend
            async for rate in self._generate_blend():
                if not self._running:
                    break
                yield rate
    
    async def _generate_sequential(self) -> AsyncIterator[float]:
        """Generate sequential pattern composition."""
        for pattern, duration in self.patterns:
            if not self._running:
                break
            
            start_time = asyncio.get_event_loop().time()
            
            async for rate in pattern.generate():
                if not self._running:
                    break
                
                if duration is not None:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed >= duration:
                        break
                
                yield rate
    
    async def _generate_blend(self) -> AsyncIterator[float]:
        """Generate blended pattern composition."""
        # Start all patterns
        generators = [p.generate() for p, _ in self.patterns]
        
        while self._running:
            rates = []
            for gen in generators:
                try:
                    rate = await gen.asend(None)
                    rates.append(rate)
                except StopAsyncIteration:
                    pass
            
            if not rates:
                break
            
            # Average the rates
            yield sum(rates) / len(rates)
            await asyncio.sleep(0.1)
    
    def stop(self) -> None:
        """Stop all constituent patterns."""
        self._running = False
        for pattern, _ in self.patterns:
            pattern.stop()
    
    def __repr__(self) -> str:
        return f"CompositePattern(patterns={len(self.patterns)}, mode='{self.mode}')"


# Legacy compatibility - re-export existing generators
from loadtest.generators.constant import ConstantRateGenerator, VariableRateGenerator
from loadtest.generators.ramp import RampGenerator
from loadtest.generators.spike import SpikeGenerator, BurstGenerator as LegacyBurstGenerator

__all__ = [
    "PatternEvent",
    "PatternEventType",
    "TrafficPattern",
    "BurstGenerator",
    "SteadyStateGenerator",
    "CustomCurveGenerator",
    "StepLadderGenerator",
    "ChaosGenerator",
    "CompositePattern",
    # Legacy
    "ConstantRateGenerator",
    "VariableRateGenerator",
    "RampGenerator",
    "SpikeGenerator",
    "LegacyBurstGenerator",
]
