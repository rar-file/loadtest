# LoadTest Quick Reference

## 🚀 3-Line Quick Start

```python
from loadtest import loadtest
test = loadtest("https://api.example.com")
test.run()
```

---

## 📋 Common Patterns

### Basic Test
```python
test = loadtest("https://api.example.com", rps=10, duration=60)
test.add("GET /users")
test.run()
```

### Multiple Endpoints with Weights
```python
test = loadtest("https://api.example.com")
test.add("GET /products", weight=10)        # 10x frequency
test.add("GET /products/123", weight=5)     # 5x frequency  
test.add("POST /cart", weight=1)            # 1x frequency
test.run()
```

### With Authentication
```python
test = loadtest("https://api.example.com")
test.auth("your-token")                     # Bearer token
test.headers({"X-API-Key": "secret"})       # Custom headers
test.add("GET /protected")
test.run()
```

---

## 🌊 Traffic Patterns

| Pattern | Use Case | Code |
|---------|----------|------|
| **Constant** | Baseline load | `loadtest(url, pattern="constant", rps=10)` |
| **Ramp** | Capacity testing | `loadtest(url, pattern="ramp", rps=10, target_rps=100)` |
| **Spike** | Burst resilience | `loadtest(url, pattern="spike", rps=10, peak_rps=500)` |
| **Burst** | Isolated spike | `loadtest(url, pattern="burst", rps=10, burst_rps=1000)` |

---

## 💻 CLI Commands

```bash
# Interactive wizard
loadtest init

# Run tests
loadtest run test.py
loadtest run config.json
loadtest run config.yaml

# Preview (dry run)
loadtest run test.py --dry-run

# Auto-detect OpenAPI
loadtest detect https://api.example.com

# Override duration
loadtest run test.py --duration 120

# Show help
loadtest --help
loadtest run --help
```

---

## 📄 Config File (JSON)

```json
{
  "target": "https://api.example.com",
  "pattern": "ramp",
  "rps": 10,
  "target_rps": 100,
  "duration": 60,
  "endpoints": [
    {"method": "GET", "path": "/users", "weight": 2},
    {"method": "POST", "path": "/orders", "weight": 1, "json": {"item": "widget"}}
  ]
}
```

Run: `loadtest run config.json`

---

## 🐍 One-Liners

```python
# Health check
from loadtest import loadtest; loadtest("https://api.example.com", rps=5, duration=10).run()

# With endpoint
from loadtest import loadtest; loadtest("https://api.example.com").add("GET /users").run()

# With auth
from loadtest import loadtest; t=loadtest("https://api.example.com"); t.auth("token"); t.add("GET /api").run()
```

---

## 📊 Results & Reports

```python
results = test.run()

# Access metrics
print(f"Requests: {results.total_requests}")
print(f"Success: {results.success_rate:.1f}%")

# Generate reports
test.report(format="html", output="report.html")
test.report(format="console")  # Already shown by run()
```

---

## 💾 Save & Load

```python
from loadtest import loadtest
from loadtest.config import save, load

# Save configuration
test = loadtest("https://api.example.com")
test.add("GET /users")
save(test, "my_test.json")

# Load and run
test = load("my_test.json")
test.run()
```

---

## 🔍 Auto-Detect Endpoints

```python
from loadtest.openapi import detect_endpoints_sync

config = detect_endpoints_sync("https://api.example.com")
test = loadtest(**config)
test.run()
```

Or via CLI:
```bash
loadtest detect https://api.example.com
loadtest run loadtest.json
```

---

## ⚠️ Error Handling

LoadTest provides helpful error messages:

- **Connection refused** → "Check that the server is running"
- **404 Not Found** → "Check that the endpoint URL is correct"
- **401 Unauthorized** → "Try: test.auth('your-token')"
- **Timeout** → "Try increasing timeout: test.add(..., timeout=60)"

---

## 🎯 Best Practices

1. **Start small**: 1-5 RPS, 10-30 second duration
2. **Use dry-run**: Preview with `test.dry_run()` or `--dry-run`
3. **Ramp gradually**: Start low, increase over time
4. **Monitor**: Watch API logs during tests
5. **Be realistic**: Use weights matching real traffic

---

## 📚 More Help

- **Tutorial**: `examples/tutorial.ipynb`
- **Examples**: `examples/one_liners.py`
- **Full Docs**: See `docs/` directory

```bash
# Run tutorial
jupyter notebook examples/tutorial.ipynb
```
