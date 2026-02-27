"""API load testing example with realistic payloads.

This example demonstrates comprehensive API testing including:
- GET requests with query parameters
- POST requests with JSON payloads
- PUT/PATCH updates
- DELETE requests
- Authentication handling
- Dynamic payload generation with Phoney data
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.generators.spike import SpikeGenerator
from loadtest.scenarios.http import AuthenticatedHTTPScenario, HTTPScenario


class APIScenarioFactory:
    """Factory for creating API test scenarios with realistic data."""
    
    def __init__(self, base_url: str = "https://httpbin.org"):
        """Initialize the factory.
        
        Args:
            base_url: Base URL for the API.
        """
        self.base_url = base_url.rstrip("/")
    
    def create_list_users_scenario(self) -> HTTPScenario:
        """Create a scenario for listing users with pagination."""
        import random
        
        def get_pagination_params() -> dict[str, str]:
            return {
                "page": str(random.randint(1, 10)),
                "limit": str(random.choice([10, 20, 50])),
            }
        
        return HTTPScenario(
            name="List Users",
            method="GET",
            url=f"{self.base_url}/get",
            params_factory=get_pagination_params,
            headers={
                "Accept": "application/json",
                "X-Request-ID": lambda: f"req_{random.randint(10000, 99999)}",
            },
        )
    
    def create_create_user_scenario(self) -> HTTPScenario:
        """Create a scenario for creating users with fake data."""
        import random
        
        def generate_user_payload() -> dict[str, Any]:
            """Generate realistic user creation payload."""
            first_names = ["Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan"]
            last_names = ["Smith", "Johnson", "Williams", "Jones", "Brown", "Davis"]
            domains = ["gmail.com", "yahoo.com", "outlook.com", "company.com"]
            roles = ["user", "admin", "editor", "viewer"]
            departments = ["Engineering", "Sales", "Marketing", "HR", "Finance"]
            
            first = random.choice(first_names)
            last = random.choice(last_names)
            
            return {
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower()}@{random.choice(domains)}",
                "role": random.choice(roles),
                "department": random.choice(departments),
                "phone": f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                "metadata": {
                    "created_via": "api",
                    "signup_source": random.choice(["web", "mobile", "partner"]),
                    "tags": random.sample(["premium", "trial", "enterprise", "startup"], k=random.randint(0, 2)),
                },
            }
        
        return HTTPScenario(
            name="Create User",
            method="POST",
            url=f"{self.base_url}/post",
            headers={"Content-Type": "application/json"},
            data_factory=generate_user_payload,
        )
    
    def create_update_user_scenario(self) -> HTTPScenario:
        """Create a scenario for updating user data."""
        import random
        
        def generate_update_payload() -> dict[str, Any]:
            """Generate user update payload."""
            return {
                "user_id": random.randint(1000, 9999),
                "updates": {
                    "last_login": "2024-01-15T10:30:00Z",
                    "preferences": {
                        "notifications": random.choice([True, False]),
                        "theme": random.choice(["light", "dark", "auto"]),
                        "language": random.choice(["en", "es", "fr", "de"]),
                    },
                    "profile_completion": random.randint(0, 100),
                },
            }
        
        return HTTPScenario(
            name="Update User",
            method="PUT",
            url=f"{self.base_url}/put",
            headers={"Content-Type": "application/json"},
            data_factory=generate_update_payload,
        )
    
    def create_delete_user_scenario(self) -> HTTPScenario:
        """Create a scenario for deleting users."""
        import random
        
        return HTTPScenario(
            name="Delete User",
            method="DELETE",
            url=lambda: f"{self.base_url}/delete?user_id={random.randint(1000, 9999)}",
        )
    
    def create_search_scenario(self) -> HTTPScenario:
        """Create a scenario for search requests."""
        import random
        
        search_terms = [
            "api documentation",
            "user guide",
            "pricing",
            "support",
            "contact",
            "features",
            "integration",
            "webhook",
        ]
        
        def get_search_params() -> dict[str, str]:
            return {
                "q": random.choice(search_terms),
                "limit": str(random.choice([5, 10, 20])),
                "sort": random.choice(["relevance", "date", "name"]),
            }
        
        return HTTPScenario(
            name="Search",
            method="GET",
            url=f"{self.base_url}/get",
            params_factory=get_search_params,
        )
    
    def create_batch_operation_scenario(self) -> HTTPScenario:
        """Create a scenario for batch operations."""
        import random
        
        def generate_batch_payload() -> dict[str, Any]:
            """Generate batch operation payload."""
            operations = []
            for _ in range(random.randint(2, 5)):
                operations.append({
                    "op": random.choice(["create", "update", "delete"]),
                    "id": f"item_{random.randint(1000, 9999)}",
                    "data": {"status": random.choice(["active", "pending", "archived"])},
                })
            
            return {
                "batch_id": f"batch_{random.randint(10000, 99999)}",
                "operations": operations,
                "options": {
                    "continue_on_error": random.choice([True, False]),
                    "transactional": random.choice([True, False]),
                },
            }
        
        return HTTPScenario(
            name="Batch Operation",
            method="POST",
            url=f"{self.base_url}/post",
            headers={"Content-Type": "application/json"},
            data_factory=generate_batch_payload,
        )


async def run_constant_load_test() -> None:
    """Run a constant load API test."""
    print("=" * 70)
    print("API Load Test - Constant Traffic Pattern")
    print("=" * 70)
    print()
    
    factory = APIScenarioFactory()
    
    # Create test
    test = LoadTest(
        name="API Constant Load Test",
        duration=30,
        warmup_duration=3,
        console_output=True,
    )
    
    # Add various API scenarios with different weights
    test.add_scenario(factory.create_list_users_scenario(), weight=5)      # Most common
    test.add_scenario(factory.create_search_scenario(), weight=3)          # Common
    test.add_scenario(factory.create_create_user_scenario(), weight=2)     # Less common
    test.add_scenario(factory.create_update_user_scenario(), weight=1)     # Rare
    test.add_scenario(factory.create_delete_user_scenario(), weight=0.5)   # Very rare
    test.add_scenario(factory.create_batch_operation_scenario(), weight=1) # Occasional
    
    # Constant rate: 10 requests per second
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    print("Test Configuration:")
    print(f"  Duration: {test.config.duration} seconds")
    print(f"  Pattern: Constant 10 requests/second")
    print(f"  Scenarios:")
    print(f"    - List Users (weight: 5)")
    print(f"    - Search (weight: 3)")
    print(f"    - Create User (weight: 2)")
    print(f"    - Update User (weight: 1)")
    print(f"    - Delete User (weight: 0.5)")
    print(f"    - Batch Operation (weight: 1)")
    print()
    
    results = await test.run()
    
    print()
    print(test.report(format="console"))
    
    test.report(
        format="html",
        output="api_constant_report.html",
        title="API Constant Load Test Report",
    )
    print("\nReport saved to: api_constant_report.html")


async def run_spike_test() -> None:
    """Run a spike load API test."""
    print("=" * 70)
    print("API Load Test - Spike Traffic Pattern")
    print("=" * 70)
    print()
    
    factory = APIScenarioFactory()
    
    test = LoadTest(
        name="API Spike Test",
        duration=120,
        warmup_duration=5,
        console_output=True,
    )
    
    # Add scenarios (focus on read operations during spike)
    test.add_scenario(factory.create_list_users_scenario(), weight=4)
    test.add_scenario(factory.create_search_scenario(), weight=3)
    test.add_scenario(factory.create_create_user_scenario(), weight=1)
    
    # Spike pattern: baseline of 5 rps with spikes to 100 rps
    test.set_pattern(SpikeGenerator(
        baseline_rate=5,
        spike_rate=100,
        spike_duration=10,
        interval=30,
        jitter=0.1,
    ))
    
    print("Test Configuration:")
    print(f"  Duration: {test.config.duration} seconds")
    print(f"  Pattern: Spike from 5 to 100 requests/second")
    print(f"  Spike Duration: 10 seconds")
    print(f"  Spike Interval: 30 seconds")
    print()
    
    results = await test.run()
    
    print()
    print(test.report(format="console"))
    
    test.report(
        format="html",
        output="api_spike_report.html",
        title="API Spike Test Report",
    )
    print("\nReport saved to: api_spike_report.html")


async def main() -> None:
    """Run API load tests based on user selection."""
    import argparse
    
    parser = argparse.ArgumentParser(description="API Load Test Examples")
    parser.add_argument(
        "--pattern",
        choices=["constant", "spike", "both"],
        default="both",
        help="Traffic pattern to use",
    )
    
    args = parser.parse_args()
    
    try:
        if args.pattern in ("constant", "both"):
            await run_constant_load_test()
            print("\n" + "=" * 70 + "\n")
        
        if args.pattern in ("spike", "both"):
            await run_spike_test()
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
