# Getting Started

## Installation

### Prerequisites

- Python 3.9 or higher
- pip

### Basic Installation

```bash
pip install loadtest
```

### With Web Automation Support

```bash
pip install "loadtest[web]"
playwright install chromium
```

### Development Installation

```bash
git clone https://github.com/example/loadtest.git
cd loadtest
pip install -e ".[dev,web]"
playwright install chromium
```

## Quick Start

### 1. Basic HTTP Load Test

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    # Create test
    test = LoadTest(name="API Test", duration=60)
    
    # Add scenario
    scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://api.example.com/users",
    )
    test.add_scenario(scenario, weight=1)
    
    # Set traffic pattern
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    # Run test
    results = await test.run()
    print(f"Success rate: {results.success_rate}%")

asyncio.run(main())
```

### 2. Dynamic Test Data

```python
from phoney import Phoney

phoney = Phoney()

scenario = HTTPScenario(
    name="Create User",
    method="POST",
    url="https://api.example.com/users",
    data_factory=lambda: {
        "name": phoney.full_name(),
        "email": phoney.email(),
    },
)
```

### 3. Traffic Patterns

```python
from loadtest.generators.ramp import RampGenerator

# Ramp up from 10 to 100 RPS over 5 minutes
test.set_pattern(RampGenerator(
    start_rate=10,
    end_rate=100,
    ramp_duration=300,
))
```

### 4. Generate Reports

```python
# Run test
results = await test.run()

# Generate HTML report
test.report(format="html", output="report.html")

# Print console report
print(test.report(format="console"))
```

## Next Steps

- Learn about [Traffic Patterns](../user-guide/patterns.md)
- Explore [Scenarios](../user-guide/scenarios.md)
- See more [Examples](../examples/basic.md)
