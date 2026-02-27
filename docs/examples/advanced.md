# Advanced Examples

## Example 16: E-commerce Load Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.ramp import RampGenerator
from phoney import Phoney

phoney = Phoney()

async def main():
    test = LoadTest(name="E-commerce Load Test", duration=600)
    
    # Browse products
    browse = HTTPScenario(
        name="Browse Products",
        method="GET",
        url="https://api.shop.example.com/products",
        params_factory=lambda: {"category": phoney.random_element(["electronics", "clothing", "home"])},
    )
    
    # View product details
    view = HTTPScenario(
        name="View Product",
        method="GET",
        url_factory=lambda: f"https://api.shop.example.com/products/{phoney.random_int(1, 1000)}",
    )
    
    # Add to cart
    add_cart = HTTPScenario(
        name="Add to Cart",
        method="POST",
        url="https://api.shop.example.com/cart/items",
        json_factory=lambda: {
            "product_id": phoney.random_int(1, 1000),
            "quantity": phoney.random_int(1, 5),
        },
    )
    
    # Checkout
    checkout = HTTPScenario(
        name="Checkout",
        method="POST",
        url="https://api.shop.example.com/checkout",
        json_factory=lambda: {
            "email": phoney.email(),
            "shipping_address": phoney.street_address(),
            "payment_method": "card",
        },
    )
    
    # Add scenarios with realistic weights (browse-heavy)
    test.add_scenario(browse, weight=50)
    test.add_scenario(view, weight=30)
    test.add_scenario(add_cart, weight=15)
    test.add_scenario(checkout, weight=5)
    
    # Ramp up over 10 minutes
    test.set_pattern(RampGenerator(
        start_rate=10,
        end_rate=200,
        ramp_duration=600,
    ))
    
    results = await test.run()
    test.report(format="html", output="ecommerce_report.html")

asyncio.run(main())
```

## Example 17: API Gateway Stress Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.spike import SpikeGenerator

async def main():
    test = LoadTest(name="Gateway Stress Test", duration=1800)
    
    # Test various endpoints through gateway
    scenarios = [
        HTTPScenario("Users API", "GET", "https://gateway.example.com/users"),
        HTTPScenario("Orders API", "GET", "https://gateway.example.com/orders"),
        HTTPScenario("Inventory API", "GET", "https://gateway.example.com/inventory"),
        HTTPScenario("Payments API", "GET", "https://gateway.example.com/payments"),
    ]
    
    for scenario in scenarios:
        test.add_scenario(scenario, weight=1)
    
    # Normal traffic with extreme spikes
    test.set_pattern(SpikeGenerator(
        baseline_rate=100,
        spike_rate=5000,
        spike_duration=60,
        interval=300,
    ))
    
    results = await test.run()
    print(f"Max RPS achieved: {results.metrics.get_statistics().get('max_rps', 0)}")

asyncio.run(main())
```

## Example 18: Authentication Flow Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator
from phoney import Phoney

phoney = Phoney()

class AuthFlow:
    """Simulate complete authentication flows."""
    
    @staticmethod
    def create_register_scenario():
        return HTTPScenario(
            name="Register",
            method="POST",
            url="https://auth.example.com/register",
            json_factory=lambda: {
                "email": phoney.email(),
                "password": phoney.password(),
                "name": phoney.full_name(),
            },
        )
    
    @staticmethod
    def create_login_scenario():
        # In real scenario, use previously registered credentials
        return HTTPScenario(
            name="Login",
            method="POST",
            url="https://auth.example.com/login",
            json_factory=lambda: {
                "email": phoney.email(),
                "password": "TestPassword123!",
            },
        )
    
    @staticmethod
    def create_refresh_scenario():
        return HTTPScenario(
            name="Token Refresh",
            method="POST",
            url="https://auth.example.com/refresh",
            headers={"Authorization": "Bearer valid-refresh-token"},
        )

async def main():
    test = LoadTest(name="Auth Flow Test", duration=300)
    
    test.add_scenario(AuthFlow.create_register_scenario(), weight=10)
    test.add_scenario(AuthFlow.create_login_scenario(), weight=60)
    test.add_scenario(AuthFlow.create_refresh_scenario(), weight=30)
    
    test.set_pattern(ConstantRateGenerator(rate=20))
    
    results = await test.run()

