"""
Structured logging utilities for the Nova CLI tool.

This module provides utilities for structured logging in JSON format.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any, Dict, Optional


class StructuredLogFormatter(logging.Formatter):
    """
    Custom formatter for structured logging in JSON format.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.

        Args:
            record: The log record to format.

        Returns:
            A JSON string representation of the log record.
        """
        log_data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
            }

        # Add extra fields if available
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO", structured: bool = True) -> None:
    """
    Set up logging configuration with structured logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        structured: Whether to use structured logging (JSON format).

    Raises:
        ValueError: If the log level is invalid.
    """
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)

    if structured:
        formatter = StructuredLogFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Log a message with additional context.

    Args:
        logger: Logger instance.
        level: Log level (debug, info, warning, error, critical).
        message: Log message.
        extra: Additional context to include in the log.
    """
    log_method = getattr(logger, level.lower())
    log_method(message, extra={"extra": extra or {}})
