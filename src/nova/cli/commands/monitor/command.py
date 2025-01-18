"""Monitor command for Nova system."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import (
    Any,
    TypedDict,
    TypeVar,
    cast,
)

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from nova.cli.utils.command import NovaCommand
from nova.config import load_config
from nova.monitoring.logs import LogManager
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore

logger: logging.Logger = logging.getLogger(__name__)

# Type variable for click command function
F = TypeVar("F", bound=Callable[..., Any])


# Type definitions for monitoring data
class MemoryStatus(TypedDict):
    """Memory status information."""

    status: str
    current_mb: float
    peak_mb: float
    warning_count: int


class ComponentStatus(TypedDict):
    """Component status information."""

    status: str


class HealthStatus(TypedDict):
    """System health status information."""

    memory: MemoryStatus
    vector_store: str
    monitor: str
    logs: str
    session_uptime: float
    status: str


class ProcessStats(TypedDict):
    """Process statistics."""

    current_memory_mb: float
    peak_memory_mb: float
    warning_count: int


class MemoryStats(TypedDict):
    """Memory statistics."""

    process: ProcessStats


class SessionStats(TypedDict):
    """Session statistics."""

    start_time: str
    uptime: float


class SystemStats(TypedDict):
    """System statistics."""

    memory: MemoryStats
    session: SessionStats
    profiles: list[dict[str, Any]]
    vector_store: dict[str, Any]
    monitor: dict[str, Any]
    logs: dict[str, int]


class LogEntry(TypedDict):
    """Log entry information."""

    timestamp: str
    level: str
    component: str
    message: str


class ProfileInfo(TypedDict):
    """Profile information."""

    name: str
    timestamp: str
    duration: float
    stats_file: str
    profile_file: str


class MonitorCommand(NovaCommand):
    """Monitor command for nova CLI."""

    name = "monitor"
    help = "Monitor system status and performance"

    def __init__(self) -> None:
        """Initialize monitor command."""
        super().__init__()
        self.config = load_config()
        self.console = Console()
        self.monitor = SessionMonitor(nova_dir=self.config.paths.state_dir)
        self.persistent_monitor = PersistentMonitor(base_path=self.config.paths.state_dir)
        self.log_manager = LogManager(log_dir=str(self.config.paths.logs_dir))

    def create_command(self) -> click.Command:
        """Create the monitor command group.

        Returns:
            click.Command: The Click command group
        """

        @click.group(name=self.name, help=self.help)
        def monitor() -> None:
            """Monitor system status and performance."""
            pass

        @monitor.command()
        def health() -> None:
            """Check system health."""
            self.check_health()

        @monitor.command()
        def stats() -> None:
            """Display system statistics."""
            self.display_stats()

        @monitor.command()
        @click.option(
            "--component",
            type=str,
            help="Filter logs by component",
            required=False,
        )
        @click.option(
            "--level",
            type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
            help="Filter logs by level",
            required=False,
        )
        def logs(component: str | None, level: str | None) -> None:
            """View system logs."""
            self.view_logs(component, level)

        return monitor

    def check_health(self) -> None:
        """Check system health."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task_id = progress.add_task("Checking system health...", total=None)
            health_status = self._get_health_status()
            progress.remove_task(task_id)

        table = Table(title="System Health Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Memory", health_status["memory"]["status"])
        table.add_row("Vector Store", health_status["vector_store"])
        table.add_row("Monitor", health_status["monitor"])
        table.add_row("Logs", health_status["logs"])
        table.add_row("Session Uptime", f"{health_status['session_uptime']:.2f}s")
        table.add_row("Overall Status", health_status["status"])

        self.console.print(table)

    def display_stats(self) -> None:
        """Display system statistics."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task_id = progress.add_task("Gathering system statistics...", total=None)
            stats = self._get_system_stats()
            progress.remove_task(task_id)

        # Memory stats
        memory_table = Table(title="Memory Statistics")
        memory_table.add_column("Metric", style="cyan")
        memory_table.add_column("Value", style="green")
        memory_table.add_row(
            "Current Memory", f"{stats['memory']['process']['current_memory_mb']:.2f} MB"
        )
        memory_table.add_row(
            "Peak Memory", f"{stats['memory']['process']['peak_memory_mb']:.2f} MB"
        )
        memory_table.add_row("Warning Count", str(stats["memory"]["process"]["warning_count"]))
        self.console.print(memory_table)
        self.console.print()

        # Session stats
        session_table = Table(title="Session Statistics")
        session_table.add_column("Metric", style="cyan")
        session_table.add_column("Value", style="green")
        session_table.add_row("Start Time", stats["session"]["start_time"])
        session_table.add_row("Uptime", f"{stats['session']['uptime']:.2f}s")
        self.console.print(session_table)
        self.console.print()

        # Vector store stats
        vector_table = Table(title="Vector Store Statistics")
        vector_table.add_column("Metric", style="cyan")
        vector_table.add_column("Value", style="green")
        for key, value in stats["vector_store"].items():
            vector_table.add_row(key, str(value))
        self.console.print(vector_table)
        self.console.print()

        # Monitor stats
        monitor_table = Table(title="Monitor Statistics")
        monitor_table.add_column("Metric", style="cyan")
        monitor_table.add_column("Value", style="green")
        for key, value in stats["monitor"].items():
            monitor_table.add_row(key, str(value))
        self.console.print(monitor_table)
        self.console.print()

        # Log stats
        log_table = Table(title="Log Statistics")
        log_table.add_column("Metric", style="cyan")
        log_table.add_column("Value", style="green")
        for key, value in stats["logs"].items():
            log_table.add_row(key, str(value))
        self.console.print(log_table)

    def view_logs(self, component: str | None, level: str | None) -> None:
        """View system logs.

        Args:
            component: Filter logs by component
            level: Filter logs by level
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task_id = progress.add_task("Loading logs...", total=None)
            logs = self._get_logs(component, level)
            progress.remove_task(task_id)

        table = Table(title="System Logs")
        table.add_column("Timestamp", style="cyan")
        table.add_column("Level", style="green")
        table.add_column("Component", style="blue")
        table.add_column("Message", style="white")

        for log in logs:
            table.add_row(log["timestamp"], log["level"], log["component"], log["message"])

        self.console.print(table)

    def _get_health_status(self) -> HealthStatus:
        """Get system health status.

        Returns:
            HealthStatus: System health status information
        """
        # Get memory status from monitor
        health_status = self.monitor.check_health()
        memory_status = cast(MemoryStatus, health_status["memory"])

        # Check vector store
        try:
            vector_store = VectorStore(base_path=str(self.config.paths.vector_store_dir))
            vector_store_status = "OK"
        except Exception as e:
            vector_store_status = f"Error: {e}"

        # Check monitor
        try:
            self.persistent_monitor.check_health()
            monitor_status = "OK"
        except Exception as e:
            monitor_status = f"Error: {e}"

        # Check logs
        try:
            self.log_manager.rotate_logs()
            logs_status = "OK"
        except Exception as e:
            logs_status = f"Error: {e}"

        # Get session uptime
        session_uptime = (datetime.now() - self.monitor.session_start).total_seconds()

        # Determine overall status
        if all(
            s == "OK"
            for s in [memory_status["status"], vector_store_status, monitor_status, logs_status]
        ):
            overall_status = "Healthy"
        else:
            overall_status = "Degraded"

        return {
            "memory": memory_status,
            "vector_store": vector_store_status,
            "monitor": monitor_status,
            "logs": logs_status,
            "session_uptime": session_uptime,
            "status": overall_status,
        }

    def _get_system_stats(self) -> SystemStats:
        """Get system statistics.

        Returns:
            SystemStats: System statistics information
        """
        # Get memory stats
        memory_check = self.monitor.memory.check_memory()
        memory_stats: ProcessStats = {
            "current_memory_mb": memory_check["current_mb"],
            "peak_memory_mb": memory_check["peak_mb"],
            "warning_count": memory_check["warning_count"],
        }

        # Get session stats
        session_stats: SessionStats = {
            "start_time": self.monitor.session_start.isoformat(),
            "uptime": (datetime.now() - self.monitor.session_start).total_seconds(),
        }

        # Get persistent stats
        persistent_stats = self.persistent_monitor.get_stats()
        profiles = cast(list[dict[str, Any]], persistent_stats.get("profiles", []))
        vector_store = cast(dict[str, Any], persistent_stats.get("vector_store", {}))
        monitor = cast(dict[str, Any], persistent_stats.get("monitor", {}))

        # Get log stats
        log_stats = self.log_manager.get_stats()

        return {
            "memory": {"process": memory_stats},
            "session": session_stats,
            "profiles": profiles,
            "vector_store": vector_store,
            "monitor": monitor,
            "logs": log_stats,
        }

    def _get_logs(self, component: str | None = None, level: str | None = None) -> list[LogEntry]:
        """Get system logs.

        Args:
            component: Filter logs by component
            level: Filter logs by level

        Returns:
            List[LogEntry]: List of log entries
        """
        # Get last 100 logs
        raw_logs = self.log_manager.tail_logs(n=100)

        # Convert and filter logs
        filtered_logs: list[LogEntry] = []
        for raw_log in raw_logs:
            log_entry: LogEntry = {
                "timestamp": raw_log["timestamp"],
                "level": raw_log["level"],
                "component": raw_log["component"],
                "message": raw_log["message"],
            }
            if component and log_entry["component"] != component:
                continue
            if level and log_entry["level"] != level:
                continue
            filtered_logs.append(log_entry)

        return filtered_logs
