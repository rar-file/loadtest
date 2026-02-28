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


async def create_test() -> LoadTest:
    """Create a simple load test configuration (for CLI/Docker usage)."""
    scenario = HTTPScenario(
        name="Get Request",
        method="GET",
        url="https://httpbin.org/get",
    )

    return (
        LoadTest(
            name="Quick Start Test",
            duration=10,  # 10 seconds
            warmup_duration=1,
            console_output=True,
        )
        .add_scenario(scenario, weight=1)
        .set_pattern(ConstantRateGenerator(rate=2))  # 2 requests/second
    )


async def main() -> int:
    """Run a simple load test against httpbin.org (for standalone execution)."""
    print("🚀 LoadTest Quick Start")
    print("=" * 50)

    test = await create_test()

    print(f"Test: {test.config.name}")
    print(f"Duration: {test.config.duration} seconds")
    print(f"Rate: 2 requests/second")
    print("=" * 50)

    try:
        results = await test.run()
        print("\n" + test.report(format="console"))
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
