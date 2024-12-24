"""Logging utilities for Nova document processor."""

import logging
import os
from pathlib import Path
from typing import Optional, Union

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
        """Format log record with colors.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message with colors
        """
        # Get the original formatted message
        message = super().format(record)
        
        # Add color if available for the level
        if record.levelname in self.COLORS:
            message = (
                f"{self.COLORS[record.levelname]}"
                f"{message}"
                f"{self.COLORS['RESET']}"
            )
            
        return message

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

def setup_logging(
    level: Union[str, int] = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
) -> None:
    """Set up logging configuration.
    
    Args:
        level: Logging level
        log_file: Optional path to log file
        log_format: Log message format
    """
    # Convert level string to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper())
    
    # Create handlers
    handlers = []
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter(log_format))
    handlers.append(console_handler)
    
    # File handler if log file specified
    if log_file:
        log_file = Path(log_file)
        os.makedirs(log_file.parent, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True
    )

def get_logger(name: str) -> logging.Logger:
    """Get logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)