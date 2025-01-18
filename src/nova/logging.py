"""Nova logging configuration."""

import logging
from enum import Enum
from pathlib import Path
from typing import Any


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


def configure_logging() -> None:
    """Configure logging.

    Sets up console output and file output to .nova/logs/nova.log.
    """
    # Ensure .nova/logs exists
    log_dir = Path(".nova/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for Nova's logging
    file_handler = logging.FileHandler(log_dir / "nova.log")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # Add handler to Nova logger
    nova_logger = logging.getLogger("nova")
    nova_logger.setLevel(logging.INFO)
    nova_logger.addHandler(file_handler)
    nova_logger.propagate = True  # Propagate to root logger's console handler
