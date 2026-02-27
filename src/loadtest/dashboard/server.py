"""Real-time dashboard with WebSocket server for load test monitoring.

Provides live visualization of load test metrics through a web-based dashboard
with real-time updates via WebSocket.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable


@dataclass
class DashboardMetric:
    """A single metric data point for the dashboard."""
    timestamp: float
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class DashboardSnapshot:
    """Snapshot of metrics at a point in time."""
    timestamp: float = field(default_factory=time.time)
    rps: float = 0.0
    avg_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    error_rate: float = 0.0
    active_sessions: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    status_codes: dict[str, int] = field(default_factory=dict)
    custom_metrics: dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'rps': self.rps,
            'avg_response_time': self.avg_response_time,
            'p95_response_time': self.p95_response_time,
            'p99_response_time': self.p99_response_time,
            'error_rate': self.error_rate,
            'active_sessions': self.active_sessions,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'status_codes': self.status_codes,
            'custom_metrics': self.custom_metrics,
        }


class MetricsBuffer:
    """Circular buffer for time-series metrics."""
    
    def __init__(self, max_points: int = 3600) -> None:
        """Initialize buffer.
        
        Args:
            max_points: Maximum number of data points to retain.
        """
        self.max_points = max_points
        self._data: list[DashboardSnapshot] = []
        self._lock = asyncio.Lock()
    
    async def append(self, snapshot: DashboardSnapshot) -> None:
        """Add a snapshot to the buffer."""
        async with self._lock:
            self._data.append(snapshot)
            if len(self._data) > self.max_points:
                self._data = self._data[-self.max_points:]
    
    async def get_recent(self, count: int = 100) -> list[DashboardSnapshot]:
        """Get recent snapshots.
        
        Args:
            count: Number of snapshots to return.
        
        Returns:
            List of recent snapshots.
        """
        async with self._lock:
            return self._data[-count:] if count < len(self._data) else self._data.copy()
    
    async def get_time_range(
        self,
        start: float | None = None,
        end: float | None = None
    ) -> list[DashboardSnapshot]:
        """Get snapshots within a time range.
        
        Args:
            start: Start timestamp.
            end: End timestamp.
        
        Returns:
            List of snapshots in range.
        """
        async with self._lock:
            data = self._data
            if start:
                data = [s for s in data if s.timestamp >= start]
            if end:
                data = [s for s in data if s.timestamp <= end]
            return data
    
    async def clear(self) -> None:
        """Clear all data."""
        async with self._lock:
            self._data.clear()


class WebSocketDashboard:
    """Real-time dashboard server with WebSocket support.
    
    Serves a web dashboard and provides real-time metrics updates
    to connected clients via WebSocket.
    
    Example:
        >>> dashboard = WebSocketDashboard()
        >>> await dashboard.start(port=8080)
        >>> 
        >>> # In your load test
        >>> dashboard.update(metrics_collector.get_statistics())
    """
    
    def __init__(
        self,
        update_interval: float = 1.0,
        history_size: int = 3600,
    ) -> None:
        """Initialize the dashboard.
        
        Args:
            update_interval: Metrics update interval in seconds.
            history_size: Number of historical data points to keep.
        """
        self.update_interval = update_interval
        self.buffer = MetricsBuffer(max_points=history_size)
        self._clients: set = set()
        self._running = False
        self._update_task: asyncio.Task | None = None
        self._metrics_source: Any = None
        self._start_time: float = 0
        
        # Event handlers
        self._on_client_connect: list[Callable] = []
        self._on_client_disconnect: list[Callable] = []
    
    def on_client_connect(self, callback: Callable) -> Callable:
        """Register callback for client connections.
        
        Args:
            callback: Function to call when client connects.
        
        Returns:
            The callback (for use as decorator).
        """
        self._on_client_connect.append(callback)
        return callback
    
    def on_client_disconnect(self, callback: Callable) -> Callable:
        """Register callback for client disconnections.
        
        Args:
            callback: Function to call when client disconnects.
        
        Returns:
            The callback (for use as decorator).
        """
        self._on_client_disconnect.append(callback)
        return callback
    
    def _create_snapshot(self, stats: dict[str, Any]) -> DashboardSnapshot:
        """Create a dashboard snapshot from metrics statistics."""
        duration = time.time() - self._start_time
        throughput = stats.get('throughput', 0)
        
        return DashboardSnapshot(
            timestamp=time.time(),
            rps=throughput,
            avg_response_time=stats.get('mean_response_time', 0),
            p95_response_time=stats.get('p95_response_time', 0),
            p99_response_time=stats.get('p99_response_time', 0),
            error_rate=stats.get('error_rate', 0),
            active_sessions=stats.get('active_sessions', 0),
            total_requests=stats.get('total_requests', 0),
            successful_requests=stats.get('successful_requests', 0),
            failed_requests=stats.get('failed_requests', 0),
            status_codes={str(k): v for k, v in stats.get('status_codes', {}).items()},
            custom_metrics=stats.get('custom_metrics', {}),
        )
    
    def update(self, stats: dict[str, Any]) -> None:
        """Update dashboard with new metrics.
        
        Args:
            stats: Metrics statistics dictionary.
        """
        snapshot = self._create_snapshot(stats)
        
        # Store in buffer (fire and forget)
        asyncio.create_task(self.buffer.append(snapshot))
        
        # Broadcast to clients
        asyncio.create_task(self._broadcast({
            'type': 'snapshot',
            'data': snapshot.to_dict(),
        }))
    
    async def _broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast message to all connected clients."""
        if not self._clients:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for ws in self._clients:
            try:
                await ws.send_str(message_str)
            except Exception:
                disconnected.add(ws)
        
        # Clean up disconnected clients
        self._clients -= disconnected
        for ws in disconnected:
            for callback in self._on_client_disconnect:
                try:
                    callback(ws)
                except Exception:
                    pass
    
    async def _metrics_updater(self) -> None:
        """Background task to periodically update metrics."""
        while self._running:
            try:
                if self._metrics_source:
                    stats = self._metrics_source.get_statistics()
                    self.update(stats)
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(self.update_interval)
    
    async def start(
        self,
        port: int = 8080,
        host: str = "0.0.0.0",
        metrics_source: Any = None,
    ) -> None:
        """Start the dashboard server.
        
        Args:
            port: Port to listen on.
            host: Host to bind to.
            metrics_source: Optional metrics source to auto-update from.
        """
        from aiohttp import web, WSMsgType
        
        self._metrics_source = metrics_source
        self._running = True
        self._start_time = time.time()
        
        # Start background updater
        self._update_task = asyncio.create_task(self._metrics_updater())
        
        async def index_handler(request: web.Request) -> web.Response:
            """Serve the dashboard HTML."""
            return web.Response(
                text=self._get_dashboard_html(),
                content_type='text/html',
            )
        
        async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
            """Handle WebSocket connections."""
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            
            self._clients.add(ws)
            
            # Notify callbacks
            for callback in self._on_client_connect:
                try:
                    callback(ws)
                except Exception:
                    pass
            
            # Send initial data
            history = await self.buffer.get_recent(60)
            await ws.send_str(json.dumps({
                'type': 'history',
                'data': [s.to_dict() for s in history],
            }))
            
            # Keep connection alive and handle messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_client_message(ws, data)
                    except json.JSONDecodeError:
                        pass
                elif msg.type == WSMsgType.ERROR:
                    break
            
            self._clients.discard(ws)
            
            for callback in self._on_client_disconnect:
                try:
                    callback(ws)
                except Exception:
                    pass
            
            return ws
        
        async def api_stats_handler(request: web.Request) -> web.Response:
            """Serve current stats via REST API."""
            if self._metrics_source:
                stats = self._metrics_source.get_statistics()
                return web.json_response(stats)
            return web.json_response({})
        
        async def api_history_handler(request: web.Request) -> web.Response:
            """Serve historical data via REST API."""
            count = int(request.query.get('count', '100'))
            history = await self.buffer.get_recent(count)
            return web.json_response([s.to_dict() for s in history])
        
        app = web.Application()
        app.router.add_get('/', index_handler)
        app.router.add_get('/ws', websocket_handler)
        app.router.add_get('/api/stats', api_stats_handler)
        app.router.add_get('/api/history', api_history_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        print(f"📊 Dashboard running at http://{host}:{port}")
        
        # Keep running
        while self._running:
            await asyncio.sleep(1)
    
    async def _handle_client_message(self, ws, data: dict[str, Any]) -> None:
        """Handle messages from clients."""
        msg_type = data.get('type')
        
        if msg_type == 'ping':
            await ws.send_str(json.dumps({'type': 'pong'}))
        
        elif msg_type == 'get_history':
            count = data.get('count', 100)
            history = await self.buffer.get_recent(count)
            await ws.send_str(json.dumps({
                'type': 'history',
                'data': [s.to_dict() for s in history],
            }))
    
    def stop(self) -> None:
        """Stop the dashboard server."""
        self._running = False
        if self._update_task:
            self._update_task.cancel()
    
    def _get_dashboard_html(self) -> str:
        """Get the dashboard HTML page."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LoadTest Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            min-height: 100vh;
        }
        .header {
            background: #1e293b;
            padding: 1rem 2rem;
            border-bottom: 1px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { font-size: 1.5rem; color: #60a5fa; }
        .status { display: flex; align-items: center; gap: 0.5rem; }
        .status-dot {
            width: 10px; height: 10px; border-radius: 50%;
            background: #22c55e; animation: pulse 2s infinite;
        }
        .status-dot.disconnected { background: #ef4444; animation: none; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .container {
            padding: 2rem;
            max-width: 1400px;
            margin: 0 auto;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 0.5rem;
            border: 1px solid #334155;
        }
        .metric-card h3 {
            font-size: 0.875rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .metric-card.success .metric-value { color: #22c55e; }
        .metric-card.error .metric-value { color: #ef4444; }
        .metric-card.warning .metric-value { color: #f59e0b; }
        .chart-container {
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 0.5rem;
            border: 1px solid #334155;
            margin-bottom: 1rem;
            height: 300px;
            position: relative;
        }
        .chart-title {
            font-size: 1rem;
            color: #94a3b8;
            margin-bottom: 1rem;
        }
        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1rem;
        }
        .status-codes {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .status-code {
            background: #334155;
            padding: 0.5rem 1rem;
            border-radius: 0.25rem;
            font-size: 0.875rem;
        }
        .status-code.ok { background: #166534; }
        .status-code.error { background: #7f1d1d; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 LoadTest Dashboard</h1>
        <div class="status">
            <span id="status-text">Connecting...</span>
            <div id="status-dot" class="status-dot disconnected"></div>
        </div>
    </div>
    
    <div class="container">
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Requests/sec</h3>
                <div id="rps" class="metric-value">0</div>
            </div>
            <div class="metric-card">
                <h3>Avg Response Time</h3>
                <div id="avg-response" class="metric-value">0ms</div>
            </div>
            <div class="metric-card">
                <h3>P95 Response Time</h3>
                <div id="p95-response" class="metric-value">0ms</div>
            </div>
            <div class="metric-card error">
                <h3>Error Rate</h3>
                <div id="error-rate" class="metric-value">0%</div>
            </div>
            <div class="metric-card">
                <h3>Active Sessions</h3>
                <div id="active-sessions" class="metric-value">0</div>
            </div>
            <div class="metric-card success">
                <h3>Total Requests</h3>
                <div id="total-requests" class="metric-value">0</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-container">
                <div class="chart-title">Throughput (RPS)</div>
                <canvas id="rpsChart"></canvas>
            </div>
            <div class="chart-container">
                <div class="chart-title">Response Times</div>
                <canvas id="responseChart"></canvas>
            </div>
        </div>
        
        <div class="chart-container">
            <div class="chart-title">Status Codes</div>
            <div id="status-codes" class="status-codes"></div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${window.location.host}/ws`);
        let rpsChart, responseChart;
        let historyData = [];
        
        // Initialize charts
        function initCharts() {
            const ctx1 = document.getElementById('rpsChart').getContext('2d');
            rpsChart = new Chart(ctx1, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'RPS',
                        data: [],
                        borderColor: '#60a5fa',
                        backgroundColor: 'rgba(96, 165, 250, 0.1)',
                        fill: true,
                        tension: 0.4,
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8', maxTicksLimit: 10 }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#e2e8f0' } }
                    }
                }
            });
            
            const ctx2 = document.getElementById('responseChart').getContext('2d');
            responseChart = new Chart(ctx2, {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [
                        {
                            label: 'Avg',
                            data: [],
                            borderColor: '#22c55e',
                            backgroundColor: 'rgba(34, 197, 94, 0.1)',
                            fill: false,
                            tension: 0.4,
                        },
                        {
                            label: 'P95',
                            data: [],
                            borderColor: '#f59e0b',
                            backgroundColor: 'rgba(245, 158, 11, 0.1)',
                            fill: false,
                            tension: 0.4,
                        },
                        {
                            label: 'P99',
                            data: [],
                            borderColor: '#ef4444',
                            backgroundColor: 'rgba(239, 68, 68, 0.1)',
                            fill: false,
                            tension: 0.4,
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8' }
                        },
                        x: {
                            grid: { color: '#334155' },
                            ticks: { color: '#94a3b8', maxTicksLimit: 10 }
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#e2e8f0' } }
                    }
                }
            });
        }
        
        // Format timestamp
        function formatTime(ts) {
            const d = new Date(ts * 1000);
            return d.toLocaleTimeString();
        }
        
        // Update charts with new data
        function updateCharts(data) {
            const maxPoints = 60;
            
            if (data.length > maxPoints) {
                data = data.slice(-maxPoints);
            }
            
            const labels = data.map(d => formatTime(d.timestamp));
            const rps = data.map(d => d.rps.toFixed(1));
            const avgResponse = data.map(d => (d.avg_response_time * 1000).toFixed(0));
            const p95Response = data.map(d => (d.p95_response_time * 1000).toFixed(0));
            const p99Response = data.map(d => (d.p99_response_time * 1000).toFixed(0));
            
            rpsChart.data.labels = labels;
            rpsChart.data.datasets[0].data = rps;
            rpsChart.update('none');
            
            responseChart.data.labels = labels;
            responseChart.data.datasets[0].data = avgResponse;
            responseChart.data.datasets[1].data = p95Response;
            responseChart.data.datasets[2].data = p99Response;
            responseChart.update('none');
        }
        
        // Update metric cards
        function updateMetrics(snapshot) {
            document.getElementById('rps').textContent = snapshot.rps.toFixed(1);
            document.getElementById('avg-response').textContent = 
                (snapshot.avg_response_time * 1000).toFixed(0) + 'ms';
            document.getElementById('p95-response').textContent = 
                (snapshot.p95_response_time * 1000).toFixed(0) + 'ms';
            document.getElementById('error-rate').textContent = 
                snapshot.error_rate.toFixed(2) + '%';
            document.getElementById('active-sessions').textContent = 
                snapshot.active_sessions;
            document.getElementById('total-requests').textContent = 
                snapshot.total_requests.toLocaleString();
            
            // Update status codes
            const statusCodes = document.getElementById('status-codes');
            statusCodes.innerHTML = '';
            for (const [code, count] of Object.entries(snapshot.status_codes)) {
                const div = document.createElement('div');
                div.className = 'status-code' + (code.startsWith('2') ? ' ok' : ' error');
                div.textContent = `${code}: ${count}`;
                statusCodes.appendChild(div);
            }
        }
        
        ws.onopen = () => {
            document.getElementById('status-text').textContent = 'Connected';
            document.getElementById('status-dot').classList.remove('disconnected');
        };
        
        ws.onclose = () => {
            document.getElementById('status-text').textContent = 'Disconnected';
            document.getElementById('status-dot').classList.add('disconnected');
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            
            if (msg.type === 'history') {
                historyData = msg.data;
                updateCharts(historyData);
                if (historyData.length > 0) {
                    updateMetrics(historyData[historyData.length - 1]);
                }
            } else if (msg.type === 'snapshot') {
                historyData.push(msg.data);
                if (historyData.length > 300) {
                    historyData.shift();
                }
                updateCharts(historyData);
                updateMetrics(msg.data);
            }
        };
        
        // Reconnect on close
        ws.onclose = () => {
            document.getElementById('status-text').textContent = 'Disconnected';
            document.getElementById('status-dot').classList.add('disconnected');
            setTimeout(() => window.location.reload(), 3000);
        };
        
        // Initialize
        initCharts();
    </script>
</body>
</html>
'''
