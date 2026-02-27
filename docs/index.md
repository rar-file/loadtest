# LoadTest

[![CI](https://github.com/example/loadtest/actions/workflows/ci.yml/badge.svg)](https://github.com/example/loadtest/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/example/loadtest/branch/main/graph/badge.svg)](https://codecov.io/gh/example/loadtest)
[![PyPI](https://img.shields.io/pypi/v/loadtest.svg)](https://pypi.org/project/loadtest/)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://loadtest.readthedocs.io)

**A modern, async-first synthetic traffic generator for load testing web applications.**

## Features

- **Async-first architecture** - High concurrency with minimal resource usage
- **Realistic user data** - Integration with Phoney for authentic test data
- **Multiple scenario types** - HTTP API testing and browser automation (Playwright)
- **Traffic patterns** - Constant rate, ramp up/down, and spike testing
- **Rich metrics** - Response times, throughput, error rates, percentiles
- **HTML reports** - Beautiful, interactive test reports
- **Rich CLI output** - Real-time progress and results display
- **Extensible** - Easy to add custom scenarios and generators

## Installation

```bash
pip install loadtest
```

With web automation support:

```bash
pip install "loadtest[web]"  # Includes Playwright
```

## Quick Start

```python
import asyncio
from loadtest import LoadTest
from loadtest.scenarios.http import HTTPScenario
from loadtest.generators.constant import ConstantRateGenerator

async def main():
    # Create a load test
    test = LoadTest(name="API Load Test", duration=60)
    
    # Define an HTTP scenario
    scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://api.example.com/users",
    )
    
    # Add scenario to test
    test.add_scenario(scenario, weight=1)
    
    # Set traffic pattern: 10 requests per second
    test.set_pattern(ConstantRateGenerator(rate=10))
    
    # Run the test
    results = await test.run()
    
    # Generate report
    test.report(format="html", output="report.html")

asyncio.run(main())
```

## Documentation

- [Getting Started](getting-started/quickstart.md)
- [User Guide](user-guide/core-concepts.md)
- [API Reference](api/core.md)
- [Examples](examples/basic.md)

## Traffic Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Constant** | Steady rate of requests | Baseline performance testing |
| **Ramp** | Gradually increase/decrease | Finding breaking points |
| **Spike** | Sudden traffic bursts | Testing auto-scaling |

## Architecture

```mermaid
graph TB
    A[LoadTest Orchestrator] --> B[Traffic Generator]
    A --> C[Scenario Manager]
    A --> D[Metrics Collector]
    B --> E[Constant Rate]
    B --> F[Ramp Pattern]
    B --> G[Spike Pattern]
    C --> H[HTTP Scenario]
    C --> I[Web Scenario]
    C --> J[Custom Scenario]
    D --> K[Response Times]
    D --> L[Throughput]
    D --> M[Error Rates]
    K --> N[Report Generator]
    L --> N
    M --> N
```

## Contributing

We welcome contributions! See [CONTRIBUTING.md](https://github.com/example/loadtest/blob/main/CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/example/loadtest/blob/main/LICENSE) file for details.
