"""Logging configuration for Nova."""

import logging
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler

from ..config.manager import ConfigManager
from ..config.settings import LoggingConfig, NovaConfig

# This module is deprecated in favor of nova.core.logging.LoggingManager
# Keeping this file for backwards compatibility
from ..core.logging import LoggingManager


def setup_logging(config: Optional[ConfigManager] = None) -> None:
    """Set up logging configuration using LoggingManager.

    This function is deprecated. Use LoggingManager directly instead.

    Args:
        config: Optional configuration manager instance
    """
    if config and isinstance(config.config, NovaConfig) and config.config.logging:
        manager = LoggingManager(config.config.logging)
    else:
        manager = LoggingManager(LoggingConfig())
