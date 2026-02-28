"""Traffic generators for load testing patterns.

This package provides various traffic pattern generators for creating
different types of load test scenarios.

Available Generators:
    - ConstantRateGenerator: Steady, unchanging rate
    - VariableRateGenerator: Rate varies by waveform
    - RampGenerator: Gradually increase/decrease load
    - SpikeGenerator: Sudden traffic spikes
    - BurstGenerator: Single isolated burst
    - SteadyStateGenerator: Steady rate with jitter
    - CustomCurveGenerator: User-defined rate function
    - StepLadderGenerator: Discrete steps
    - ChaosGenerator: Random/unpredictable patterns
    - CompositePattern: Combine multiple patterns

Deprecated - Use patterns module instead:
    These legacy generators are maintained for backward compatibility.
    New code should use the patterns module which provides enhanced
    functionality.
"""

from __future__ import annotations

# Legacy generators (maintained for backward compatibility)
from loadtest.generators.constant import ConstantRateGenerator, VariableRateGenerator
from loadtest.generators.ramp import RampGenerator
from loadtest.generators.spike import BurstGenerator as LegacyBurstGenerator
from loadtest.generators.spike import SpikeGenerator

# New enhanced patterns
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

__all__ = [
    # Legacy
    "ConstantRateGenerator",
    "VariableRateGenerator",
    "RampGenerator",
    "SpikeGenerator",
    "LegacyBurstGenerator",
    # New patterns
    "BurstGenerator",
    "ChaosGenerator",
    "CompositePattern",
    "CustomCurveGenerator",
    "PatternEvent",
    "PatternEventType",
    "SteadyStateGenerator",
    "StepLadderGenerator",
    "TrafficPattern",
]
