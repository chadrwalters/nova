"""Error reporting functionality."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
import logging

from rich.console import Console
from rich.table import Table
from rich.text import Text


@dataclass
class ErrorReport:
    """Error report details."""
    source: str
    function: str
    line: int
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_warning: bool = False


class ErrorReporter:
    """Reports and formats error messages."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize error reporter.
        
        Args:
            console: Optional rich console instance
        """
        self.console = console or Console()
        self.errors: List[ErrorReport] = []
        self.warnings: List[ErrorReport] = []
        
    def add_error(
        self,
        message: str,
        source: str,
        function: str,
        line: int
    ) -> None:
        """Add an error report.
        
        Args:
            message: Error message
            source: Source file or component
            function: Function name
            line: Line number
        """
        self.errors.append(ErrorReport(
            message=message,
            source=source,
            function=function,
            line=line,
            is_warning=False
        ))
        
    def add_warning(
        self,
        message: str,
        source: str,
        function: str,
        line: int
    ) -> None:
        """Add a warning report.
        
        Args:
            message: Warning message
            source: Source file or component
            function: Function name
            line: Line number
        """
        self.warnings.append(ErrorReport(
            message=message,
            source=source,
            function=function,
            line=line,
            is_warning=True
        ))
        
    def get_error_count(self) -> int:
        """Get total number of errors.
        
        Returns:
            Number of errors
        """
        return len(self.errors)
        
    def get_warning_count(self) -> int:
        """Get total number of warnings.
        
        Returns:
            Number of warnings
        """
        return len(self.warnings)
        
    def get_error_summary(self) -> Table:
        """Get error summary table.
        
        Returns:
            Rich table with error summary
        """
        table = Table(title="Error Summary", show_header=True)
        table.add_column("Time", style="dim")
        table.add_column("Type", style="bold")
        table.add_column("Source", style="cyan")
        table.add_column("Function", style="blue")
        table.add_column("Line", style="magenta")
        table.add_column("Message", style="red")
        
        for error in sorted(
            self.errors + self.warnings,
            key=lambda x: x.timestamp
        ):
            table.add_row(
                error.timestamp.strftime("%H:%M:%S"),
                "Warning" if error.is_warning else "Error",
                error.source,
                error.function,
                str(error.line),
                error.message
            )
            
        return table
        
    def display_summary(self) -> None:
        """Display error summary."""
        if not self.errors and not self.warnings:
            self.console.print("\nNo errors or warnings to report.", style="green")
            return
            
        self.console.print("\nError Summary:", style="bold red")
        self.console.print(f"  Errors: {self.get_error_count()}")
        self.console.print(f"  Warnings: {self.get_warning_count()}")
        
        if self.errors or self.warnings:
            self.console.print(self.get_error_summary())
            
    def clear(self) -> None:
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear() 