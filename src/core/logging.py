"""Logging configuration for Nova Document Processor."""

import logging
import json
from typing import Any, Dict
from pathlib import Path

from .models import LoggingConfig

class NovaFormatter(logging.Formatter):
    """Custom formatter that handles structured logging cleanly."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        # Skip debug messages unless explicitly requested
        if record.levelno == logging.DEBUG:
            return ""
            
        # For INFO level, only show specific messages
        if record.levelno == logging.INFO:
            msg = record.getMessage()
            # Only show specific info messages
            if any(x in msg for x in [
                "Running Markdown Parse Phase",
                "Processing completed",
                "Processing directory:",
                "Starting markdown parse"
            ]):
                return msg
            return ""
            
        # For other levels, include the level
        return f"{record.levelname}: {record.getMessage()}"

def setup_logging(config: LoggingConfig, verbose: bool = False) -> None:
    """Set up logging configuration."""
    # Remove all existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Set level based on verbose flag
    level = logging.DEBUG if verbose else getattr(logging, config.level.upper())
    root_logger.setLevel(level)
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(NovaFormatter())
    root_logger.addHandler(console_handler)
    
    # Configure all loggers to use the root logger
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        logger.handlers = []
        logger.propagate = True
    
    # Suppress all logging from libraries
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("markdown_it").setLevel(logging.WARNING)
    logging.getLogger("markitdown").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the Nova configuration."""
    logger = logging.getLogger(name)
    logger.propagate = True  # Ensure messages propagate to root logger
    return logger