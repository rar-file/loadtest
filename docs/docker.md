# LoadTest Docker Deployment Guide

This guide covers deploying LoadTest using Docker and Docker Compose.

## Quick Start

### 1. Build the Image

```bash
docker build -t loadtest:latest .
```

### 2. Run a Test

```bash
# Run with built-in examples
docker run --rm -v $(pwd)/reports:/app/reports loadtest:latest run /app/examples/quickstart.py --output /app/reports/report.html

# Run your own test file
docker run --rm -v $(pwd)/tests:/app/tests:ro -v $(pwd)/reports:/app/reports loadtest:latest run /app/tests/my_test.py
```

## Docker Compose

### Basic Usage

```bash
# Start with default configuration
docker-compose up loadtest

# Run a specific test
docker-compose run --rm loadtest run /app/examples/simple_http_load.py

# Generate HTML report
docker-compose run --rm loadtest run /app/examples/api_load_test.py --output /app/reports/results.html
```

### Override Configuration

Create a `docker-compose.override.yml` for local customizations:

```yaml
version: '3.8'

services:
  loadtest:
    volumes:
      - ./my_tests:/app/tests:ro
    command: ["run", "/app/tests/production_load.py", "--output", "/app/reports/report.html"]
```

## Production Deployment

### Kubernetes

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: loadtest-job
spec:
  template:
    spec:
      containers:
      - name: loadtest
        image: loadtest:latest
        imagePullPolicy: Always
        command: ["run", "/app/tests/stress_test.py"]
        volumeMounts:
        - name: tests
          mountPath: /app/tests
        - name: reports
          mountPath: /app/reports
      volumes:
      - name: tests
        configMap:
          name: loadtest-config
      - name: reports
        emptyDir: {}
      restartPolicy: Never
```

### CI/CD Integration

#### GitHub Actions

```yaml
name: Load Test

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  loadtest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: docker build -t loadtest:latest .
      
      - name: Run load test
        run: |
          docker run --rm \
            -v $(pwd)/tests:/app/tests:ro \
            -v $(pwd)/reports:/app/reports \
            loadtest:latest run /app/tests/api_test.py --output /app/reports/index.html
      
      - name: Upload report
        uses: actions/upload-artifact@v4
        with:
          name: loadtest-report
          path: reports/
```

#### GitLab CI

```yaml
loadtest:
  stage: test
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t loadtest:latest .
    - docker run --rm -v $(pwd)/tests:/app/tests:ro -v $(pwd)/reports:/app/reports loadtest:latest run /app/tests/test.py --output /app/reports/report.html
  artifacts:
    paths:
      - reports/
    expire_in: 1 week
  only:
    - schedules
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PYTHONUNBUFFERED` | Disable Python output buffering | `1` |
| `TERM` | Terminal type for colored output | `xterm-256color` |

## Volume Mounts

| Path | Description | Notes |
|------|-------------|-------|
| `/app/tests` | Your test files | Mount as read-only (`:ro`) |
| `/app/examples` | Built-in examples | Already included in image |
| `/app/reports` | Output directory for HTML reports | Must be writable |

## Health Checks

The container includes a health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD loadtest version || exit 1
```

## Security

- Container runs as non-root user (`loadtest`, UID 1000)
- Only production dependencies are installed
- Build artifacts are excluded from final image

## Troubleshooting

### Permission Denied on Reports

```bash
# Fix ownership
sudo chown -R 1000:1000 ./reports
```

### Test File Not Found

Ensure the path inside the container is correct:

```bash
# Wrong
docker run loadtest:latest run ./tests/my_test.py

# Right
docker run -v $(pwd)/tests:/app/tests:ro loadtest:latest run /app/tests/my_test.py
```

### Container Exits Immediately

Check that your test file defines `create_test()` or `main()`:

```python
async def create_test():
    return LoadTest(...)
```

## Building with Web Support

For Playwright/browser automation support:

```dockerfile
# Dockerfile.web
FROM python:3.12-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# ... rest of Dockerfile
RUN pip install ".[web]"
RUN playwright install chromium
```
