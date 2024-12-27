"""Console logging utilities."""

from typing import Optional
from rich.console import Console
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn


class ConsoleLogger:
    """Console logger with rich formatting."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize console logger.
        
        Args:
            console: Optional console instance
        """
        self.console = console or Console()
        self._progress = None
        
    @property
    def progress(self) -> Progress:
        """Get progress instance.
        
        Returns:
            Progress instance
        """
        if self._progress is None:
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            )
        return self._progress
        
    def info(self, message: str) -> None:
        """Log info message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[info]{message}[/]")
        
    def warning(self, message: str) -> None:
        """Log warning message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[warning]WARNING: {message}[/]")
        
    def error(self, message: str) -> None:
        """Log error message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[error]ERROR: {message}[/]")
        
    def success(self, message: str) -> None:
        """Log success message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[success]{message}[/]")
        
    def highlight(self, message: str) -> None:
        """Log highlighted message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[highlight]{message}[/]")
        
    def debug(self, message: str) -> None:
        """Log debug message.
        
        Args:
            message: Message to log
        """
        self.console.print(f"[dim]{message}[/]") 