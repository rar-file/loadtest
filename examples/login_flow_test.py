"""Multi-step login flow load test example.

This example demonstrates a complex scenario with multiple steps:
1. Register a new user with fake data
2. Login with created credentials
3. Perform authenticated action
4. Logout

This uses the Phoney library for generating realistic user data.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from loadtest import LoadTest
from loadtest.generators.ramp import RampGenerator
from loadtest.scenarios.base import Scenario
from loadtest.scenarios.http import AuthenticatedHTTPScenario, HTTPScenario


class RegistrationLoginScenario(Scenario):
    """Multi-step scenario: Register -> Login -> Action -> Logout.
    
    This scenario simulates a complete user flow:
    1. Register a new user with fake credentials
    2. Login to get authentication token
    3. Access a protected resource
    4. (Optional) Logout
    """
    
    def __init__(self, name: str = "Login Flow", base_url: str = "https://httpbin.org"):
        """Initialize the scenario.
        
        Args:
            name: Scenario name.
            base_url: Base URL for the API.
        """
        super().__init__(name)
        self.base_url = base_url.rstrip("/")
        self._users: list[dict[str, Any]] = []
    
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """Execute the login flow scenario.
        
        Args:
            context: Execution context.
        
        Returns:
            Result dictionary with flow status.
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Step 1: Generate user data using Phoney
            # In production: user_data = self._create_user_with_phoney()
            user_data = self._create_mock_user()
            
            # Step 2: Register user
            # Note: Using httpbin.org/post as a mock registration endpoint
            reg_response = await client.post(
                f"{self.base_url}/post",
                json={
                    "action": "register",
                    "username": user_data["username"],
                    "email": user_data["email"],
                    "password": user_data["password"],
                },
            )
            reg_response.raise_for_status()
            
            # Step 3: Login (mock)
            login_response = await client.post(
                f"{self.base_url}/post",
                json={
                    "action": "login",
                    "email": user_data["email"],
                    "password": user_data["password"],
                },
            )
            login_response.raise_for_status()
            
            # Simulate getting a token
            auth_token = f"mock_token_{user_data['username']}"
            
            # Step 4: Access protected resource
            protected_response = await client.get(
                f"{self.base_url}/bearer",
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            # httpbin /bearer returns 200 if auth header is present
            
            # Step 5: Update user profile
            profile_response = await client.post(
                f"{self.base_url}/post",
                json={
                    "action": "update_profile",
                    "user_id": user_data["username"],
                    "profile": {
                        "full_name": user_data["full_name"],
                        "phone": user_data["phone"],
                        "address": user_data["address"],
                    },
                },
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            profile_response.raise_for_status()
            
            return {
                "success": True,
                "user": user_data["username"],
                "steps_completed": 5,
            }
    
    def _create_mock_user(self) -> dict[str, Any]:
        """Create mock user data.
        
        In production, this would use Phoney:
            from phoney import Phoney
            phoney = Phoney()
            return {
                "username": phoney.username(),
                "email": phoney.email(),
                "password": phoney.password(length=16),
                "full_name": phoney.full_name(),
                "phone": phoney.phone(),
                "address": phoney.address(),
            }
        """
        import random
        import string
        
        first_names = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia"]
        
        first = random.choice(first_names)
        last = random.choice(last_names)
        username = f"{first.lower()}{last.lower()}{random.randint(100, 999)}"
        
        return {
            "username": username,
            "email": f"{username}@example.com",
            "password": "".join(random.choices(
                string.ascii_letters + string.digits + "!@#$%",
                k=16,
            )),
            "full_name": f"{first} {last}",
            "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm'])} St",
        }
    
    def _create_user_with_phoney(self) -> dict[str, Any]:
        """Create user data using Phoney library.
        
        Returns:
            Dictionary with realistic user data.
        """
        # This would work with the actual Phoney library
        return {
            "username": self.phoney.username(),
            "email": self.phoney.email(),
            "password": self.phoney.password(length=16, include_symbols=True),
            "full_name": self.phoney.full_name(),
            "phone": self.phoney.phone(),
            "address": self.phoney.address(),
        }


async def main() -> None:
    """Run the login flow load test."""
    print("=" * 70)
    print("Login Flow Load Test")
    print("=" * 70)
    print()
    print("This test simulates users performing a complete flow:")
    print("  1. Register with fake user data")
    print("  2. Login to obtain session/token")
    print("  3. Access protected resources")
    print("  4. Update profile with realistic data")
    print()
    
    # Create load test with ramp pattern
    test = LoadTest(
        name="Login Flow Load Test",
        duration=60,
        warmup_duration=5,
        console_output=True,
    )
    
    # Add the multi-step scenario
    login_scenario = RegistrationLoginScenario(
        name="Full Login Flow",
        base_url="https://httpbin.org",
    )
    test.add_scenario(login_scenario, weight=1)
    
    # Use a ramp pattern: start low, increase to medium load
    # This simulates users gradually starting to use the system
    test.set_pattern(RampGenerator(
        start_rate=1,      # Start with 1 user flow per second
        end_rate=5,        # Ramp up to 5 flows per second
        ramp_duration=45,  # Over 45 seconds
    ))
    
    print("Test Configuration:")
    print(f"  Duration: {test.config.duration} seconds")
    print(f"  Pattern: Ramp from 1 to 5 flows/second")
    print(f"  Scenario: Full user registration and login flow")
    print()
    print("Starting test in 3 seconds...")
    await asyncio.sleep(3)
    
    try:
        results = await test.run()
        
        print()
        print("=" * 70)
        print("Test Results")
        print("=" * 70)
        
        # Console report
        print(test.report(format="console"))
        
        # HTML report
        test.report(
            format="html",
            output="login_flow_report.html",
            title="Login Flow Load Test Report",
        )
        print("\nDetailed HTML report saved to: login_flow_report.html")
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        test.stop()
    except Exception as e:
        print(f"\nTest failed: {e}")
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
