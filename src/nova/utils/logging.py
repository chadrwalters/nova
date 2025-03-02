"""
Logging utilities for Nova.

This module provides logging utilities for Nova.
"""

from nova.utils.logger import get_logger, configure_root_logger

# Re-export functions from logger.py
__all__ = [
    "get_logger",
    "configure_root_logger",
]

# Add a setup_logging function for convenience
def setup_logging(level: str = "INFO") -> None:
    """Set up logging with the specified level.

    Args:
        level: The logging level as a string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    import logging

    # Convert string level to logging level
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    # Configure the root logger
    configure_root_logger(numeric_level)
