"""Logging configuration."""

import sys
from pathlib import Path
from typing import Any, Dict
import structlog
from structlog.types import Processor
from structlog.dev import ConsoleRenderer
from structlog.processors import StackInfoRenderer

def configure_logging() -> None:
    """Configure structured logging."""
    
    # Configure processors for structlog
    processors = [
        # Add timestamps in a standard format
        structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
        # Add log level
        structlog.processors.add_log_level,
        # Format the event dict to a string
        structlog.processors.format_exc_info,
        # Add colors and pretty printing
        ConsoleRenderer(
            colors=True,
            level_styles={  # Use proper ANSI color codes
                'debug': '\x1b[36m',    # Cyan
                'info': '\x1b[32m',     # Green
                'warning': '\x1b[33m',  # Yellow
                'error': '\x1b[31m',    # Red
                'critical': '\x1b[41m', # Red background
            },
            sort_keys=True,
            repr_native_str=False,
            pad_event=25  # Fixed width for event messages
        )
    ]

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

# Alias for backward compatibility
setup_logging = configure_logging

def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)

def get_file_logger(name: str) -> structlog.BoundLogger:
    """Get a logger configured for file operations.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger
    """
    return structlog.get_logger(name).bind(
        component="file_operations"
    )

def log_file_operation(
    logger: structlog.BoundLogger,
    operation: str,
    file_path: Path,
    category: str,
    **kwargs
) -> None:
    """Log a file operation with consistent formatting.
    
    Args:
        logger: Logger instance
        operation: Operation being performed (read/write/create/delete)
        file_path: Path to file
        category: File category (markdown/html/pdf/temp)
        **kwargs: Additional logging context
    """
    logger.info(
        f"{operation} {category} file",
        path=str(file_path),
        operation=operation,
        category=category,
        **kwargs
    )
