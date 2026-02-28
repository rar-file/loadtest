"""Progress tracking and live results display.

Provides real-time progress bars, live metrics, and beautiful console output.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

if TYPE_CHECKING:
    from loadtest.core import TestResult
    from loadtest.metrics.collector import MetricsCollector


console = Console()


@dataclass
class LiveStats:
    """Live statistics snapshot."""

    elapsed: float
    total_requests: int
    successful: int
    failed: int
    rps: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    error_rate: float


class ProgressTracker:
    """Track and display test progress with live updates."""

    def __init__(
        self, duration: float, test_name: str = "Load Test", show_live: bool = True
    ) -> None:
        """Initialize progress tracker.

        Args:
            duration: Total test duration in seconds
            test_name: Name of the test
            show_live: Whether to show live dashboard
        """
        self.duration = duration
        self.test_name = test_name
        self.show_live = show_live
        self.start_time: float | None = None
        self._stop_event = asyncio.Event()
        self._metrics_callback: Callable[[], dict] | None = None

    def set_metrics_callback(self, callback: Callable[[], dict]) -> None:
        """Set callback to get current metrics."""
        self._metrics_callback = callback

    def _create_progress_bar(self) -> Progress:
        """Create the main progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TimeElapsedColumn(),
            "/",
            TimeRemainingColumn(),
            console=console,
        )

    def _create_stats_table(self, stats: LiveStats) -> Table:
        """Create statistics table."""
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan", width=15)
        table.add_column("Value", style="white")

        table.add_row("Requests", f"{stats.total_requests:,}")
        table.add_row("Success", f"[green]{stats.successful:,}[/green]")
        table.add_row("Failed", f"[red]{stats.failed:,}[/red]" if stats.failed > 0 else "0")
        table.add_row("RPS", f"{stats.rps:.1f}")
        table.add_row("Avg Latency", f"{stats.avg_latency*1000:.1f}ms")
        table.add_row("P95 Latency", f"{stats.p95_latency*1000:.1f}ms")
        table.add_row("P99 Latency", f"{stats.p99_latency*1000:.1f}ms")
        table.add_row(
            "Error Rate",
            (
                f"[red]{stats.error_rate:.1f}%[/red]"
                if stats.error_rate > 5
                else f"{stats.error_rate:.1f}%"
            ),
        )

        return table

    def _get_live_stats(self) -> LiveStats:
        """Get current live statistics."""
        metrics = self._metrics_callback() if self._metrics_callback else {}

        elapsed = time.time() - (self.start_time or time.time())
        total = metrics.get("total_requests", 0)

        return LiveStats(
            elapsed=elapsed,
            total_requests=total,
            successful=metrics.get("successful_requests", 0),
            failed=metrics.get("failed_requests", 0),
            rps=total / max(elapsed, 0.001),
            avg_latency=metrics.get("mean_response_time", 0),
            p95_latency=metrics.get("p95_response_time", 0),
            p99_latency=metrics.get("p99_response_time", 0),
            error_rate=metrics.get("error_rate", 0),
        )

    async def _update_loop(self, live: Live, progress: Progress, task_id: int) -> None:
        """Update loop for live display."""
        while not self._stop_event.is_set():
            elapsed = time.time() - (self.start_time or time.time())

            # Update progress
            progress.update(task_id, completed=elapsed, total=self.duration)

            # Update stats
            stats = self._get_live_stats()
            stats_table = self._create_stats_table(stats)

            layout = Layout()
            layout.split_column(
                Layout(Panel(progress, title="Progress", border_style="blue")),
                Layout(Panel(stats_table, title="Live Metrics", border_style="green")),
            )

            live.update(layout)

            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop_event.wait(), timeout=0.5)

    async def run(self) -> None:
        """Run the progress tracker."""
        if not self.show_live:
            # Just wait without display
            await asyncio.wait_for(self._stop_event.wait(), timeout=self.duration)
            return

        self.start_time = time.time()

        progress = self._create_progress_bar()
        task_id = progress.add_task(f"[cyan]{self.test_name}", total=self.duration, completed=0)

        with Live(console=console, refresh_per_second=4) as live:
            await self._update_loop(live, progress, task_id)

    def stop(self) -> None:
        """Stop the progress tracker."""
        self._stop_event.set()


def show_test_summary(result: TestResult, console: Console | None = None) -> None:
    """Display a beautiful test summary.

    Args:
        result: Test result to display
        console: Console to use (creates new if None)
    """
    console = console or Console()

    stats = result.metrics.get_statistics()

    # Main results table
    table = Table(title="Load Test Results", title_style="bold cyan")
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Value", style="white")

    # Basic stats
    table.add_row("Test Name", result.config.name)
    table.add_row("Duration", f"{result.duration:.2f}s")
    table.add_row("Total Requests", f"{result.total_requests:,}")
    table.add_row("Successful", f"[green]{result.successful_requests:,}[/green]")
    table.add_row(
        "Failed", f"[red]{result.failed_requests:,}[/red]" if result.failed_requests > 0 else "0"
    )
    table.add_row(
        "Success Rate",
        (
            f"[green]{result.success_rate:.1f}%[/green]"
            if result.success_rate >= 95
            else f"[yellow]{result.success_rate:.1f}%[/yellow]"
        ),
    )

    # Response times
    table.add_row("", "")
    table.add_row("[bold]Response Times[/bold]", "")
    table.add_row("  Min", f"{stats.get('min_response_time', 0)*1000:.2f}ms")
    table.add_row("  Max", f"{stats.get('max_response_time', 0)*1000:.2f}ms")
    table.add_row("  Mean", f"{stats.get('mean_response_time', 0)*1000:.2f}ms")
    table.add_row("  Median", f"{stats.get('median_response_time', 0)*1000:.2f}ms")
    table.add_row("  P95", f"{stats.get('p95_response_time', 0)*1000:.2f}ms")
    table.add_row("  P99", f"{stats.get('p99_response_time', 0)*1000:.2f}ms")

    console.print()
    console.print(table)

    # Performance verdict
    success_rate = result.success_rate
    p99 = stats.get("p99_response_time", 0) * 1000

    if success_rate >= 99 and p99 < 500:
        verdict = "[bold green]✓ EXCELLENT[/bold green] - API is performing great!"
    elif success_rate >= 95 and p99 < 1000:
        verdict = "[bold green]✓ GOOD[/bold green] - API is healthy"
    elif success_rate >= 90:
        verdict = "[bold yellow]⚠ FAIR[/bold yellow] - Some degradation observed"
    else:
        verdict = "[bold red]✗ POOR[/bold red] - Significant issues detected"

    console.print()
    console.print(Panel(verdict, border_style="blue"))


class TestProgress:
    """Simple progress wrapper for use in core LoadTest."""

    def __init__(self, duration: float, test_name: str = "Load Test") -> None:
        """Initialize test progress.

        Args:
            duration: Test duration in seconds.
            test_name: Name of the test.
        """
        self.duration = duration
        self.test_name = test_name
        self.tracker = ProgressTracker(duration, test_name)
        self._task: asyncio.Task | None = None

    def set_metrics(self, metrics: MetricsCollector) -> None:
        """Set metrics source."""
        self.tracker.set_metrics_callback(metrics.get_statistics)

    async def start(self) -> None:
        """Start showing progress."""
        self._task = asyncio.create_task(self.tracker.run())

    def stop(self) -> None:
        """Stop progress display."""
        self.tracker.stop()
        if self._task:
            self._task.cancel()
