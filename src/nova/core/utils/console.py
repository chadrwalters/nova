"""Console logging utilities."""

import sys
import logging
from typing import Optional, TextIO, Any
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.logging import RichHandler
from rich.theme import Theme
from rich.style import Style


class ConsoleLogger:
    """Console logger with rich formatting."""

    def __init__(self, 
                 console: Optional[Console] = None,
                 metrics: Optional[Any] = None,
                 level: str = "INFO",
                 show_time: bool = True,
                 show_path: bool = True,
                 stderr: bool = False,
                 file: Optional[TextIO] = None):
        """Initialize console logger.
        
        Args:
            console: Rich console instance
            metrics: Metrics tracker instance
            level: Logging level
            show_time: Whether to show timestamps
            show_path: Whether to show file paths
            stderr: Whether to log to stderr
            file: File to log to
        """
        self.console = console or Console(
            theme=Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "red",
                "debug": "grey50"
            })
        )
        
        self.metrics = metrics
        self.level = level.upper()
        self.show_time = show_time
        self.show_path = show_path
        
        # Set up logging handler
        self.handler = RichHandler(
            console=self.console,
            show_time=show_time,
            show_path=show_path,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        
        # Configure logging
        logging.basicConfig(
            level=self.level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[self.handler]
        )
        
        self.logger = logging.getLogger("nova")
        
        # Set up progress tracking
        self.progress = Progress(
            *Progress.get_default_columns(),
            console=self.console
        )
        self.tasks: dict[str, TaskID] = {}

    def start_progress(self, description: str, total: Optional[int] = None) -> TaskID:
        """Start progress tracking.
        
        Args:
            description: Task description
            total: Total steps
            
        Returns:
            Task ID
        """
        task_id = self.progress.add_task(description, total=total)
        self.tasks[description] = task_id
        return task_id

    def update_progress(self, task_id: TaskID, advance: int = 1) -> None:
        """Update progress.
        
        Args:
            task_id: Task ID
            advance: Steps to advance
        """
        self.progress.update(task_id, advance=advance)
        if self.metrics:
            self.metrics.increment("progress", advance)

    def stop_progress(self, task_id: TaskID) -> None:
        """Stop progress tracking.
        
        Args:
            task_id: Task ID
        """
        self.progress.remove_task(task_id)

    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message.
        
        Args:
            message: Message to log
            **kwargs: Additional arguments
        """
        self.logger.info(message, extra={"markup": True, **kwargs})
        if self.metrics:
            self.metrics.increment("info_messages")

    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message.
        
        Args:
            message: Message to log
            **kwargs: Additional arguments
        """
        self.logger.warning(message, extra={"markup": True, **kwargs})
        if self.metrics:
            self.metrics.increment("warnings")

    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message.
        
        Args:
            message: Message to log
            **kwargs: Additional arguments
        """
        self.logger.error(message, extra={"markup": True, **kwargs})
        if self.metrics:
            self.metrics.increment("errors")

    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message.
        
        Args:
            message: Message to log
            **kwargs: Additional arguments
        """
        self.logger.debug(message, extra={"markup": True, **kwargs})
        if self.metrics:
            self.metrics.increment("debug_messages")

    def print(self, message: str, style: Optional[str] = None, **kwargs: Any) -> None:
        """Print message with optional styling.
        
        Args:
            message: Message to print
            style: Text style
            **kwargs: Additional arguments
        """
        self.console.print(message, style=style, **kwargs)

    def rule(self, title: str, style: Optional[str] = None) -> None:
        """Print horizontal rule with title.
        
        Args:
            title: Rule title
            style: Text style
        """
        self.console.rule(title, style=style)

    def status(self, message: str) -> None:
        """Show status message.
        
        Args:
            message: Status message
        """
        self.console.status(message)

    def clear(self) -> None:
        """Clear console."""
        self.console.clear()

    def get_style(self, name: str) -> Style:
        """Get named style.
        
        Args:
            name: Style name
            
        Returns:
            Style instance
        """
        return self.console.get_style(name) 