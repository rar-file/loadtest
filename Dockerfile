# LoadTest Docker Image
# Multi-stage build for production-ready container

## Build Stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

## Production Stage
FROM python:3.12-slim

LABEL maintainer="LoadTest Team <dev@example.com>"
LABEL description="LoadTest - Synthetic traffic generator for load testing"

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Create non-root user
RUN useradd -m -u 1000 loadtest && \
    mkdir -p /app/tests /app/reports && \
    chown -R loadtest:loadtest /app

USER loadtest

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD loadtest version || exit 1

# Default command
ENTRYPOINT ["loadtest"]
CMD ["--help"]
