"""
Configuration loader module for the Nova CLI tool.

This module provides utilities for loading and validating configuration files.
"""

from pathlib import Path
from typing import Type

from pydantic import BaseModel


def load_config(config_path: str, config_model: Type[BaseModel]) -> BaseModel:
    """
    Load and validate configuration from a TOML file using a Pydantic model.

    Args:
        config_path: Path to the configuration file.
        config_model: Pydantic model class to use for validation.

    Returns:
        Validated configuration object.

    Raises:
        ConfigurationError: If the configuration file doesn't exist or is invalid.
    """
    import logging

    from nova.exceptions import ConfigurationError

    config_file = Path(config_path).resolve()
    if not config_file.exists():
        raise ConfigurationError(
            f"Configuration file not found: {config_path}", config_file=str(config_file)
        )

    try:
        with open(config_file, "rb") as f:
            # Use tomllib if available (Python 3.11+), otherwise fall back to toml
            try:
                import tomllib

                config_dict = tomllib.load(f)
            except ImportError:
                import toml

                config_dict = toml.load(f)

        # Validate configuration using Pydantic model
        return config_model(**config_dict)
    except Exception as e:
        logging.error(f"Error parsing configuration file: {e}")
        raise ConfigurationError(
            f"Invalid configuration: {e}", config_file=str(config_file)
        )
