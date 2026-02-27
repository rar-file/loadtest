# API Reference - Core

## LoadTest

::: loadtest.core.LoadTest
    options:
      show_source: true
      show_root_heading: true

## LoadTestConfig

::: loadtest.core.LoadTestConfig
    options:
      show_source: true

## TestResult

::: loadtest.core.TestResult
    options:
      show_source: true

## Configuration Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `"Load Test"` | Name of the test |
| `duration` | `float` | `60.0` | Test duration in seconds |
| `warmup_duration` | `float` | `5.0` | Warmup period before recording |
| `max_concurrent` | `int` | `1000` | Maximum concurrent executions |
| `console_output` | `bool` | `True` | Enable real-time console output |

## Error Handling

The LoadTest raises the following exceptions:

- `RuntimeError`: When no scenarios or pattern is configured
- `asyncio.TimeoutError`: When scenario execution times out

## Example Usage

```python
from loadtest import LoadTest

# Basic usage
test = LoadTest(name="My Test", duration=60)

# Method chaining
test = LoadTest() &#46;add_scenario(scenario1) &#46;add_scenario(scenario2) &#46;set_pattern(generator)

# Run test
results = await test.run()
```
