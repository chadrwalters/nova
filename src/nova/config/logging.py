"""Logging configuration for Nova."""

import os
import logging
from pathlib import Path
from rich.logging import RichHandler
from rich.console import Console

def setup_logging():
    """Set up logging configuration."""
    # Get log level from environment variable
    log_level = os.getenv('NOVA_LOG_LEVEL', 'WARNING').upper()
    
    # Configure rich console
    console = Console(force_terminal=True)
    
    # Configure rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=True,
        show_path=True,
        enable_link_path=True,
        markup=True,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        level=log_level
    )
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler]
    )
    
    # Set log level for all nova loggers
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith('nova'):
            logger = logging.getLogger(logger_name)
            logger.setLevel(log_level)
            
            # Remove any existing handlers
            logger.handlers = []
            
            # Add rich handler
            logger.addHandler(rich_handler)
            
            # Ensure the logger propagates to the root logger
            logger.propagate = False  # Don't propagate to avoid duplicate messages 