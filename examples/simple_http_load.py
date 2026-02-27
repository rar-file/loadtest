"""Simple HTTP load test example.

This example demonstrates basic usage of loadtest for generating
HTTP traffic against an endpoint with fake user data.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.http import HTTPScenario


async def main() -> None:
    """Run a simple HTTP load test."""
    # Create a load test
    test = LoadTest(
        name="Simple HTTP Load Test",
        duration=30,  # Run for 30 seconds
        warmup_duration=2,
        console_output=True,
    )
    
    # Define HTTP scenarios with Phoney-generated data
    # Scenario 1: GET request to fetch users
    get_scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://httpbin.org/get",
        headers={
            "Accept": "application/json",
            "User-Agent": "LoadTest/0.1.0",
        },
    )
    
    # Scenario 2: POST request with dynamic data
    # Note: httpbin.org/post echoes back the posted data
    def create_user_data() -> dict:
        """Generate fake user data for POST requests."""
        # This would use phoney in production:
        # from phoney import Phoney
        # phoney = Phoney()
        # return {
        #     "name": phoney.full_name(),
        #     "email": phoney.email(),
        #     "phone": phoney.phone(),
        # }
        import random
        names = ["Alice Smith", "Bob Johnson", "Carol White", "David Brown"]
        domains = ["example.com", "test.org", "demo.net"]
        return {
            "name": random.choice(names),
            "email": f"user{random.randint(1, 10000)}@{random.choice(domains)}",
            "role": random.choice(["user", "admin", "editor"]),
        }
    
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
    # GET requests happen 3x more frequently than POST
    test.add_scenario(get_scenario, weight=3)
    test.add_scenario(post_scenario, weight=1)
    
    # Set traffic pattern: 5 requests per second
    test.set_pattern(ConstantRateGenerator(rate=5))
    
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
        # Run the test
        results = await test.run()
        
        print()
        print("=" * 60)
        print("Test Complete!")
        print("=" * 60)
        
        # Print console report
        print(test.report(format="console"))
        
        # Generate HTML report
        html_report = test.report(
            format="html",
            output="simple_http_report.html",
            title="Simple HTTP Load Test Report",
        )
        print(f"\nHTML report saved to: simple_http_report.html")
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        test.stop()
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        raise


if __name__ == "__main__":
    # Check if we should use a mock server for testing
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        print("Running with mock server...")
        # Import and start mock server
        sys.path.insert(0, str(Path(__file__).parent.parent / "tests" / "fixtures"))
        # Mock server code would go here
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
