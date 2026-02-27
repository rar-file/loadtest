"""Tests for traffic pattern engine."""

from __future__ import annotations

import asyncio
import math

import pytest

from loadtest.patterns import (
    BurstGenerator,
    ChaosGenerator,
    CompositePattern,
    CustomCurveGenerator,
    PatternEvent,
    PatternEventType,
    SteadyStateGenerator,
    StepLadderGenerator,
    TrafficPattern,
)


class TestPatternEvent:
    """Test pattern events."""
    
    def test_event_creation(self) -> None:
        """Test event creation."""
        event = PatternEvent(
            event_type=PatternEventType.START,
            rate=100.0,
            metadata={"test": "value"},
        )
        
        assert event.event_type == PatternEventType.START
        assert event.rate == 100.0
        assert event.metadata == {"test": "value"}


class TestBurstGenerator:
    """Test burst traffic pattern."""
    
    def test_initialization(self) -> None:
        """Test burst generator initialization."""
        generator = BurstGenerator(
            initial_rate=10.0,
            burst_rate=1000.0,
            burst_duration=30.0,
            delay=60.0,
        )
        
        assert generator.initial_rate == 10.0
        assert generator.burst_rate == 1000.0
        assert generator.burst_duration == 30.0
        assert generator.delay == 60.0
        assert generator.final_rate == 10.0
    
    def test_invalid_rates(self) -> None:
        """Test validation of invalid rates."""
        with pytest.raises(ValueError, match="Rates must be non-negative"):
            BurstGenerator(initial_rate=-10)
        
        with pytest.raises(ValueError, match="Rates must be non-negative"):
            BurstGenerator(burst_rate=-100)
    
    def test_invalid_duration(self) -> None:
        """Test validation of invalid duration."""
        with pytest.raises(ValueError, match="burst_duration must be positive"):
            BurstGenerator(burst_duration=0)
        
        with pytest.raises(ValueError, match="burst_duration must be positive"):
            BurstGenerator(burst_duration=-10)
    
    def test_invalid_delay(self) -> None:
        """Test validation of invalid delay."""
        with pytest.raises(ValueError, match="delay must be non-negative"):
            BurstGenerator(delay=-5)
    
    @pytest.mark.asyncio
    async def test_burst_sequence(self) -> None:
        """Test burst pattern sequence."""
        generator = BurstGenerator(
            initial_rate=10.0,
            burst_rate=500.0,
            burst_duration=0.2,
            delay=0.1,
            final_rate=20.0,
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 10:  # Collect ~1 second of samples
                generator.stop()
        
        # First samples should be initial_rate
        assert rates[0] == 10.0
        
        # Should eventually hit burst rate
        assert 500.0 in rates
        
        # Should end at final_rate
        assert rates[-1] == 20.0
    
    @pytest.mark.asyncio
    async def test_event_emission(self) -> None:
        """Test burst event emission."""
        events = []
        generator = BurstGenerator(
            initial_rate=10.0,
            burst_rate=500.0,
            burst_duration=0.1,
            delay=0.05,
        )
        
        @generator.on(PatternEventType.START)
        def on_start(event):
            events.append(("start", event.rate))
        
        @generator.on(PatternEventType.BURST_START)
        def on_burst_start(event):
            events.append(("burst_start", event.rate))
        
        @generator.on(PatternEventType.BURST_END)
        def on_burst_end(event):
            events.append(("burst_end", event.rate))
        
        async for rate in generator.generate():
            if len(events) >= 3:
                generator.stop()
        
        assert ("start", 10.0) in events
        assert any(e[0] == "burst_start" and e[1] == 500.0 for e in events)


class TestSteadyStateGenerator:
    """Test steady-state traffic pattern with jitter."""
    
    def test_initialization(self) -> None:
        """Test steady-state generator initialization."""
        generator = SteadyStateGenerator(
            target_rate=100.0,
            jitter=0.2,
            jitter_distribution="gaussian",
        )
        
        assert generator.target_rate == 100.0
        assert generator.jitter == 0.2
        assert generator.jitter_distribution == "gaussian"
    
    def test_invalid_target_rate(self) -> None:
        """Test validation of invalid target rate."""
        with pytest.raises(ValueError, match="target_rate must be non-negative"):
            SteadyStateGenerator(target_rate=-50)
    
    def test_invalid_jitter(self) -> None:
        """Test validation of invalid jitter."""
        with pytest.raises(ValueError, match="jitter must be between"):
            SteadyStateGenerator(jitter=-0.1)
        
        with pytest.raises(ValueError, match="jitter must be between"):
            SteadyStateGenerator(jitter=1.5)
    
    def test_invalid_distribution(self) -> None:
        """Test validation of invalid distribution."""
        with pytest.raises(ValueError, match="jitter_distribution must be"):
            SteadyStateGenerator(jitter_distribution="invalid")
    
    @pytest.mark.asyncio
    async def test_rate_with_jitter(self) -> None:
        """Test that rate varies within jitter bounds."""
        generator = SteadyStateGenerator(
            target_rate=100.0,
            jitter=0.2,
            jitter_distribution="uniform",
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 20:
                generator.stop()
        
        # All rates should be within jitter bounds
        min_expected = 100.0 * (1 - 0.2)
        max_expected = 100.0 * (1 + 0.2)
        
        for rate in rates:
            assert min_expected <= rate <= max_expected
            assert rate >= 0  # Never negative
    
    @pytest.mark.asyncio
    async def test_no_jitter(self) -> None:
        """Test that rate is constant with zero jitter."""
        generator = SteadyStateGenerator(
            target_rate=100.0,
            jitter=0.0,
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 10:
                generator.stop()
        
        # All rates should be exactly target_rate
        assert all(r == 100.0 for r in rates)


class TestCustomCurveGenerator:
    """Test custom curve traffic pattern."""
    
    @pytest.mark.asyncio
    async def test_linear_curve(self) -> None:
        """Test linear curve function."""
        generator = CustomCurveGenerator(
            curve_function=lambda t: 10 + t * 10,
            duration=1.0,
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 15:
                generator.stop()
        
        # First rate should be near 10
        assert rates[0] >= 10.0
        
        # Rates should increase
        assert rates[-1] > rates[0]
    
    @pytest.mark.asyncio
    async def test_sine_curve(self) -> None:
        """Test sine wave curve function."""
        generator = CustomCurveGenerator(
            curve_function=lambda t: 100 + 50 * math.sin(t),
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 50:  # Multiple cycles
                generator.stop()
        
        # Should have values near min and max of sine
        assert any(r < 60 for r in rates)  # Near 100-50
        assert any(r > 140 for r in rates)  # Near 100+50


class TestStepLadderGenerator:
    """Test step ladder traffic pattern."""
    
    def test_initialization(self) -> None:
        """Test step ladder generator initialization."""
        generator = StepLadderGenerator(
            start_rate=10.0,
            end_rate=100.0,
            steps=5,
            step_duration=60.0,
            direction="up",
        )
        
        assert generator.start_rate == 10.0
        assert generator.end_rate == 100.0
        assert generator.steps == 5
        assert generator.step_duration == 60.0
        assert generator.direction == "up"
    
    def test_up_direction(self) -> None:
        """Test step values for up direction."""
        generator = StepLadderGenerator(
            start_rate=0.0,
            end_rate=100.0,
            steps=5,
            step_duration=1.0,
            direction="up",
        )
        
        # Should have 5 evenly spaced steps from 0 to 100
        expected = [0.0, 25.0, 50.0, 75.0, 100.0]
        assert generator._step_values == expected
    
    def test_down_direction(self) -> None:
        """Test step values for down direction."""
        generator = StepLadderGenerator(
            start_rate=100.0,
            end_rate=0.0,
            steps=5,
            step_duration=1.0,
            direction="down",
        )
        
        # Should start at end_rate and go down to start_rate
        assert generator._step_values[0] == 0.0
        assert generator._step_values[-1] == 100.0
    
    def test_updown_direction(self) -> None:
        """Test step values for updown direction."""
        generator = StepLadderGenerator(
            start_rate=0.0,
            end_rate=100.0,
            steps=6,
            step_duration=1.0,
            direction="updown",
        )
        
        # Should go up then down - the peak should be near end_rate
        max_value = max(generator._step_values)
        assert max_value >= 90.0  # Near peak
        
        # Should have increasing then decreasing pattern
        up_part = generator._step_values[:len(generator._step_values)//2]
        assert up_part[-1] >= 80.0  # Should reach near peak in first half
    
    def test_invalid_direction(self) -> None:
        """Test validation of invalid direction."""
        with pytest.raises(ValueError, match="direction must be"):
            StepLadderGenerator(direction="sideways")
    
    @pytest.mark.asyncio
    async def test_step_sequence(self) -> None:
        """Test step sequence generation."""
        generator = StepLadderGenerator(
            start_rate=10.0,
            end_rate=50.0,
            steps=3,
            step_duration=0.1,
            direction="up",
        )
        
        rates = []
        timestamps = []
        async for rate in generator.generate():
            rates.append(rate)
            timestamps.append(asyncio.get_event_loop().time())
            if len(rates) >= 20:
                generator.stop()
        
        # Should see the different step values
        unique_rates = sorted(set(rates))
        assert len(unique_rates) >= 2  # At least 2 different steps


class TestChaosGenerator:
    """Test chaotic traffic pattern."""
    
    def test_initialization(self) -> None:
        """Test chaos generator initialization."""
        generator = ChaosGenerator(
            min_rate=10.0,
            max_rate=500.0,
            change_interval=5.0,
            distribution="gaussian",
        )
        
        assert generator.min_rate == 10.0
        assert generator.max_rate == 500.0
        assert generator.change_interval == 5.0
        assert generator.distribution == "gaussian"
    
    def test_invalid_rates(self) -> None:
        """Test validation of invalid rates."""
        with pytest.raises(ValueError, match="Rates must be non-negative"):
            ChaosGenerator(min_rate=-10)
        
        with pytest.raises(ValueError, match="min_rate must be"):
            ChaosGenerator(min_rate=100, max_rate=50)
    
    def test_invalid_change_interval(self) -> None:
        """Test validation of invalid change interval."""
        with pytest.raises(ValueError, match="change_interval must be positive"):
            ChaosGenerator(change_interval=0)
    
    @pytest.mark.asyncio
    async def test_rate_bounds(self) -> None:
        """Test that rates stay within bounds."""
        generator = ChaosGenerator(
            min_rate=50.0,
            max_rate=150.0,
            change_interval=0.05,
            distribution="uniform",
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 30:  # Multiple change intervals
                generator.stop()
        
        # All rates should be within bounds
        for rate in rates:
            assert 50.0 <= rate <= 150.0
    
    @pytest.mark.asyncio
    async def test_rate_changes(self) -> None:
        """Test that rates change over time."""
        generator = ChaosGenerator(
            min_rate=10.0,
            max_rate=100.0,
            change_interval=0.05,
        )
        
        rates = []
        async for rate in generator.generate():
            rates.append(rate)
            if len(rates) >= 20:
                generator.stop()
        
        # Should have some variation
        assert max(rates) > min(rates)


class TestCompositePattern:
    """Test composite traffic pattern."""
    
    @pytest.mark.asyncio
    async def test_sequential_composition(self) -> None:
        """Test sequential pattern composition."""
        pattern1 = BurstGenerator(
            initial_rate=10.0,
            burst_rate=100.0,
            burst_duration=0.1,
            delay=0.05,
        )
        pattern2 = BurstGenerator(
            initial_rate=50.0,
            burst_rate=200.0,
            burst_duration=0.1,
            delay=0.05,
        )
        
        composite = CompositePattern(
            patterns=[(pattern1, 0.2), (pattern2, 0.2)],
            mode="sequential",
        )
        
        rates = []
        async for rate in composite.generate():
            rates.append(rate)
            if len(rates) >= 15:
                composite.stop()
        
        # Should see rates from both patterns
        assert 100.0 in rates or 200.0 in rates
    
    @pytest.mark.asyncio
    async def test_blend_composition(self) -> None:
        """Test blended pattern composition."""
        # Two constant generators for predictable blending
        class ConstantPattern(TrafficPattern):
            def __init__(self, rate):
                super().__init__()
                self.rate = rate
            
            async def generate(self):
                self._running = True
                while self._running:
                    yield self.rate
                    await asyncio.sleep(0.01)
        
        pattern1 = ConstantPattern(100.0)
        pattern2 = ConstantPattern(200.0)
        
        composite = CompositePattern(
            patterns=[(pattern1, None), (pattern2, None)],
            mode="blend",
        )
        
        rates = []
        async for rate in composite.generate():
            rates.append(rate)
            if len(rates) >= 5:
                composite.stop()
        
        # Blended rate should average of the two
        assert all(abs(r - 150.0) < 1 for r in rates)
    
    def test_stop_propagation(self) -> None:
        """Test that stop propagates to child patterns."""
        pattern1 = BurstGenerator()
        pattern2 = BurstGenerator()
        
        composite = CompositePattern(
            patterns=[(pattern1, None), (pattern2, None)],
        )
        
        composite.stop()
        
        assert not pattern1._running
        assert not pattern2._running


class TestEventHandling:
    """Test pattern event handling."""
    
    @pytest.mark.asyncio
    async def test_event_handler_registration(self) -> None:
        """Test event handler registration."""
        generator = BurstGenerator()
        
        @generator.on(PatternEventType.START)
        def handler(event):
            pass
        
        assert handler in generator._event_handlers[PatternEventType.START]
    
    @pytest.mark.asyncio
    async def test_event_handler_decorator_return(self) -> None:
        """Test that decorator returns handler function."""
        generator = BurstGenerator()
        
        @generator.on(PatternEventType.START)
        def my_handler(event):
            return "handled"
        
        assert my_handler(None) == "handled"
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self) -> None:
        """Test multiple handlers for same event."""
        generator = BurstGenerator()
        calls = []
        
        @generator.on(PatternEventType.START)
        def handler1(event):
            calls.append(1)
        
        @generator.on(PatternEventType.START)
        def handler2(event):
            calls.append(2)
        
        # Emit manually
        generator._emit(PatternEventType.START)
        
        assert 1 in calls
        assert 2 in calls
    
    @pytest.mark.asyncio
    async def test_handler_exception_ignored(self) -> None:
        """Test that handler exceptions don't break pattern."""
        generator = BurstGenerator()
        
        @generator.on(PatternEventType.START)
        def bad_handler(event):
            raise ValueError("oops")
        
        # Should not raise
        generator._emit(PatternEventType.START, 100.0)
