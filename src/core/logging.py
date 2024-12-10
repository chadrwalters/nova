"""Logging configuration and setup."""

import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, TypeAlias, Union, cast

import structlog
from structlog import PrintLoggerFactory, configure, dev, make_filtering_bound_logger
from structlog.contextvars import merge_contextvars
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    TimeStamper,
    UnicodeDecoder,
    add_log_level,
    format_exc_info,
)
from structlog.stdlib import BoundLogger
from structlog.types import EventDict, Processor

# Type aliases
LogLevel: TypeAlias = Union[str, int]
LogHandler: TypeAlias = logging.Handler
LogConfig: TypeAlias = dict[str, Any]
Processors: TypeAlias = list[Processor]


def setup_logging(
    log_level: LogLevel = "INFO",
    log_file: Optional[Path] = None,
    json_format: bool = False,
) -> None:
    """Set up logging configuration.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (if None, logs to stdout only)
        json_format: Whether to use JSON format for logs

    Raises:
        ValueError: If log_level is invalid
    """
    # Validate log level
    if isinstance(log_level, str):
        level = logging.getLevelName(log_level.upper())
        if not isinstance(level, int):
            raise ValueError(f"Invalid log level: {log_level}")
    else:
        level = log_level

    # Set up processors
    processors: Processors = [
        merge_contextvars,
        add_log_level,
        TimeStamper(fmt="iso"),
        StackInfoRenderer(),
        format_exc_info,
    ]

    if json_format:
        processors.append(JSONRenderer())
    else:
        processors.extend(
            [
                UnicodeDecoder(),
                dev.ConsoleRenderer(),
            ]
        )

    # Configure structlog
    configure(
        processors=cast(List[Processor], processors),
        logger_factory=PrintLoggerFactory(),
        wrapper_class=make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

    # Set up logging handlers
    handlers: List[LogHandler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(filename=log_file, encoding="utf-8"))

    # Configure logging
    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=handlers,
    )


def get_logger(name: Optional[str] = None) -> BoundLogger:
    """Get a logger instance.

    Args:
        name: Logger name (if None, uses calling module name)

    Returns:
        Configured logger instance
    """
    return cast(BoundLogger, structlog.get_logger(name))


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


# Type hints for exports
__all__: list[str] = ["setup_logging", "get_logger"]
