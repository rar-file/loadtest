# Basic Examples

## Example 1: Simple HTTP Load Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Simple Test", duration=30)
    
    scenario = HTTPScenario(
        name="Health Check",
        method="GET",
        url="https://api.example.com/health",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    results = await test.run()
    print(f"Success rate: {results.success_rate}%")

asyncio.run(main())
```

## Example 2: POST Request with JSON Body

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="POST Test", duration=60)
    
    scenario = HTTPScenario(
        name="Create Item",
        method="POST",
        url="https://api.example.com/items",
        headers={"Content-Type": "application/json"},
        json={"name": "Test Item", "value": 42},
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=5))
    
    results = await test.run()

asyncio.run(main())
```

## Example 3: Dynamic Data with Phoney

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator
from phoney import Phoney

async def main():
    phoney = Phoney()
    test = LoadTest(name="Dynamic Test", duration=60)
    
    scenario = HTTPScenario(
        name="Register User",
        method="POST",
        url="https://api.example.com/users",
        headers={"Content-Type": "application/json"},
        data_factory=lambda: {
            "name": phoney.full_name(),
            "email": phoney.email(),
            "phone": phoney.phone_number(),
        },
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=2))
    
    results = await test.run()

asyncio.run(main())
```

## Example 4: Ramp Up Pattern

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.ramp import RampGenerator

async def main():
    test = LoadTest(name="Ramp Test", duration=300)
    
    scenario = HTTPScenario(
        name="API Call",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    
    # Start at 10 rps, ramp to 100 rps over 5 minutes
    test.set_pattern(RampGenerator(
        start_rate=10,
        end_rate=100,
        ramp_duration=300,
    ))
    
    results = await test.run()

asyncio.run(main())
```

## Example 5: Spike Testing

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.spike import SpikeGenerator

async def main():
    test = LoadTest(name="Spike Test", duration=600)
    
    scenario = HTTPScenario(
        name="API Call",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    
    # Baseline 20 rps with spikes to 500 rps
    test.set_pattern(SpikeGenerator(
        baseline_rate=20,
        spike_rate=500,
        spike_duration=30,
        interval=300,
    ))
    
    results = await test.run()

asyncio.run(main())
```

## Example 6: Multiple Scenarios with Weights

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Multi-Scenario", duration=120)
    
    # Read-heavy workload (80% reads, 20% writes)
    read_scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://api.example.com/users",
    )
    
    write_scenario = HTTPScenario(
        name="Create User",
        method="POST",
        url="https://api.example.com/users",
        json={"name": "Test"},
    )
    
    test.add_scenario(read_scenario, weight=4)   # 80%
    test.add_scenario(write_scenario, weight=1)  # 20%
    
    test.set_pattern(ConstantRateGenerator(rate=50))
    
    results = await test.run()

asyncio.run(main())
```

## Example 7: HTML Report Generation

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Report Test", duration=60)
    
    scenario = HTTPScenario(
        name="API",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=20))
    
    results = await test.run()
    
    # Generate HTML report
    test.report(format="html", output="report.html")
    print("Report saved to report.html")

asyncio.run(main())
```

## Example 8: Console Report

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Console Test", duration=30, console_output=True)
    
    scenario = HTTPScenario(
        name="API",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    results = await test.run()
    
    # Print console report
    print(test.report(format="console"))

asyncio.run(main())
```

## Example 9: Custom Headers and Authentication

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Auth Test", duration=60)
    
    scenario = HTTPScenario(
        name="Protected Endpoint",
        method="GET",
        url="https://api.example.com/protected",
        headers={
            "Authorization": "Bearer your-token-here",
            "X-API-Key": "your-api-key",
            "Accept": "application/json",
        },
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=5))
    
    results = await test.run()

asyncio.run(main())
```

## Example 10: Query Parameters

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator
from phoney import Phoney

phoney = Phoney()

async def main():
    test = LoadTest(name="Query Test", duration=60)
    
    scenario = HTTPScenario(
        name="Search",
        method="GET",
        url="https://api.example.com/search",
        params_factory=lambda: {"q": phoney.word(), "limit": 10},
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=15))
    
    results = await test.run()

asyncio.run(main())
```

## Example 11: Response Validation

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Validation Test", duration=60)
    
    class ValidatedScenario(HTTPScenario):
        async def execute(self, context):
            response = await super().execute(context)
            
            # Validate response
            if response.status_code == 200:
                data = response.json()
                if "id" not in data:
                    raise ValueError("Response missing 'id' field")
            
            return response
    
    scenario = ValidatedScenario(
        name="Validated API",
        method="GET",
        url="https://api.example.com/users/1",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    results = await test.run()

asyncio.run(main())
```

## Example 12: Web Scenario with Playwright

```python
import asyncio
from loadtest.scenarios.web import WebScenario
from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator

class LoginScenario(WebScenario):
    async def execute(self, context):
        page = context["page"]
        
        # Navigate
        await page.goto("https://example.com/login")
        
        # Fill form
        await page.fill("#username", self.phoney.email())
        await page.fill("#password", "TestPassword123!")
        
        # Submit
        await page.click("#submit")
        
        # Wait for navigation
        await page.wait_for_url("**/dashboard")
        
        return {"status": "success"}

async def main():
    test = LoadTest(name="Web Test", duration=60)
    
    scenario = LoginScenario(name="User Login")
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=2))
    
    results = await test.run()

asyncio.run(main())
```

## Example 13: Custom Metrics

```python
import asyncio
import time
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

class MetricScenario(HTTPScenario):
    async def execute(self, context):
        start = time.time()
        
        response = await super().execute(context)
        
        # Record custom metric
        metrics = context.get("metrics")
        if metrics:
            metrics.record("custom_latency", time.time() - start)
            metrics.record("response_size", len(response.content))
        
        return response

async def main():
    test = LoadTest(name="Metrics Test", duration=60)
    
    scenario = MetricScenario(
        name="API",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    results = await test.run()
    
    # Access custom metrics
    stats = test.metrics.get_statistics()
    print(stats)

asyncio.run(main())
```

## Example 14: Method Chaining

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    # Build test using method chaining
    test = (
        LoadTest(name="Chained Test", duration=60)
        .add_scenario(
            HTTPScenario(name="GET", method="GET", url="https://api.example.com/get"),
            weight=3
        )
        .add_scenario(
            HTTPScenario(name="POST", method="POST", url="https://api.example.com/post"),
            weight=1
        )
        .set_pattern(ConstantRateGenerator(rate=20))
    )
    
    results = await test.run()
    print(f"Total requests: {results.total_requests}")

asyncio.run(main())
```

## Example 15: Graceful Shutdown

```python
import asyncio
import signal
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    test = LoadTest(name="Long Test", duration=3600)  # 1 hour
    
    scenario = HTTPScenario(
        name="API",
        method="GET",
        url="https://api.example.com/data",
    )
    
    test.add_scenario(scenario, weight=1)
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    # Handle shutdown signals
    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        test.stop()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        results = await test.run()
        print(f"Test completed. Success rate: {results.success_rate}%")
    except asyncio.CancelledError:
        print("Test was cancelled")

asyncio.run(main())
```