asyncio.run(main())
```

## Example 19: WebSocket Load Test

```python
import asyncio
import websockets
from loadtest.scenarios.base import Scenario
from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from phoney import Phoney

phoney = Phoney()

class WebSocketScenario(Scenario):
    """WebSocket scenario for real-time applications."""
    
    async def execute(self, context):
        uri = "wss://realtime.example.com/ws"
        
        async with websockets.connect(uri) as websocket:
            # Send connection message
            await websocket.send('{"type": "connect"}')
            
            # Send random messages
            for _ in range(5):
                message = {
                    "type": "message",
                    "content": phoney.sentence(),
                }
                await websocket.send(json.dumps(message))
                
                # Wait for response
                response = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=5.0
                )
            
            return {"status": "success", "messages_sent": 5}

async def main():
    test = LoadTest(name="WebSocket Test", duration=60)
    
    scenario = WebSocketScenario(name="Chat Messages")
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=5))
    
    results = await test.run()

asyncio.run(main())
```

## Example 20: GraphQL API Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.ramp import RampGenerator
from phoney import Phoney

phoney = Phoney()

class GraphQLScenario(HTTPScenario):
    """GraphQL-specific scenario with query handling."""
    
    def __init__(self, name, query, variables_factory=None, **kwargs):
        super().__init__(
            name=name,
            method="POST",
            headers={"Content-Type": "application/json"},
            **kwargs
        )
        self.query = query
        self.variables_factory = variables_factory
    
    async def execute(self, context):
        self.json = {
            "query": self.query,
            "variables": self.variables_factory() if self.variables_factory else {},
        }
        return await super().execute(context)

async def main():
    test = LoadTest(name="GraphQL Load Test", duration=300)
    
    # Query scenario
    users_query = """
    query GetUsers($limit: Int!) {
        users(limit: $limit) {
            id
            name
            email
        }
    }
    """
    
    users_scenario = GraphQLScenario(
        name="Get Users",
        url="https://graphql.example.com/query",
        query=users_query,
        variables_factory=lambda: {"limit": phoney.random_int(10, 100)},
    )
    
    # Mutation scenario
    create_mutation = """
    mutation CreateUser($name: String!, $email: String!) {
        createUser(name: $name, email: $email) {
            id
            name
        }
    }
    """
    
    create_scenario = GraphQLScenario(
        name="Create User",
        url="https://graphql.example.com/query",
        query=create_mutation,
        variables_factory=lambda: {
            "name": phoney.full_name(),
            "email": phoney.email(),
        },
    )
    
    test.add_scenario(users_scenario, weight=3)
    test.add_scenario(create_scenario, weight=1)
    
    test.set_pattern(RampGenerator(
        start_rate=10,
        end_rate=100,
        ramp_duration=300,
    ))
    
    results = await test.run()

asyncio.run(main())
```

## Example 21: Multi-Region Load Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

REGIONS = {
    "us-east": "https://us-east.api.example.com",
    "us-west": "https://us-west.api.example.com",
    "eu-west": "https://eu-west.api.example.com",
    "ap-south": "https://ap-south.api.example.com",
}

async def test_region(region, base_url, duration=300):
    """Test a specific region."""
    test = LoadTest(name=f"{region} Region Test", duration=duration)
    
    scenario = HTTPScenario(
        name=f"{region} API",
        method="GET",
        url=f"{base_url}/health",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=50))
    
    results = await test.run()
    return {
        "region": region,
        "success_rate": results.success_rate,
        "avg_response_time": results.metrics.get_statistics().get("mean_response_time", 0),
    }

async def main():
    # Run tests for all regions concurrently
    tasks = [
        test_region(region, url)
        for region, url in REGIONS.items()
    ]
    
    results = await asyncio.gather(*tasks)
    
    print("\n=== Multi-Region Results ===")
    for result in results:
        print(f"{result['region']}: {result['success_rate']:.1f}% success, "
              f"{result['avg_response_time']:.3f}s avg response")

