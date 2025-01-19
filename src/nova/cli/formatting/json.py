"""JSON formatter for Nova CLI output."""

import json
from typing import Any

from rich.console import RenderableType
from rich.syntax import Syntax

from nova.cli.formatting.base import BaseFormatter, HealthData, StatsData
from nova.monitoring.warnings import Warning


class JSONFormatter(BaseFormatter):
    """JSON formatter for Nova CLI output."""

    def format_health(self, health_data: HealthData) -> RenderableType:
        """Format health status data.

        Args:
            health_data: Health status data

        Returns:
            RenderableType: Rich renderable object
        """
        return self._format_json(health_data)

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
            return self._format_json({"warnings": [], "count": 0})

        warning_data = []
        for warning in warnings:
            warning_dict = {
                "timestamp": warning.timestamp.isoformat() if warning.timestamp else None,
                "severity": warning.severity.value,
                "category": warning.category.value,
                "message": warning.message,
                "details": warning.details or {},
            }
            if show_history and hasattr(warning, "resolved_at"):
                warning_dict["resolved"] = warning.resolved
                warning_dict["resolved_at"] = (
                    warning.resolved_at.isoformat()
                    if warning.resolved and warning.resolved_at
                    else None
                )
            warning_data.append(warning_dict)

        if group_by == "category":
            grouped_data = self._group_warnings_by_category(warning_data)
        elif group_by == "severity":
            grouped_data = self._group_warnings_by_severity(warning_data)
        else:
            grouped_data = {"warnings": warning_data, "count": len(warning_data)}

        return self._format_json(grouped_data)

    def format_stats(self, stats_data: StatsData, verbose: bool = False) -> RenderableType:
        """Format statistics data.

        Args:
            stats_data: Statistics data
            verbose: Whether to show detailed statistics

        Returns:
            RenderableType: Rich renderable object
        """
        if not verbose:
            # Filter out verbose data
            filtered_data = {}
            for category, stats in stats_data.items():
                filtered_data[category] = {
                    k: v
                    for k, v in stats.items()
                    if not k.startswith("detailed_") and k != "top_co_occurrences"
                }
            return self._format_json(filtered_data)
        return self._format_json(stats_data)

    def _format_json(self, data: Any) -> RenderableType:
        """Format data as syntax-highlighted JSON.

        Args:
            data: Data to format

        Returns:
            RenderableType: Rich renderable object
        """
        json_str = json.dumps(data, indent=2, sort_keys=True)
        return Syntax(json_str, "json", theme="monokai")

    def _group_warnings_by_category(self, warnings: list[dict[str, Any]]) -> dict[str, Any]:
        """Group warnings by category.

        Args:
            warnings: List of warning dictionaries

        Returns:
            Dict[str, Any]: Grouped warnings
        """
        grouped: dict[str, list[dict[str, Any]]] = {}
        for warning in warnings:
            category = warning["category"]
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(warning)

        return {
            "by_category": {
                category: {
                    "warnings": category_warnings,
                    "count": len(category_warnings),
                }
                for category, category_warnings in grouped.items()
            },
            "total_count": len(warnings),
        }

    def _group_warnings_by_severity(self, warnings: list[dict[str, Any]]) -> dict[str, Any]:
        """Group warnings by severity.

        Args:
            warnings: List of warning dictionaries

        Returns:
            Dict[str, Any]: Grouped warnings
        """
        grouped: dict[str, list[dict[str, Any]]] = {}
        for warning in warnings:
            severity = warning["severity"]
            if severity not in grouped:
                grouped[severity] = []
            grouped[severity].append(warning)

        return {
            "by_severity": {
                severity: {
                    "warnings": severity_warnings,
                    "count": len(severity_warnings),
                }
                for severity, severity_warnings in grouped.items()
            },
            "total_count": len(warnings),
        }
