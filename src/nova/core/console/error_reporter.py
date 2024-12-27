"""Error reporting functionality for Nova."""

import sys
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .color_scheme import ColorScheme

@dataclass
class ErrorContext:
    """Context information for an error."""
    phase: str
    operation: str
    file: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ErrorReport:
    """Detailed error report."""
    error: Exception
    context: ErrorContext
    traceback: str
    suggestions: List[str] = field(default_factory=list)

class ErrorReporter:
    """Handles error reporting and tracking."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize error reporter.
        
        Args:
            console: Optional rich console
        """
        self.console = console or Console(theme=ColorScheme.get_theme())
        self.errors: List[ErrorReport] = []
    
    def capture_error(
        self,
        error: Exception,
        phase: str,
        operation: str,
        file: Optional[str] = None,
        **details: Any
    ) -> ErrorReport:
        """Capture error with context.
        
        Args:
            error: Exception that occurred
            phase: Processing phase
            operation: Operation being performed
            file: Optional file being processed
            **details: Additional error details
            
        Returns:
            Error report object
        """
        context = ErrorContext(
            phase=phase,
            operation=operation,
            file=file,
            details=details
        )
        
        report = ErrorReport(
            error=error,
            context=context,
            traceback=traceback.format_exc()
        )
        
        # Add suggestions based on error type
        self._add_suggestions(report)
        
        self.errors.append(report)
        return report
    
    def _add_suggestions(self, report: ErrorReport):
        """Add helpful suggestions based on error type.
        
        Args:
            report: Error report to add suggestions to
        """
        error = report.error
        
        if isinstance(error, FileNotFoundError):
            report.suggestions.extend([
                "Check if the file exists at the specified path",
                "Verify file permissions",
                "Check for typos in the file path"
            ])
        elif isinstance(error, PermissionError):
            report.suggestions.extend([
                "Check file and directory permissions",
                "Run with elevated privileges if needed",
                "Verify ownership of files and directories"
            ])
        elif isinstance(error, ValueError):
            report.suggestions.extend([
                "Check input data format",
                "Verify configuration values",
                "Review documentation for correct usage"
            ])
    
    def display_error(self, report: ErrorReport):
        """Display error report.
        
        Args:
            report: Error report to display
        """
        # Create error panel
        error_text = [
            Text("Error Details:", style="error"),
            Text(f"  Type: {type(report.error).__name__}", style="error"),
            Text(f"  Message: {str(report.error)}", style="error"),
            Text("\nContext:", style="info"),
            Text(f"  Phase: {report.context.phase}", style="info"),
            Text(f"  Operation: {report.context.operation}", style="info")
        ]
        
        if report.context.file:
            error_text.append(Text(f"  File: {report.context.file}", style="info"))
        
        if report.context.details:
            error_text.append(Text("\nDetails:", style="info"))
            for key, value in report.context.details.items():
                error_text.append(Text(f"  {key}: {value}", style="info"))
        
        if report.suggestions:
            error_text.extend([
                Text("\nSuggestions:", style="warning"),
                *[Text(f"  • {suggestion}", style="warning") for suggestion in report.suggestions]
            ])
        
        panel = Panel.fit(
            "\n".join(str(t) for t in error_text),
            title="Error Report",
            border_style="error"
        )
        
        self.console.print(panel)
    
    def display_summary(self):
        """Display error summary."""
        if not self.errors:
            return
        
        # Create summary table
        table = Table(
            title="Error Summary",
            show_header=True,
            header_style="table.header",
            border_style="table.border",
            title_style="table.title"
        )
        
        table.add_column("Phase", style="phase")
        table.add_column("Operation", style="info")
        table.add_column("Error Type", style="error")
        table.add_column("Message", style="error")
        
        for report in self.errors:
            table.add_row(
                report.context.phase,
                report.context.operation,
                type(report.error).__name__,
                str(report.error)
            )
        
        self.console.print(table)
    
    def get_error_count(self, phase: Optional[str] = None) -> int:
        """Get number of errors.
        
        Args:
            phase: Optional phase to filter by
            
        Returns:
            Number of errors
        """
        if phase:
            return sum(1 for r in self.errors if r.context.phase == phase)
        return len(self.errors)
    
    def clear(self):
        """Clear all errors."""
        self.errors.clear() 