asyncio.run(main())
```

## Example 22: Database-Backed Session Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator
from phoney import Phoney
import aiohttp

phoney = Phoney()

class SessionScenario(HTTPScenario):
    """Scenario that maintains session state across requests."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_cookie = None
    
    async def execute(self, context):
        session = context.get("session")
        
        # First request - login
        login_response = await session.post(
            "https://api.example.com/login",
            json={"email": phoney.email(), "password": "test123"}
        )
        
        # Extract session cookie
        self.session_cookie = login_response.cookies.get("session_id")
        
        # Make authenticated requests
        async with session.get(
            "https://api.example.com/profile",
            cookies={"session_id": self.session_cookie}
        ) as response:
            return response

async def main():
    test = LoadTest(name="Session Test", duration=120)
    
    scenario = SessionScenario(
        name="User Session",
        method="GET",
        url="https://api.example.com/dashboard",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    # Create shared session
    async with aiohttp.ClientSession() as session:
        test._shared_session = session
        results = await test.run()

asyncio.run(main())
```

## Example 23: Custom Metrics and Alerting

```python
import asyncio
import time
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

class MetricScenario(HTTPScenario):
    """Scenario with custom metrics and alerting."""
    
    async def execute(self, context):
        start = time.time()
        
        response = await super().execute(context)
        
        metrics = context.get("metrics")
        duration = time.time() - start
        
        # Record custom metrics
        if metrics:
            metrics.record("request_latency", duration)
            metrics.record("response_size", len(response.content))
            
            # Error rate by status code
            if response.status_code >= 500:
                metrics.increment("server_errors")
            elif response.status_code == 429:
                metrics.increment("rate_limited")
            
            # Alert on high latency
            if duration > 1.0:
                metrics.increment("slow_requests")
        
        return response

async def main():
    test = LoadTest(name="Metrics Test", duration=300, console_output=True)
    
    scenario = MetricScenario(
        name="API",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=50))
    
    results = await test.run()
    
    # Print custom metrics
    stats = test.metrics.get_statistics()
    print(f"\nCustom Metrics:")
    print(f"  Slow requests (>1s): {stats.get('slow_requests', 0)}")
    print(f"  Server errors: {stats.get('server_errors', 0)}")
    print(f"  Rate limited: {stats.get('rate_limited', 0)}")

asyncio.run(main())
```

## Example 24: CI/CD Integration Test

```python
import asyncio
import sys
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def run_ci_test():
    """Run load test in CI/CD pipeline with pass/fail criteria."""
    
    test = LoadTest(name="CI Load Test", duration=60, console_output=True)
    
    # Critical endpoints
    endpoints = [
        ("Health", "GET", "/health"),
        ("Users", "GET", "/api/users"),
        ("Orders", "GET", "/api/orders"),
    ]
    
    for name, method, path in endpoints:
        scenario = HTTPScenario(
            name=name,
            method=method,
            url=f"https://api.example.com{path}",
        )
        test.add_scenario(scenario, weight=1)
    
    test.set_pattern(ConstantRateGenerator(rate=30))
    
    results = await test.run()
    stats = results.metrics.get_statistics()
    
    # Define pass criteria
    passes = True
    checks = []
    
    # Check 1: Success rate > 99%
    success_rate = results.success_rate
    checks.append(("Success Rate > 99%", success_rate > 99, f"{success_rate:.2f}%"))
    
    # Check 2: P95 latency < 500ms
    p95 = stats.get("p95_response_time", 0) * 1000  # Convert to ms
    checks.append(("P95 Latency < 500ms", p95 < 500, f"{p95:.2f}ms"))
    
    # Check 3: Error rate < 1%
    error_rate = 100 - success_rate
    checks.append(("Error Rate < 1%", error_rate < 1, f"{error_rate:.2f}%"))
    
    # Print results
    print("\n" + "=" * 60)
    print("CI/CD Load Test Results")
    print("=" * 60)
    
    for check_name, passed, value in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status} ({value})")
        if not passed:
            passes = False
    
    print("=" * 60)
    
    # Exit with appropriate code
    if passes:
        print("✅ All checks passed!")
        return 0
    else:
        print("❌ Some checks failed!")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(run_ci_test())
    sys.exit(exit_code)
```
