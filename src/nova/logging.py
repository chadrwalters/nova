"""Nova logging configuration."""

import logging
from enum import Enum
from pathlib import Path
from typing import Any

from fastmcp.utilities.logging import configure_logging as configure_fastmcp_logging


class LogLevel(str, Enum):
    """Log levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def get_component_logger(name: str) -> logging.Logger:
    """Get a logger for a component.

    Args:
        name: Component name

    Returns:
        Logger for the component
    """
    return logging.getLogger(f"nova.{name}")


def log_error(logger: logging.Logger, message: str, error: Exception | None = None) -> None:
    """Log an error message.

    Args:
        logger: Logger to use
        message: Error message
        error: Optional exception
    """
    if error:
        logger.error(f"{message}: {error!s}")
    else:
        logger.error(message)


def log_tool_call(logger: logging.Logger, tool_name: str, args: dict[str, Any]) -> None:
    """Log a tool call.

    Args:
        logger: Logger to use
        tool_name: Name of the tool
        args: Tool arguments
    """
    logger.info(f"Calling tool {tool_name} with args: {args}")


def configure_logging(log_dir: Path | None = None) -> None:
    """Configure logging.

    Args:
        log_dir: Optional log directory
    """
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    configure_fastmcp_logging(log_dir=str(log_dir) if log_dir else None, log_level=LogLevel.INFO)
