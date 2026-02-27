# LoadTest

[![CI](https://github.com/rar-file/loadtest/actions/workflows/ci.yml/badge.svg)](https://github.com/rar-file/loadtest/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/loadtest.svg)](https://badge.fury.io/py/loadtest)
[![Python versions](https://img.shields.io/pypi/pyversions/loadtest.svg)](https://pypi.org/project/loadtest/)

> Enterprise-grade synthetic traffic generator for load testing

LoadTest is a modern load testing framework designed for realistic traffic simulation. It supports multiple protocols, user behavior modeling, and distributed load generation.

## Features

### Protocol Support
- HTTP/1.1, HTTP/2
- WebSocket
- GraphQL
- gRPC (coming soon)
- HTTP/3 (coming soon)

### Traffic Patterns
- **Steady**: Constant load
- **Ramp**: Gradual increase
- **Spike**: Sudden burst
- **Burst**: Repeated spikes
- **Wave**: Sinusoidal pattern
- **Step**: Step-wise increase

### User Simulation
- Realistic think times
- Session-based workflows
- Cookie/state management
- Concurrent user scenarios

### Metrics & Reporting
- Real-time dashboard
- Prometheus export
- Statistical analysis
- A/B test comparisons

## Quick Start

```bash
pip install loadtest
```

Create a test scenario:

```python
# test_scenario.py
from loadtest import TestBuilder, Scenario

scenario = (
    TestBuilder()
    .target("https://api.example.com")
    .pattern("ramp", target_rps=1000, duration=300)
    .scenario("login_flow")
    .users(concurrent=100)
    .build()
)

scenario.run()
```

Run it:

```bash
loadtest run test_scenario.py
```

## Example Scenarios

### E-commerce Checkout
```python
from loadtest import HttpClient, scenario

@scenario
async def checkout_flow(client: HttpClient):
    # Browse products
    await client.get("/products")
    await client.think(2, 5)  # Think 2-5 seconds
    
    # Add to cart
    await client.post("/cart", json={"product_id": 123})
    await client.think(1, 3)
    
    # Checkout
    await client.post("/checkout", json={
        "payment": "visa",
        "shipping": "express"
    })
```

### API Load Test
```python
from loadtest import TestBuilder

test = (
    TestBuilder()
    .target("https://api.example.com")
    .headers({"Authorization": "Bearer ${TOKEN}"})
    .pattern("spike", 
        target_rps=5000,
        duration=60,
        spike_duration=10
    )
    .endpoint("GET /users")
    .endpoint("POST /orders", weight=0.3)
    .endpoint("GET /products", weight=0.7)
    .build()
)

test.run()
```

### WebSocket Test
```python
from loadtest.protocols import WebSocketHandler

@scenario
async def websocket_chat(client):
    ws = await client.websocket("wss://chat.example.com")
    
    await ws.send({"type": "join", "room": "general"})
    
    async for message in ws.listen(duration=30):
        if message["type"] == "message":
            await ws.think(1, 5)
            await ws.send({
                "type": "reply",
                "text": "Thanks!"
            })
```

## CLI Usage

```bash
# Run a test
loadtest run scenario.py

# With custom config
loadtest run scenario.py --config config.yaml

# Distributed mode
loadtest master --port 5557
loadtest worker --master localhost:5557

# View results
loadtest report results.json --format html
```

## Configuration

```yaml
# config.yaml
target:
  base_url: https://api.example.com
  timeout: 30

pattern:
  type: ramp
  target_rps: 1000
  duration: 300
  warmup: 30

users:
  concurrent: 100
  ramp_up: 60

reporting:
  format: json
  output: results.json
  prometheus:
    enabled: true
    port: 9090
```

## Real-Time Dashboard

```bash
# Start test with dashboard
loadtest run scenario.py --dashboard
```

Access dashboard at `http://localhost:8080`

Features:
- Live RPS/RPM metrics
- Response time percentiles
- Error rate tracking
- Active user count

## Distributed Load Testing

```bash
# Start master
loadtest master --bind 0.0.0.0:5557

# Start workers (on multiple machines)
loadtest worker --master 192.168.1.100:5557
loadtest worker --master 192.168.1.100:5557

# Run distributed test
loadtest run scenario.py --distributed
```

## Metrics Export

### Prometheus
```yaml
reporting:
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
```

### JSON
```python
results = test.run()
results.save_json("load_test_results.json")
```

## Analysis

```python
from loadtest.analysis import analyze_results

results = analyze_results("results.json")

print(f"99th percentile: {results.latency_p99}ms")
print(f"Error rate: {results.error_rate}%")
print(f"Max RPS: {results.max_rps}")

# Compare runs
comparison = results.compare_to("baseline.json")
print(comparison.summary())
```

## Installation

### Basic
```bash
pip install loadtest
```

### With Web Support
```bash
pip install "loadtest[web]"  # Includes Playwright
```

### All Features
```bash
pip install "loadtest[all]"
```

## Development

```bash
git clone https://github.com/rar-file/loadtest.git
cd loadtest
pip install -e ".[dev]"
pytest
```

## License

MIT License - see [LICENSE](LICENSE) file.
