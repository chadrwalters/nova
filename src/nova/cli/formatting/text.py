"""Text formatter for Nova CLI output."""

from datetime import datetime
from typing import Any, cast

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.table import Table

from nova.cli.formatting.base import BaseFormatter, HealthData, StatsData
from nova.monitoring.warnings import Warning, WarningCategory, WarningSeverity


class TextFormatter(BaseFormatter):
    """Text formatter for Nova CLI output."""

    def format_health(self, health_data: HealthData) -> RenderableType:
        """Format health status data.

        Args:
            health_data: Health status data

        Returns:
            RenderableType: Rich renderable object
        """
        status_table = self._create_table(
            "System Health Status",
            "Component",
            "Status",
            "Details",
        )

        # Memory Status
        memory = cast(dict[str, str | float], health_data["memory"])
        status_table.add_row(
            self._style_text("Memory", "header"),
            self._style_text(str(memory["status"]), str(memory["status"])),
            self._style_text(
                f"Current: {float(memory['current_mb']):.1f}MB, Peak: {float(memory['peak_mb']):.1f}MB",
                "value",
            ),
        )

        # Disk Status
        disk = cast(dict[str, str | float], health_data["disk"])
        status_table.add_row(
            self._style_text("Disk", "header"),
            self._style_text(str(disk["status"]), str(disk["status"])),
            self._style_text(
                f"Used: {float(disk['used_percent']):.1f}%, Free: {float(disk['free_gb']):.1f}GB",
                "value",
            ),
        )

        # CPU Status
        cpu_percent = float(health_data["cpu_percent"])
        cpu_status = "healthy" if cpu_percent < 80 else "warning"
        status_table.add_row(
            self._style_text("CPU", "header"),
            self._style_text(cpu_status, cpu_status),
            self._style_text(f"Usage: {cpu_percent:.1f}%", "value"),
        )

        # Directory Status
        directories = cast(dict[str, str], health_data["directories"])
        dir_status = "healthy"
        dir_details = []
        for dir_name, status in directories.items():
            if status != "healthy":
                dir_status = "warning"
                dir_details.append(f"{dir_name}={status}")

        status_table.add_row(
            self._style_text("Directories", "header"),
            self._style_text(dir_status, dir_status),
            self._style_text(
                ", ".join(dir_details) if dir_details else "All directories OK",
                "value",
            ),
        )

        # Overall Status
        status_table.add_row(
            self._style_text("Overall Status", "header"),
            self._style_text(str(health_data["status"]), str(health_data["status"])),
            self._style_text(f"Last checked: {health_data['timestamp']}", "value"),
        )

        return Panel(
            status_table,
            title="System Health Status",
            subtitle=f"Last updated: {datetime.now().strftime('%H:%M:%S')}",
        )

    def format_warnings(
        self,
        warnings: list[Warning],
        show_history: bool = False,
        group_by: str | None = None,
    ) -> RenderableType:
        """Format warning data.

        Args:
            warnings: List of warnings
            show_history: Whether to show warning history
            group_by: Optional grouping field (category/severity)

        Returns:
            RenderableType: Rich renderable object
        """
        if not warnings:
            return self._style_text("No warnings found with the specified filters.", "healthy")

        if group_by == "category":
            return self._format_warnings_by_category(warnings, show_history)
        elif group_by == "severity":
            return self._format_warnings_by_severity(warnings, show_history)
        else:
            return self._format_warnings_flat(warnings, show_history)

    def format_stats(self, stats_data: StatsData, verbose: bool = False) -> RenderableType:
        """Format statistics data.

        Args:
            stats_data: Statistics data
            verbose: Whether to show detailed statistics

        Returns:
            RenderableType: Rich renderable object
        """
        # Document Statistics
        doc_stats = cast(dict[str, dict[str, int]], stats_data["documents"])
        doc_table = self._create_table("Document Statistics", "Metric", "Value")
        doc_table.add_row(
            self._style_text("Total Documents", "header"),
            self._style_text(str(doc_stats["total_count"]), "value"),
        )
        doc_table.add_row(
            self._style_text("Document Types", "header"),
            self._style_text(
                ", ".join(f"{k}={v}" for k, v in doc_stats["type_counts"].items()),
                "value",
            ),
        )
        doc_table.add_row(
            self._style_text("Size Distribution", "header"),
            self._style_text(
                ", ".join(f"{k}={v}" for k, v in doc_stats["size_distribution"].items()),
                "value",
            ),
        )
        doc_table.add_row(
            self._style_text("Average Size", "header"),
            self._style_text(f"{doc_stats['avg_size']:.2f} bytes", "value"),
        )

        # Chunk Statistics
        chunk_stats = cast(dict[str, dict[str, int]], stats_data["chunks"])
        chunk_table = self._create_table("Chunk Statistics", "Metric", "Value")
        chunk_table.add_row(
            self._style_text("Total Chunks", "header"),
            self._style_text(str(chunk_stats["total_count"]), "value"),
        )
        chunk_table.add_row(
            self._style_text("Average per Document", "header"),
            self._style_text(f"{chunk_stats['avg_per_document']:.2f}", "value"),
        )
        chunk_table.add_row(
            self._style_text("Size Distribution", "header"),
            self._style_text(
                ", ".join(f"{k}={v}" for k, v in chunk_stats["size_distribution"].items()),
                "value",
            ),
        )

        # Tag Statistics
        tag_stats = cast(dict[str, dict[str, int]], stats_data["tags"])
        tag_table = self._create_table("Tag Statistics", "Metric", "Value")
        tag_table.add_row(
            self._style_text("Total Tags", "header"),
            self._style_text(str(tag_stats["total_count"]), "value"),
        )
        tag_table.add_row(
            self._style_text("Unique Tags", "header"),
            self._style_text(str(tag_stats["unique_count"]), "value"),
        )
        tag_table.add_row(
            self._style_text("Top Tags", "header"),
            self._style_text(
                ", ".join(f"{k}={v}" for k, v in tag_stats["top_tags"].items()),
                "value",
            ),
        )

        if verbose:
            tag_table.add_row(
                self._style_text("Top Co-occurrences", "header"),
                self._style_text(
                    ", ".join(f"{k}={v}" for k, v in tag_stats["top_co_occurrences"].items()),
                    "value",
                ),
            )

        return Group(doc_table, chunk_table, tag_table)

    def _format_warnings_by_category(self, warnings: list[Warning], show_history: bool) -> Table:
        """Format warnings grouped by category.

        Args:
            warnings: List of warnings
            show_history: Whether to show warning history

        Returns:
            Table: Rich table instance
        """
        categories = {category.value: [] for category in WarningCategory}
        for warning in warnings:
            categories[warning.category.value].append(warning)

        table = self._create_table(
            "Warnings by Category",
            "Category",
            "Count",
            "Details",
            style="warning",
        )

        for category, category_warnings in categories.items():
            if category_warnings:
                details = [
                    f"{w.severity.value}: {w.message}"
                    for w in sorted(
                        category_warnings,
                        key=lambda w: WarningSeverity[w.severity.value].value,
                        reverse=True,
                    )
                ]
                table.add_row(
                    self._style_text(category, "header"),
                    self._style_text(str(len(category_warnings)), "value"),
                    self._style_text("\n".join(details), "detail"),
                )

        return table

    def _format_warnings_by_severity(self, warnings: list[Warning], show_history: bool) -> Table:
        """Format warnings grouped by severity.

        Args:
            warnings: List of warnings
            show_history: Whether to show warning history

        Returns:
            Table: Rich table instance
        """
        severities = {severity.value: [] for severity in WarningSeverity}
        for warning in warnings:
            severities[warning.severity.value].append(warning)

        table = self._create_table(
            "Warnings by Severity",
            "Severity",
            "Count",
            "Details",
            style="warning",
        )

        for severity, severity_warnings in severities.items():
            if severity_warnings:
                details = [
                    f"{w.category.value}: {w.message}"
                    for w in sorted(
                        severity_warnings,
                        key=lambda w: w.category.value,
                    )
                ]
                table.add_row(
                    self._style_text(severity.upper(), severity.lower()),
                    self._style_text(str(len(severity_warnings)), "value"),
                    self._style_text("\n".join(details), "detail"),
                )

        return table

    def _format_warnings_flat(self, warnings: list[Warning], show_history: bool) -> Table:
        """Format warnings in a flat list.

        Args:
            warnings: List of warnings
            show_history: Whether to show warning history

        Returns:
            Table: Rich table instance
        """
        table = self._create_table(
            "Active Warnings" if not show_history else "Warning History",
            "Timestamp",
            "Severity",
            "Category",
            "Message",
            "Details",
            style="warning",
        )

        for warning in warnings:
            if warning.timestamp is None:
                continue

            row = [
                self._style_text(warning.timestamp.strftime("%Y-%m-%d %H:%M:%S"), "detail"),
                self._style_text(warning.severity.value.upper(), warning.severity.value.lower()),
                self._style_text(warning.category.value, "header"),
                self._style_text(warning.message, "value"),
                self._style_text(
                    ", ".join(f"{k}={v}" for k, v in (warning.details or {}).items()),
                    "detail",
                ),
            ]

            if show_history and hasattr(warning, "resolved_at"):
                resolution = "Active"
                if warning.resolved and warning.resolved_at is not None:
                    resolution = f"Resolved at {warning.resolved_at.strftime('%Y-%m-%d %H:%M:%S')}"
                row.append(self._style_text(resolution, "info"))

            table.add_row(*row)

        return table


def format_float(value: str | float | dict[str, Any]) -> float:
    """Format a value as float.

    Args:
        value: Value to format

    Returns:
        float: Formatted value
    """
    if isinstance(value, (int, float)):
        return float(value)
    elif isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    elif isinstance(value, dict):
        try:
            return float(value.get("value", 0.0))
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def format_categories(categories: dict[str, int]) -> str:
    """Format warning categories.

    Args:
        categories: Warning categories and their counts

    Returns:
        str: Formatted categories
    """
    if not categories:
        return "No categories"

    parts = []
    for category, count in categories.items():
        parts.append(f"{category}: {count}")
    return ", ".join(parts)


def format_severities(severities: dict[str, int]) -> str:
    """Format warning severities.

    Args:
        severities: Warning severities and their counts

    Returns:
        str: Formatted severities
    """
    if not severities:
        return "No severities"

    parts = []
    for severity, count in severities.items():
        parts.append(f"{severity}: {count}")
    return ", ".join(parts)
