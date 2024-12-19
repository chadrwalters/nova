"""Logging configuration for Nova Document Processor."""

import logging
from typing import Optional

from .models import NovaConfig

def setup_logging(config: NovaConfig) -> None:
    """Setup logging configuration."""
    # Get log level from config, default to INFO
    log_level = getattr(config.logging, 'level', 'INFO') if hasattr(config, 'logging') else 'INFO'
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure specific loggers to be less verbose
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('markdown_it').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)