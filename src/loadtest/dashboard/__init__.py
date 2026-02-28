"""Real-time dashboard for loadtest.

This module provides WebSocket-based real-time dashboards
for monitoring load tests as they run.
"""

from __future__ import annotations

from loadtest.dashboard.server import (
    DashboardMetric,
    DashboardSnapshot,
    MetricsBuffer,
    WebSocketDashboard,
)

__all__ = [
    "DashboardMetric",
    "DashboardSnapshot",
    "MetricsBuffer",
    "WebSocketDashboard",
]
