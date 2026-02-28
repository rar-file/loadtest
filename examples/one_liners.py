"""5 One-Liner Load Test Examples

Each example can be run standalone. Copy any example and run it!

Prerequisites:
    pip install loadtest

Quick test target (replace with your own API):
    We use https://httpbin.org for demonstration. Replace with your actual API.
"""

# =============================================================================
# EXAMPLE 1: Smoke Test - Quick Health Check
# =============================================================================
# "Is my API responding?" - A 10-second sanity check
#
# Usage: python -c "$(curl -s https://example.com/examples/one_liners.py)" --ex1

# One-liner version:
exec("from loadtest import loadtest; t=loadtest('https://httpbin.org', rps=5, duration=10); t.run()")

# =============================================================================
# EXAMPLE 2: API Endpoints Test - Multiple Routes
# =============================================================================
# "Test my key API endpoints" - Simple multi-endpoint test
#
# Tests 3 endpoints: GET /get, POST /post, GET /headers
# Weights control frequency: GET /get runs 2x as often as the others

# Full version:
from loadtest import loadtest
test = loadtest("https://httpbin.org", rps=10, duration=30)
test.add("GET /get", weight=2)
test.add("POST /post", weight=1, json={"test": "data"})
test.add("GET /headers", weight=1)
test.run()

# =============================================================================
# EXAMPLE 3: Ramp Test - Gradual Load Increase
# =============================================================================
# "How does my API handle increasing load?" - Capacity testing
#
# Starts at 10 RPS, ramps up to 200 RPS over 60 seconds
# Great for finding performance degradation points

from loadtest import loadtest
test = loadtest("https://httpbin.org", pattern="ramp", rps=10, target_rps=200, duration=60)
test.add("GET /get")
test.add("POST /post", weight=0.5, json={"user": "test"})
test.run()

# =============================================================================
# EXAMPLE 4: Spike Test - Sudden Traffic Burst
# =============================================================================
# "Can my API handle traffic spikes?" - Burst resilience testing
#
# Runs at 10 RPS baseline, then spikes to 500 RPS for 10 seconds
# Simulates flash crowds or viral content

from loadtest import loadtest
test = loadtest("https://httpbin.org", pattern="spike", rps=10, peak_rps=500, spike_duration=10, duration=60)
test.add("GET /get")
test.run()

# =============================================================================
# EXAMPLE 5: Authenticated API Test - With Headers
# =============================================================================
# "Test my protected API" - With authentication and custom headers
#
# Sets global headers applied to all requests
# Tests protected endpoints with Bearer token

from loadtest import loadtest
test = loadtest("https://httpbin.org", rps=20, duration=30)
test.headers({"Accept": "application/json", "X-Custom-Header": "test"})
test.add("GET /bearer")  # httpbin will check for Authorization header
test.add("GET /get")
test.add("POST /post", weight=0.3, json={"key": "value"})
test.run()

# =============================================================================
# BONUS: Ultra-Compact One-Liners (for the brave!)
# =============================================================================

# Absolute minimum - 1 line, no variables:
# python -c "from loadtest import loadtest; loadtest('https://httpbin.org').run()"

# With one endpoint:
# python -c "from loadtest import loadtest; loadtest('https://httpbin.org').add('GET /get').run()"

# With auth header:
# python -c "from loadtest import loadtest; loadtest('https://httpbin.org').auth('my-token').add('GET /get').run()"

# Dry run - preview without executing:
# python -c "from loadtest import loadtest; print(loadtest('https://httpbin.org').add('GET /get').dry_run())"

# =============================================================================
# Tips for Production Use:
# =============================================================================
#
# 1. Replace 'https://httpbin.org' with your actual API URL
# 2. Adjust RPS based on your expected traffic (start low!)
# 3. Use weights to simulate realistic traffic patterns
# 4. Add more endpoints for comprehensive testing
# 5. Run longer duration (300s = 5 minutes) for stability testing
#
# Save your config:
#   from loadtest.config import save_config
#   save_config(test, 'my_test.json')
#
# Load and reuse:
#   from loadtest.config import load_config
#   test = load_config('my_test.json')
#   test.run()
