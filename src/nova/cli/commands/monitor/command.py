"""Monitor command for Nova system."""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import (
    Any,
    TypeVar,
    Union,
    cast,
)

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from nova.cli.utils.command import NovaCommand
from nova.config import load_config
from nova.monitoring.logs import LogManager
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.session import SessionHealthData, SessionMonitor
from nova.monitoring.warnings import (
    HealthWarningSystem,
    WarningCategory,
    WarningSeverity,
)
from nova.vector_store.store import VectorStore

logger: logging.Logger = logging.getLogger(__name__)

# Type variable for click command function
F = TypeVar("F", bound=Callable[..., Any])

# Type hints for health status dictionaries
MemoryStatus = dict[str, str | float]
DiskStatus = dict[str, str | float]
DirectoryStatus = dict[str, str]
HealthStatus = dict[str, str | float | dict[str, str | float] | dict[str, str]]

# Type hints for conversion functions
ConvertibleToFloat = Union[str, int, float]
ConvertibleToInt = Union[str, int, float]


def get_float(value: ConvertibleToFloat) -> float:
    """Convert a value to float.

    Args:
        value: Value to convert

    Returns:
        float: Converted value
    """
    if isinstance(value, (int, float)):
        return float(value)
    return float(value)


def get_int(value: ConvertibleToInt) -> int:
    """Convert a value to int.

    Args:
        value: Value to convert

    Returns:
        int: Converted value
    """
    if isinstance(value, int):
        return value
    return int(float(value))


def get_dict_value(d: dict[str, Any], key: str) -> str | int | float:
    """Get a value from a dictionary, ensuring it's a primitive type.

    Args:
        d: Dictionary to get value from
        key: Key to get value for

    Returns:
        Union[str, int, float]: The value
    """
    value = d[key]
    if isinstance(value, (str, int, float)):
        return value
    raise ValueError(f"Value for key {key} is not a primitive type: {type(value)}")


def get_collection_info(collection: dict[str, Any]) -> dict[str, Any]:
    """Get collection information.

    Args:
        collection: Collection data

    Returns:
        Dict[str, Any]: Collection information
    """
    return {
        "name": collection.get("name", "unknown"),
        "count": collection.get("count", 0),
        "embeddings": collection.get("embeddings", 0),
        "size": collection.get("size", 0),
    }


