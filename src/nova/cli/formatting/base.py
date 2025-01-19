"""Base formatter interface for Nova CLI output."""

from abc import ABC, abstractmethod
from typing import Any, Protocol

from rich.console import Console, RenderableType
from rich.style import Style, StyleType
from rich.table import Table
from rich.text import Text

from nova.monitoring.warnings import Warning

# Type hints for health status dictionaries
HealthData = dict[str, str | float | dict[str, str | float] | dict[str, str]]
StatsData = dict[str, dict[str, int | float] | dict[str, dict[str, int]]]


class Section(Protocol):
    """Protocol for section renderers."""

    def render(self, data: Any) -> RenderableType:
        """Render the section with provided data.

        Args:
            data: Data to render

        Returns:
            RenderableType: Rich renderable object
        """
        ...


class BaseFormatter(ABC):
    """Base formatter interface for Nova CLI output."""

    def __init__(self, console: Console, color_scheme: dict[str, str] | None = None):
        """Initialize the formatter.

        Args:
            console: Rich console instance
            color_scheme: Optional color scheme override
        """
        self.console = console
        self.color_scheme = color_scheme or self._default_color_scheme()
        self.sections: dict[str, Section] = {}

    @abstractmethod
    def format_health(self, health_data: HealthData) -> RenderableType:
        """Format health status data.

        Args:
            health_data: Health status data

        Returns:
            RenderableType: Rich renderable object
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    def format_stats(self, stats_data: StatsData, verbose: bool = False) -> RenderableType:
        """Format statistics data.

        Args:
            stats_data: Statistics data
            verbose: Whether to show detailed statistics

        Returns:
            RenderableType: Rich renderable object
        """
        pass

    def add_section(self, name: str, section: Section) -> None:
        """Add a section renderer.

        Args:
            name: Section name
            section: Section renderer
        """
        self.sections[name] = section

    def remove_section(self, name: str) -> None:
        """Remove a section renderer.

        Args:
            name: Section name
        """
        self.sections.pop(name, None)

    def _default_color_scheme(self) -> dict[str, str]:
        """Get default color scheme.

        Returns:
            Dict[str, str]: Default color scheme
        """
        return {
            "healthy": "green",
            "warning": "yellow",
            "critical": "red",
            "info": "blue",
            "header": "cyan",
            "value": "white",
            "detail": "bright_black",
        }

    def _create_table(
        self,
        title: str | None = None,
        *column_names: str,
        style: str | None = None,
    ) -> Table:
        """Create a styled table.

        Args:
            title: Optional table title
            *column_names: Column names
            style: Optional style name from color scheme

        Returns:
            Table: Rich table instance
        """
        table = Table(
            title=title,
            title_style=Style(color=self.color_scheme["header"]) if title else None,
            style=Style(color=self.color_scheme.get(style, "white")) if style else None,
        )
        for name in column_names:
            table.add_column(name, style=Style(color=self.color_scheme["header"]))
        return table

    def _style_text(self, text: str, style_name: str) -> Text:
        """Style text using color scheme.

        Args:
            text: Text to style
            style_name: Style name from color scheme

        Returns:
            Text: Rich text instance
        """
        return Text(text, style=Style(color=self.color_scheme.get(style_name, "white")))

    def create_table(self, style: StyleType | None = None) -> Table:
        """Create a table with the given style.

        Args:
            style: Table style

        Returns:
            Table: The created table
        """
        return Table(style=style or "")
