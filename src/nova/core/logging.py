"""Unified logging configuration for Nova."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.style import Style
from rich.text import Text
from tqdm import tqdm
import re

class ColorScheme:
    """Color scheme for Nova console output."""
    
    STYLES = {
        'title': Style(color="blue", bold=True),
        'path': Style(color="cyan"),
        'stats': Style(color="cyan", bold=True),
        'success': Style(color="green"),
        'warning': Style(color="yellow"),
        'error': Style(color="red"),
        'info': Style(color="blue"),
        'highlight': Style(color="magenta"),
        'detail': Style(color="white", dim=True),
        'cache': Style(color="cyan"),
        'progress': Style(color="green"),
        'skip': Style(color="yellow")
    }
    
    @classmethod
    def apply(cls, text: str, style_name: str) -> Text:
        """Apply style to text.
        
        Args:
            text: Text to style
            style_name: Name of style to apply
            
        Returns:
            Styled text
        """
        if style_name in cls.STYLES:
            return Text(text, style=cls.STYLES[style_name])
        return Text(text)

class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log messages."""
    
    COLORS = {
        'DEBUG': '\033[0;36m',     # Cyan
        'INFO': '\033[0;32m',      # Green
        'WARNING': '\033[0;33m',   # Yellow
        'ERROR': '\033[0;31m',     # Red
        'CRITICAL': '\033[0;35m',  # Magenta
        'RESET': '\033[0m',        # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        message = super().format(record)
        if record.levelname in self.COLORS:
            message = f"{self.COLORS[record.levelname]}{message}{self.COLORS['RESET']}"
        return message

class ConsoleManager:
    """Manages console output and progress bars."""
    
    def __init__(self):
        """Initialize console manager."""
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
    
    def print_stats(self, stats: Dict[str, Any]) -> None:
        """Print statistics with proper formatting.
        
        Args:
            stats: Dictionary of statistics to display
        """
        for key, value in stats.items():
            if isinstance(value, (int, float)):
                value_text = Text(str(value), style=ColorScheme.STYLES['highlight'])
            else:
                value_text = Text(str(value), style=ColorScheme.STYLES['detail'])
            key_text = Text(f"{key}: ", style=ColorScheme.STYLES['stats'])
            self.console.print(key_text + value_text)
    
    def print_path(self, path: Union[str, Path]) -> None:
        """Print file path with proper formatting.
        
        Args:
            path: Path to display
        """
        self.console.print(Text(str(path), style=ColorScheme.STYLES['path']))
    
    def print_cache_info(self, info: Dict[str, Any]) -> None:
        """Print cache information with proper formatting.
        
        Args:
            info: Cache information to display
        """
        for key, value in info.items():
            key_text = Text(f"{key}: ", style=ColorScheme.STYLES['cache'])
            value_text = Text(str(value), style=ColorScheme.STYLES['detail'])
            self.console.print(key_text + value_text)
    
    def create_progress_bar(
        self,
        total: int,
        description: str = "",
        unit: str = "it"
    ) -> tqdm:
        """Create a progress bar.
        
        Args:
            total: Total number of items
            description: Progress bar description
            unit: Unit of measurement
            
        Returns:
            Progress bar instance
        """
        return tqdm(
            total=total,
            desc=description,
            unit=unit,
            colour='green'
        )

# Global console manager instance
console = ConsoleManager()

class LoggerMixin:
    """Mixin class that provides logging methods."""
    
    def __init__(self) -> None:
        """Initialize logger for the class."""
        self._logger = get_logger(self.__class__.__name__)
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log debug message."""
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        """Log info message."""
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log warning message."""
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        """Log error message."""
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        """Log critical message."""
        self._logger.critical(msg, *args, **kwargs)

class Base64Filter(logging.Filter):
    """Filter to redact base64 data from log messages."""
    
    def __init__(self):
        """Initialize the filter."""
        super().__init__()
        self.base64_pattern = re.compile(
            r'data:(?:[^;,]+)?(?:;[^,]+)*,([A-Za-z0-9+/=]+)'
        )
    
    def filter(self, record):
        """Filter log record.
        
        Args:
            record: Log record to filter
            
        Returns:
            bool: True to include record, False to exclude
        """
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.base64_pattern.sub(
                r'data:[...base64 data redacted...]',
                record.msg
            )
        return True

def configure_package_logging() -> None:
    """Configure logging levels for third-party packages."""
    # Set higher log level for noisy third-party packages
    logging.getLogger('pdfminer').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('markitdown').setLevel(logging.WARNING)

def setup_logging(
    level: Union[str, int] = None,
    log_file: Optional[Union[str, Path]] = None,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    use_rich: bool = True,
    handlers: Dict[str, Dict[str, Any]] = None
) -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level (defaults to NOVA_LOG_LEVEL env var or INFO)
        log_file: Optional path to log file
        log_format: Log message format
        use_rich: Whether to use rich formatting for console output
        handlers: Additional handler configurations
    """
    # Get level from environment if not specified
    if level is None:
        level = os.getenv('NOVA_LOG_LEVEL', 'INFO').upper()
    
    # Convert level string to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Create handlers list
    log_handlers = []
    
    # Add base64 filter to root logger
    logging.getLogger().addFilter(Base64Filter())
    
    # Configure third-party package logging
    configure_package_logging()
    
    # Console handler (rich or colored)
    if use_rich:
        console_handler = RichHandler(
            console=console.console,
            show_time=True,
            show_path=False,
            enable_link_path=False,
            markup=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True
        )
        # Configure console width
        console.console.width = min(120, console.console.width)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter(log_format))
    log_handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        log_file = Path(log_file)
        os.makedirs(log_file.parent, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        log_handlers.append(file_handler)
    
    # Add any additional handlers from config
    if handlers:
        for handler_config in handlers.values():
            handler_class = handler_config.get('class')
            if handler_class:
                handler = getattr(logging, handler_class.split('.')[-1])()
                handler.setLevel(handler_config.get('level', level))
                handler.setFormatter(logging.Formatter(log_format))
                log_handlers.append(handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        handlers=log_handlers,
        format=log_format,
        force=True
    )
    
    # Set nova package to use the specified level
    logging.getLogger('nova').setLevel(level)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)

# Convenience functions for common log levels
def debug(msg: str, *args, **kwargs) -> None:
    """Log debug message to root logger."""
    logging.debug(msg, *args, **kwargs)

def info(msg: str, *args, **kwargs) -> None:
    """Log info message to root logger."""
    logging.info(msg, *args, **kwargs)

def warning(msg: str, *args, **kwargs) -> None:
    """Log warning message to root logger."""
    logging.warning(msg, *args, **kwargs)

def error(msg: str, *args, **kwargs) -> None:
    """Log error message to root logger."""
    logging.error(msg, *args, **kwargs)

def critical(msg: str, *args, **kwargs) -> None:
    """Log critical message to root logger."""
    logging.critical(msg, *args, **kwargs)

# Convenience functions for styled output
def print_title(title: str) -> None:
    """Print section title."""
    console.console.print(ColorScheme.apply(title, 'title'))

def print_stats(stats: Dict[str, Any]) -> None:
    """Print statistics."""
    console.print_stats(stats)

def print_path(path: Union[str, Path]) -> None:
    """Print file path."""
    console.print_path(path)

def print_cache_info(info: Dict[str, Any]) -> None:
    """Print cache information."""
    console.print_cache_info(info)

def create_progress_bar(total: int, description: str = "", unit: str = "it") -> tqdm:
    """Create a progress bar."""
    return console.create_progress_bar(total, description, unit) 