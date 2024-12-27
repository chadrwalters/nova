"""Console logging utilities."""

import logging
from typing import Any, Dict, Optional

from rich.console import Console

from ..utils.metrics import MetricsTracker


class ConsoleLogger:
    """Console logger with rich formatting."""
    
    def __init__(
        self,
        console: Optional[Console] = None,
        metrics: Optional[MetricsTracker] = None
    ):
        """Initialize the logger.
        
        Args:
            console: Optional rich console instance
            metrics: Optional metrics tracker instance
        """
        self.console = console or Console()
        self.metrics = metrics or MetricsTracker()
        self.logger = logging.getLogger(__name__)
        
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log a debug message.
        
        Args:
            message: Message to log
            **kwargs: Additional logging arguments
        """
        self.logger.debug(message, **kwargs)
        self.console.print(f"[dim]{message}[/dim]")
        self.metrics.increment('log_debug')
        
    def info(self, message: str, **kwargs: Any) -> None:
        """Log an info message.
        
        Args:
            message: Message to log
            **kwargs: Additional logging arguments
        """
        self.logger.info(message, **kwargs)
        self.console.print(message)
        self.metrics.increment('log_info')
        
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log a warning message.
        
        Args:
            message: Message to log
            **kwargs: Additional logging arguments
        """
        self.logger.warning(message, **kwargs)
        self.console.print(f"[yellow]WARNING:[/yellow] {message}")
        self.metrics.increment('log_warning')
        
    def error(self, message: str, **kwargs: Any) -> None:
        """Log an error message.
        
        Args:
            message: Message to log
            **kwargs: Additional logging arguments
        """
        self.logger.error(message, **kwargs)
        self.console.print(f"[red]ERROR:[/red] {message}")
        self.metrics.increment('log_error')
        
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log a critical message.
        
        Args:
            message: Message to log
            **kwargs: Additional logging arguments
        """
        self.logger.critical(message, **kwargs)
        self.console.print(f"[bold red]CRITICAL:[/bold red] {message}")
        self.metrics.increment('log_critical') 