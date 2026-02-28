#!/usr/bin/env python3
"""Example: Simple load test using the new simplified API.

This example demonstrates the 3-line API for load testing.
"""

from loadtest import loadtest

# Example 1: Simplest possible test
print("Example 1: Simple test")
print("-" * 40)
test = loadtest("https://httpbin.org", rps=2, duration=5)
test.run()

# Example 2: Multiple endpoints
print("\nExample 2: Multiple endpoints")
print("-" * 40)
test = loadtest("https://httpbin.org", rps=3, duration=5)
test.add("GET /get")
test.add("POST /post", json={"hello": "world"})
test.run()

# Example 3: Dry run (preview without running)
print("\nExample 3: Dry run preview")
print("-" * 40)
test = loadtest("https://api.example.com", pattern="ramp", rps=10, target_rps=100, duration=60)
test.add("GET /users")
test.add("POST /orders", weight=0.5, json={"item": "widget"})

preview = test.dry_run()
print(f"Target: {preview['target']}")
print(f"Pattern: {preview['pattern']['type']}")
print(f"Duration: {preview['pattern']['duration']}s")
print(f"Endpoints: {len(preview['endpoints'])}")
for ep in preview['endpoints']:
    print(f"  - {ep['method']} {ep['path']}")

print("\n✅ All examples completed!")
