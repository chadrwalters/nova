"""Section renderers for Nova CLI output."""

from abc import ABC, abstractmethod
from typing import Any, cast

from rich.console import RenderableType
from rich.panel import Panel
from rich.style import Style
from rich.table import Table
from rich.text import Text

from nova.cli.formatting.base import Section
from nova.monitoring.warnings import Warning


class BaseSection(Section, ABC):
    """Base section renderer."""

    def __init__(self, title: str, style: str | None = None):
        """Initialize section.

        Args:
            title: Section title
            style: Optional style name
        """
        self.title = title
        self.style = Style(color=style) if style else None

    @abstractmethod
    def render(self, data: Any) -> RenderableType:
        """Render section with data.

        Args:
            data: Data to render

        Returns:
            RenderableType: Rich renderable object
        """
        pass


class MemorySection(BaseSection):
    """Memory status section renderer."""

    def render(self, data: dict[str, str | float]) -> RenderableType:
        """Render memory status.

        Args:
            data: Memory status data

        Returns:
            RenderableType: Rich renderable object
        """
        table = Table(title=self.title, style=self.style)
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row(
            "Current Usage",
            f"{float(data['current_mb']):.1f}MB",
        )
        table.add_row(
            "Peak Usage",
            f"{float(data['peak_mb']):.1f}MB",
        )
        table.add_row(
            "Status",
            str(data["status"]),
        )

        return table


class DiskSection(BaseSection):
    """Disk status section renderer."""

    def render(self, data: dict[str, str | float]) -> RenderableType:
        """Render disk status.

        Args:
            data: Disk status data

        Returns:
            RenderableType: Rich renderable object
        """
        table = Table(title=self.title, style=self.style)
        table.add_column("Metric")
        table.add_column("Value")

        table.add_row(
            "Used Space",
            f"{float(data['used_percent']):.1f}%",
        )
        table.add_row(
            "Free Space",
            f"{float(data['free_gb']):.1f}GB",
        )
        table.add_row(
            "Status",
            str(data["status"]),
        )

        return table


class DirectorySection(BaseSection):
    """Directory status section renderer."""

    def render(self, data: dict[str, str]) -> RenderableType:
        """Render directory status.

        Args:
            data: Directory status data

        Returns:
            RenderableType: Rich renderable object
        """
        table = Table(title=self.title, style=self.style)
        table.add_column("Directory")
        table.add_column("Status")

        for directory, status in data.items():
            table.add_row(directory, status)

        return table


class WarningSection(BaseSection):
    """Warning section renderer."""

    def render(self, data: list[Warning]) -> RenderableType:
        """Render warnings.

        Args:
            data: List of warnings

        Returns:
            RenderableType: Rich renderable object
        """
        if not data:
            return Text("No warnings", style=Style(color="green"))

        table = Table(title=self.title, style=self.style)
        table.add_column("Severity")
        table.add_column("Category")
        table.add_column("Message")
        table.add_column("Details")

        for warning in data:
            table.add_row(
                warning.severity.value.upper(),
                warning.category.value,
                warning.message,
                ", ".join(f"{k}={v}" for k, v in (warning.details or {}).items()),
            )

        return table


class StatsSection(BaseSection):
    """Statistics section renderer."""

    def render(self, data: dict[str, dict[str, int | float]]) -> RenderableType:
        """Render statistics.

        Args:
            data: Statistics data

        Returns:
            RenderableType: Rich renderable object
        """
        table = Table(title=self.title, style=self.style)
        table.add_column("Category")
        table.add_column("Metric")
        table.add_column("Value")

        for category, stats in data.items():
            for metric, value in stats.items():
                if isinstance(value, (int, float)):
                    table.add_row(
                        category,
                        metric.replace("_", " ").title(),
                        f"{value:,}",
                    )

        return table


class SummarySection(BaseSection):
    """Summary section renderer."""

    def render(self, data: dict[str, Any]) -> RenderableType:
        """Render summary.

        Args:
            data: Summary data

        Returns:
            RenderableType: Rich renderable object
        """
        table = Table(title=self.title, style=self.style)
        table.add_column("Component")
        table.add_column("Status")
        table.add_column("Details")

        # System Health
        health = cast(dict[str, str], data.get("health", {}))
        table.add_row(
            "System Health",
            health.get("status", "unknown"),
            health.get("message", "No health data available"),
        )

        # Warnings
        warnings = cast(list[Warning], data.get("warnings", []))
        active_warnings = len([w for w in warnings if not w.resolved])
        table.add_row(
            "Warnings",
            "critical" if active_warnings > 0 else "healthy",
            f"{active_warnings} active warning(s)",
        )

        # Vector Store
        store = cast(dict[str, int], data.get("vector_store", {}))
        table.add_row(
            "Vector Store",
            "healthy",
            f"{store.get('total_documents', 0):,} documents, "
            f"{store.get('total_chunks', 0):,} chunks",
        )

        return Panel(table, title=self.title, style=self.style)
