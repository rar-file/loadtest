#!/usr/bin/env python3
"""Quick Start Example for LoadTest.

This example demonstrates the simplest possible load test.
Just run: python quickstart.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path (not needed if loadtest is installed via pip)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.http import HTTPScenario


async def main():
    """Run a simple load test against httpbin.org."""
    print("🚀 LoadTest Quick Start")
    print("=" * 50)
    
    # Create a simple HTTP scenario
    scenario = HTTPScenario(
        name="Get Request",
        method="GET",
        url="https://httpbin.org/get",
    )
    
    # Build the test
    test = (
        LoadTest(
            name="Quick Start Test",
            duration=10,  # 10 seconds
            warmup_duration=1,
            console_output=True,
        )
        .add_scenario(scenario, weight=1)
        .set_pattern(ConstantRateGenerator(rate=2))  # 2 requests/second
    )
    
    print(f"Test: {test.config.name}")
    print(f"Duration: {test.config.duration} seconds")
    print(f"Rate: 2 requests/second")
    print("=" * 50)
    
    try:
        # Run the test
        results = await test.run()
        
        # Print results
        print("\n" + test.report(format="console"))
        
        # Save HTML report
        test.report(format="html", output="quickstart_report.html")
        print("\n📊 HTML report saved to: quickstart_report.html")
        
        return 0 if results.success_rate >= 95 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        test.stop()
        return 130
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(130)
