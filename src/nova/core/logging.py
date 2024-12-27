"""Logging configuration and utilities."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, Union

from rich.console import Console
from rich.logging import RichHandler


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[Union[str, Path]] = None,
    console: Optional[Console] = None
) -> None:
    """Set up logging configuration.
    
    Args:
        level: Optional log level (defaults to environment variable or INFO)
        log_file: Optional path to log file
        console: Optional rich console instance
    """
    # Get log level from environment or default to INFO
    if level is None:
        level = os.getenv("NOVA_LOG_LEVEL", "INFO")
        
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(level.upper())
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Create rich handler
    rich_handler = RichHandler(
        console=console or Console(),
        show_path=False,
        omit_repeated_times=False,
        rich_tracebacks=True
    )
    rich_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(rich_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        )
        logger.addHandler(file_handler)


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


def get_logger(
    name: str,
    level: Optional[str] = None,
    console: Optional[Console] = None
) -> logging.Logger:
    """Get configured logger instance.
    
    Args:
        name: Logger name
        level: Optional log level (defaults to environment variable or INFO)
        console: Optional rich console instance
        
    Returns:
        Configured logger instance
    """
    # Get log level from environment or default to INFO
    if level is None:
        level = os.getenv("NOVA_LOG_LEVEL", "INFO")
        
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        
    # Create rich handler
    handler = RichHandler(
        console=console or Console(),
        show_path=False,
        omit_repeated_times=False,
        rich_tracebacks=True
    )
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    return logger 