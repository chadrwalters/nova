"""Logging configuration for Nova."""

import logging
import os
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

# This module is deprecated in favor of nova.core.logging.LoggingManager
# Keeping this file for backwards compatibility
from ..core.logging import LoggingManager


def setup_logging(config=None):
    """Set up logging configuration using LoggingManager.

    This function is deprecated. Use LoggingManager directly instead.

    Args:
        config: Optional configuration manager instance
    """
    if config and config.logging:
        manager = LoggingManager(config.logging)
    else:
        from ..config.settings import LoggingConfig

        manager = LoggingManager(LoggingConfig())
