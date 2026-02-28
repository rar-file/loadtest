"""Simple HTTP load test example.

This example demonstrates basic usage of loadtest for generating
HTTP traffic against an endpoint with fake user data.
"""

import random
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.http import HTTPScenario


def create_user_data() -> dict:
    """Generate fake user data for POST requests."""
    names = ["Alice Smith", "Bob Johnson", "Carol White", "David Brown"]
    domains = ["example.com", "test.org", "demo.net"]
    return {
        "name": random.choice(names),
        "email": f"user{random.randint(1, 10000)}@{random.choice(domains)}",
        "role": random.choice(["user", "admin", "editor"]),
    }


async def create_test() -> LoadTest:
    """Create and return a simple HTTP load test configuration."""
    test = LoadTest(
        name="Simple HTTP Load Test",
        duration=30,  # Run for 30 seconds
        warmup_duration=2,
        console_output=True,
    )

    # GET request scenario
    get_scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://httpbin.org/get",
        headers={
            "Accept": "application/json",
            "User-Agent": "LoadTest/0.1.0",
        },
    )

    # POST request scenario with dynamic data
    post_scenario = HTTPScenario(
        name="Create User",
        method="POST",
        url="https://httpbin.org/post",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        data_factory=create_user_data,
    )

    # Add scenarios with different weights
    test.add_scenario(get_scenario, weight=3)
    test.add_scenario(post_scenario, weight=1)

    # Set traffic pattern: 5 requests per second
    test.set_pattern(ConstantRateGenerator(rate=5))

    return test


# Keep main() for running standalone
async def main() -> None:
    """Run the load test directly (for development/testing)."""
    test = await create_test()
    
    print("=" * 60)
    print("Starting Simple HTTP Load Test")
    print("=" * 60)
    print(f"Test: {test.config.name}")
    print(f"Duration: {test.config.duration} seconds")
    print(f"Rate: 5 requests/second")
    print(f"Scenarios: Get Users (weight=3), Create User (weight=1)")
    print("=" * 60)
    print()

    try:
        results = await test.run()
        print()
        print(test.report(format="console"))
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        test.stop()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
