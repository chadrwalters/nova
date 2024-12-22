"""Logging module for Nova document processor."""

import logging
import sys
from pathlib import Path
from typing import Optional, Any
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.theme import Theme

# Create console with custom theme
NOVA_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "progress": "blue",
    "path": "magenta",
    "detail": "dim white"
})

console = Console(theme=NOVA_THEME)
progress_console = Console(theme=NOVA_THEME, file=sys.stderr)

def create_progress() -> Progress:
    """Create a Rich progress bar with Nova styling."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=progress_console
    )

def setup_logger(log_file: Optional[Path] = None, level: str = "INFO") -> None:
    """Setup logging configuration with Rich handler for colored output.
    
    Args:
        log_file: Path to log file
        level: Logging level
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure with Rich handler for console output
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=[
            RichHandler(console=console, rich_tracebacks=True)
        ]
    )
    
    # Add file handler if log file specified (plain format for files)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        logging.getLogger().addHandler(file_handler)

def get_logger(name: str) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)

# Convenience methods for direct console output
def info(message: Any, **kwargs) -> None:
    """Print info message with cyan color."""
    console.print(f"[info]{message}[/]", **kwargs)

def warning(message: Any, **kwargs) -> None:
    """Print warning message with yellow color."""
    console.print(f"[warning]{message}[/]", **kwargs)

def error(message: Any, **kwargs) -> None:
    """Print error message with red color."""
    console.print(f"[error]{message}[/]", **kwargs)

def success(message: Any, **kwargs) -> None:
    """Print success message with green color."""
    console.print(f"[success]{message}[/]", **kwargs)

def path(message: Any, **kwargs) -> None:
    """Print path with magenta color."""
    console.print(f"[path]{message}[/]", **kwargs)

def detail(message: Any, **kwargs) -> None:
    """Print detail with dim white color."""
    console.print(f"[detail]{message}[/]", **kwargs)