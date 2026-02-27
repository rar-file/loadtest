# Architecture

## Overview

LoadTest follows an async-first architecture designed for high concurrency and scalability.

## Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         LoadTest                                │
│                    (Orchestrator)                               │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    Configuration                          │ │
│  │  - Duration        - Warmup Period                       │ │
│  │  - Max Concurrent  - Console Output                      │ │
│  └───────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    TestRunner                             │ │
│  │         (Async Event Loop Management)                     │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  │  Semaphore │  │   Queue     │  │   Task Pool     │   │ │
│  │  │ (Concurrency│  │  (Pending   │  │  (Active Tasks) │   │ │
│  │  │   Control) │  │   Requests) │  │                 │   │ │
│  │  └─────────────┘  └─────────────┘  └─────────────────┘   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Async Architecture

LoadTest leverages Python's asyncio for high concurrency:

```
┌────────────────────────────────────────────┐
│           Event Loop                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐      │
│  │ Task 1  │ │ Task 2  │ │ Task N  │      │
│  │ (HTTP)  │ │ (HTTP)  │ │ (Web)   │      │
│  └────┬────┘ └────┬────┘ └────┬────┘      │
│       └────────────┴───────────┘            │
│                 │                           │
│                 ▼                           │
│        ┌─────────────────┐                  │
│        │  Scenario Queue │                  │
│        │   (Weighted)    │                  │
│        └─────────────────┘                  │
└────────────────────────────────────────────┘
```

## Scenario Execution Flow

```
Generator ──> Rate Controller ──> Scenario Selector ──> Executor
                                              │
                                              ▼
                                    ┌──────────────────┐
                                    │   Scenario       │
                                    │  - HTTP Request  │
                                    │  - Web Action    │
                                    │  - Custom Logic  │
                                    └────────┬─────────┘
                                             │
                                             ▼
                                    ┌──────────────────┐
                                    │  Metrics         │
                                    │  - Response Time │
                                    │  - Status Code   │
                                    │  - Custom        │
                                    └──────────────────┘
```

## Traffic Patterns

### Constant Rate
```
Requests
    │    ┌────────────────────────────┐
    │    │                            │
    │────┘                            └────
    └──────────────────────────────────────> Time
```

### Ramp Pattern
```
Requests
    │         ╱
    │       ╱
    │     ╱
    │   ╱
    │ ╱
    └──────────────────────────────────────> Time
```

### Spike Pattern
```
Requests
    │              ╱╲
    │             ╱  ╲
    │────────────╱    ╲───────────────────
    │           ╱      ╲
    └──────────────────────────────────────> Time
```

## Metrics Collection

LoadTest uses lock-free data structures where possible for metrics:

```python
class MetricsCollector:
    def __init__(self):
        self._response_times = []  # List append is thread-safe
        self._status_codes = Counter()
        self._custom_metrics = defaultdict(list)
```

## Extension Points

1. **Custom Scenarios**: Extend `Scenario` base class
2. **Custom Generators**: Implement generator interface
3. **Custom Reports**: Extend report generators
4. **Custom Metrics**: Use the metrics collector API

## Performance Characteristics

### Concurrency Model
- Async/await for I/O-bound operations
- Connection pooling for HTTP clients
- Bounded concurrency with semaphores

### Memory Usage
- Streaming results where possible
- Configurable metric retention
- Efficient data structures

### Scalability
- Horizontal scaling through distributed testing
- Resource-efficient async architecture
- Minimal per-request overhead