class MonitorCommand(NovaCommand):
    """Monitor command for nova CLI."""

    name = "monitor"
    help = "Monitor system status and performance"

    def __init__(self) -> None:
        """Initialize monitor command."""
        super().__init__()
        self.config = load_config()
        self.console = Console()

        # Initialize vector store with correct path
        self.vector_store = VectorStore(base_path=str(self.config.paths.vector_store_dir))

        # Initialize system monitor with vector store
        self.system_monitor = SessionMonitor(vector_store=self.vector_store)
        self.persistent_monitor = PersistentMonitor(base_path=self.config.paths.state_dir)
        self.warning_system = HealthWarningSystem(base_path=self.config.paths.state_dir)

        # Initialize monitors
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
        @click.option(
            "--watch",
            is_flag=True,
            help="Watch mode: continuously update health status",
        )
        @click.option(
            "--no-color",
            is_flag=True,
            help="Disable colored output",
        )
        @click.option(
            "--format",
            type=click.Choice(["text", "json"]),
            default="text",
            help="Output format",
        )
        @click.option(
            "--verbose",
            is_flag=True,
            help="Show detailed statistics and health information",
        )
        def health(watch: bool, no_color: bool, format: str, verbose: bool) -> None:
            """Show system health status and statistics."""
            if watch:
                with Live(
                    self._get_health_panel(verbose=verbose),
                    refresh_per_second=2,
                    console=self.console,
                ) as live:
                    try:
                        while True:
                            live.update(self._get_health_panel(verbose=verbose))
                    except KeyboardInterrupt:
                        pass
            else:
                self.check_health(no_color=no_color, format=format, verbose=verbose)

        @monitor.command()
        @click.option(
            "--category",
            type=click.Choice([c.value for c in WarningCategory]),
            help="Filter warnings by category",
        )
        @click.option(
            "--severity",
            type=click.Choice([s.value for s in WarningSeverity]),
            help="Filter warnings by severity",
        )
        @click.option(
            "--history",
            is_flag=True,
            help="Show warning history",
        )
        @click.option(
            "--limit",
            type=int,
            default=10,
            help="Maximum number of warnings to show",
        )
        def warnings(
            category: str | None,
            severity: str | None,
            history: bool,
            limit: int,
        ) -> None:
            """Show system warnings."""
            self.show_warnings(
                category=WarningCategory(category) if category else None,
                severity=WarningSeverity(severity) if severity else None,
                show_history=history,
                limit=limit,
            )

        return monitor

    def _get_health_panel(self, verbose: bool = False) -> Panel:
        """Get health status panel.

        Args:
            verbose: Whether to include verbose output

        Returns:
            Panel containing health status
        """
        logger.info("Getting current statistics")
        health_status = self.system_monitor.check_health()
        grid = Table.grid()

        # Add health table
        grid.add_row(self._create_health_table(cast(dict[str, Any], health_status)))

        # Add stats table if verbose
        if verbose:
            grid.add_row(self._create_stats_table(cast(dict[str, Any], health_status)))

        return Panel(
            grid,
            title="System Health",
            subtitle=f"Last checked: {datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}",
        )

    def check_health(
        self, no_color: bool = False, format: str = "text", verbose: bool = False
    ) -> None:
        """Check and display system health status.

        Args:
            no_color: Whether to disable colored output
            format: Output format (text/json)
            verbose: Whether to show detailed statistics
        """
        # Get health data
        health_data = self._get_health_data(verbose=verbose)

        if format == "json":
            self.console.print_json(data=health_data)
        else:
            self.console.print(self._get_health_panel(verbose=verbose))

    def _create_health_table(self, health_status: dict[str, Any]) -> Table:
        """Create health status table.

        Args:
            health_status: Health status information

        Returns:
            Rich table with health status
        """
        table = Table(title="System Health Status")
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Details")

        # Memory status
        memory = health_status["memory"]
        memory_details = (
            f"Current: {memory['current_memory_mb']:.2f}MB, "
            f"Peak: {memory['peak_memory_mb']:.2f}MB, "
            f"Available: {memory['available_memory_mb']:.2f}MB"
        )
        table.add_row("Memory", self._format_status(memory["status"]), memory_details)

        # Vector store status
        vector_details = []
        if "collection" in health_status:
            count = health_status["collection"].get("count", 0)
            vector_details.append(f"Documents: {count}")
            if health_status["collection"].get("exists", False):
                vector_details.append("Collection: exists")
            else:
                vector_details.append("Collection: missing")

        # Get vector store status
        vector_status = "healthy"
        if health_status.get("status") == "error":
            vector_status = "error"
            if "error" in health_status:
                vector_details.append(f"Error: {health_status['error']}")

        table.add_row(
            "Vector Store",
            self._format_status(vector_status),
            ", ".join(vector_details) if vector_details else "",
        )

        # Monitor status
        table.add_row("Monitor", self._format_status(health_status["monitor"]), "")

        # Logs status
        table.add_row("Logs", self._format_status(health_status["logs"]), "")

        # Overall status
        overall_status = "healthy"
        if vector_status == "error":
            overall_status = "error"

        table.add_row(
            "Overall",
            self._format_status(overall_status),
            f"Session uptime: {health_status['session_uptime']:.1f}s",
        )

        return table

    def _create_stats_table(self, health_status: dict[str, Any]) -> Table:
        """Create a table showing document statistics."""
        grid = Table.grid()

        # Get repository stats
        repository = health_status.get("repository", {})
        collection = health_status.get("collection", {})

        # Document Statistics
        doc_table = Table(title="Document Statistics")
        doc_table.add_column("Metric")
        doc_table.add_column("Value")

        # Add database status with error if present
        status = "disconnected"
        if health_status.get("status") == "healthy":
            status = "connected"
        elif health_status.get("status") == "error":
            status = f"error: {health_status.get('error', 'Unknown error')}"
        elif collection.get("exists", False):
            status = "connected"
        doc_table.add_row("Database Status", status)

        # Add basic document stats
        doc_table.add_row("Total Documents", str(collection.get("count", 0)))
        doc_table.add_row("Document Types", str(repository.get("file_types", {})))
        doc_table.add_row("Size Distribution", "Calculated on demand")
        doc_table.add_row("Average Size", "Calculated on demand")

        # Chunk Statistics
        chunk_table = Table(title="Chunk Statistics")
        chunk_table.add_column("Metric")
        chunk_table.add_column("Value")

        chunk_table.add_row("Total Chunks", str(repository.get("total_chunks", 0)))
        chunk_table.add_row("Unique Sources", str(repository.get("unique_sources", 0)))
        chunk_table.add_row("File Types", str(repository.get("file_types", {})))

        # Tag Statistics
        tag_table = Table(title="Tag Statistics")
        tag_table.add_column("Metric")
        tag_table.add_column("Value")

        tag_stats = repository.get("tags", {})
        tag_table.add_row("Total Tags", str(tag_stats.get("total", 0)))
        tag_table.add_row("Unique Tags", str(tag_stats.get("unique", 0)))
        tag_table.add_row("Tag List", str(tag_stats.get("list", [])))

        grid.add_row(doc_table)
        grid.add_row(chunk_table)
        grid.add_row(tag_table)

        return grid

    def _format_status(self, status: str) -> str:
        """Format status string with appropriate color.

        Args:
            status: Status string to format

        Returns:
            Formatted status string
        """
        status = status.lower()
        if status in ["healthy", "ok"]:
            return "[green]healthy[/green]"
        elif status in ["warning", "degraded"]:
            return "[yellow]degraded[/yellow]"
        elif "error" in status:
            return f"[red]{status}[/red]"
        else:
            return "[red]critical[/red]"

    def show_warnings(
        self,
        category: WarningCategory | None = None,
        severity: WarningSeverity | None = None,
        show_history: bool = False,
        limit: int = 10,
    ) -> None:
        """Show system warnings.

        Args:
            category: Filter warnings by category
            severity: Filter warnings by severity
            show_history: Show warning history
            limit: Maximum number of warnings to show
        """
        if show_history:
            warnings = self.warning_system.get_warning_history(
                category=category,
                severity=severity,
                limit=limit,
            )
            title = "Warning History"
        else:
            warnings = self.warning_system.get_active_warnings(
                category=category,
                severity=severity,
            )
            title = "Active Warnings"

        if not warnings:
            self.console.print(
                f"[green]No {title.lower()} found with the specified filters.[/green]"
            )
            return

        warning_table = Table(title=title)
        warning_table.add_column("Timestamp", style="cyan")
        warning_table.add_column("Severity", style="red")
        warning_table.add_column("Category", style="yellow")
        warning_table.add_column("Message", style="white")
        warning_table.add_column("Details", style="blue")
        if show_history:
            warning_table.add_column("Resolution", style="green")

        for warning in warnings:
            if warning.timestamp is None:
                continue

            row = [
                warning.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                warning.severity.value.upper(),
                warning.category.value,
                warning.message,
                ", ".join(f"{k}={v}" for k, v in (warning.details or {}).items()),
            ]
            if show_history:
                resolution = "Active"
                if warning.resolved and warning.resolved_at is not None:
                    resolution = f"Resolved at {warning.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}"
                row.append(resolution)
            warning_table.add_row(*row)

        self.console.print(warning_table)

    def _get_health_data(self, verbose: bool = False) -> dict[str, Any]:
        """Get health data for all components."""
        # Get memory stats from session monitor
        session_health = cast(SessionHealthData, self.system_monitor.check_health())
        vector_health = self.vector_store.check_health()

        health_data = {
            "status": "healthy",  # Overall status
            "memory": session_health["memory"],
            "vector_store": vector_health,  # Return full vector health data
            "monitor": {
                "status": "healthy",
                "last_check": datetime.now().isoformat(),
            },
            "logs": {
                "status": "healthy",
                "directory": str(self.config.paths.logs_dir),
            },
            "session_uptime": session_health.get("uptime", 0.0),
        }

        # Update overall status based on component health
        if any(
            component.get("status", "healthy") != "healthy"
            for component in [
                session_health["memory"],
                vector_health,
                health_data["monitor"],
                health_data["logs"],
            ]
        ):
            health_data["status"] = "degraded"

        return health_data
