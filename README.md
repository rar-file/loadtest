# LoadTest

[![CI](https://github.com/rar-file/loadtest/actions/workflows/ci.yml/badge.svg)](https://github.com/rar-file/loadtest/actions/workflows/ci.yml)
[![Python versions](https://img.shields.io/pypi/pyversions/loadtest.svg)](https://pypi.org/project/loadtest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 🚀 Modern, async-first load testing framework for Python

LoadTest is a synthetic traffic generator designed for realistic load testing of web applications. It features an intuitive API, multiple traffic patterns, and comprehensive reporting.

## Features

- **🎯 Simple API** - Intuitive builder pattern for creating tests
- **⚡ Async-First** - Built on asyncio for high concurrency
- **📊 Rich Reports** - HTML reports with interactive charts
- **🔄 Multiple Patterns** - Constant, ramp, spike, burst, and custom patterns
- **🌐 HTTP/2 Support** - Full HTTP/1.1 and HTTP/2 via httpx
- **🔌 WebSocket Ready** - Built-in WebSocket scenario support
- **🧪 Realistic Data** - Integration with Phoney for realistic test data

## Installation

```bash
# Basic installation
pip install loadtest

# With web automation support (Playwright)
pip install "loadtest[web]"

# Development installation
pip install "loadtest[dev]"
```

## Quick Start

Create a test file (`test.py`):

```python
from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.http import HTTPScenario

async def create_test():
    # Define an HTTP scenario
    scenario = HTTPScenario(
        name="Get Users",
        method="GET",
        url="https://httpbin.org/get",
    )
    
    # Build and return the test
    return (
        LoadTest(name="API Test", duration=30)
        .add_scenario(scenario, weight=1)
        .set_pattern(ConstantRateGenerator(rate=10))  # 10 req/s
    )
```

Run it:

```bash
loadtest run test.py
```

Generate an HTML report:

```bash
loadtest run test.py --output report.html
```

## Examples

### HTTP Load Test with POST Data

```python
from loadtest import LoadTest
from loadtest.generators.ramp import RampGenerator
from loadtest.scenarios.http import HTTPScenario

async def create_test():
    # POST scenario with dynamic data
    create_scenario = HTTPScenario(
        name="Create User",
        method="POST",
        url="https://httpbin.org/post",
        data_factory=lambda: {
            "name": "John Doe",
            "email": "john@example.com",
        },
    )
    
    # Ramp up from 5 to 50 req/s over 60 seconds
    return (
        LoadTest(name="Ramp Test", duration=60)
        .add_scenario(create_scenario)
        .set_pattern(RampGenerator(start_rate=5, end_rate=50, duration=60))
    )
```

### Authenticated API Testing

```python
from loadtest.scenarios.http import AuthenticatedHTTPScenario

async def create_test():
    scenario = AuthenticatedHTTPScenario(
        name="API Request",
        method="GET",
        url="https://api.example.com/data",
        auth_token="your-api-token",
        auth_prefix="Bearer ",
    )
    
    return LoadTest(name="Auth Test", duration=60).add_scenario(scenario)
```

### Using Advanced Traffic Patterns

```python
from loadtest.patterns import BurstGenerator, SteadyStateGenerator, StepLadderGenerator

async def create_test():
    from loadtest import LoadTest
    from loadtest.scenarios.http import HTTPScenario
    
    scenario = HTTPScenario(method="GET", url="https://api.example.com/health")
    
    # Burst pattern: sudden spike after delay
    pattern = BurstGenerator(
        initial_rate=10,
        burst_rate=1000,
        burst_duration=30,
        delay=60,
    )
    
    # Or steady state with jitter
    # pattern = SteadyStateGenerator(target_rate=100, jitter=0.1)
    
    # Or step ladder for capacity testing
    # pattern = StepLadderGenerator(
    #     start_rate=10, end_rate=100, steps=5, step_duration=60
    # )
    
    return LoadTest(name="Pattern Test", duration=120).add_scenario(scenario).set_pattern(pattern)
```

## CLI Usage

```bash
# Show version
loadtest version

# Show available components
loadtest info

# Show quick start guide
loadtest quickstart

# Run a test
loadtest run test.py

# Run with custom duration
loadtest run test.py --duration 120

# Generate HTML report
loadtest run test.py --output report.html
```

## Docker Usage

```bash
# Build the image
docker build -t loadtest .

# Run a test
docker run -v $(pwd)/examples:/app/tests loadtest run /app/tests/quickstart.py

# Using docker-compose
docker-compose up loadtest
```

## Project Structure

```
loadtest/
├── examples/           # Example test scenarios
│   ├── quickstart.py   # Simplest example
│   ├── simple_http_load.py
│   └── api_load_test.py
├── src/loadtest/       # Main source code
│   ├── core.py         # LoadTest class
│   ├── scenarios/      # Test scenarios
│   │   ├── http.py     # HTTP scenarios
│   │   └── websocket.py
│   ├── generators/     # Traffic generators
│   │   ├── constant.py
│   │   ├── ramp.py
│   │   └── spike.py
│   ├── patterns.py     # New pattern system
│   └── reports/        # Report generators
│       └── html.py
├── tests/              # Test suite
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Development

```bash
# Clone the repository
git clone https://github.com/example/loadtest.git
cd loadtest

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/loadtest --cov-report=html

# Format code
black src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

## Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Configuration Reference

### LoadTest Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | "Load Test" | Test name for reports |
| `duration` | float | 60.0 | Test duration in seconds |
| `warmup_duration` | float | 5.0 | Warmup period before recording |
| `max_concurrent` | int | 1000 | Maximum concurrent requests |
| `console_output` | bool | True | Show real-time console output |

### Traffic Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| `ConstantRateGenerator` | Steady rate | Baseline testing |
| `RampGenerator` | Gradual increase/decrease | Finding capacity limits |
| `SpikeGenerator` | Sudden traffic spikes | Stress testing |
| `BurstGenerator` | Single isolated burst | Spike tolerance testing |
| `SteadyStateGenerator` | Rate with jitter | Realistic traffic |
| `StepLadderGenerator` | Discrete steps | Capacity planning |
| `ChaosGenerator` | Random patterns | Resilience testing |

## Troubleshooting

### Import Errors

If you get import errors, ensure you're using the correct import paths:

```python
# Correct
from loadtest import LoadTest
from loadtest.generators.constant import ConstantRateGenerator
from loadtest.scenarios.http import HTTPScenario
```

### Tests Failing

Make sure all dependencies are installed:

```bash
pip install -e ".[dev]"
pytest -v
```

### Async Issues

Remember that your `create_test()` function should be async:

```python
async def create_test():  # Note: async
    return LoadTest(...)
```

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Support

- 📖 [Documentation](https://github.com/example/loadtest/tree/main/docs)
- 🐛 [Issue Tracker](https://github.com/example/loadtest/issues)
- 💬 [Discussions](https://github.com/example/loadtest/discussions)
