"""
Consolidate Markdown command handler.

This module provides the command handler for the consolidate-markdown command.
"""

import asyncio
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import tomli

from nova.config import ConsolidateMarkdownConfig, load_config
from nova.exceptions import ConfigurationError, ConsolidationError
from nova.utils import get_logger

logger = get_logger(__name__)


def is_consolidate_markdown_installed() -> bool:
    """Check if the consolidate-markdown package is installed."""
    return importlib.util.find_spec("consolidate_markdown") is not None


async def consolidate_markdown_command(config_path: str) -> None:
    """
    Consolidate Markdown files based on the configuration file.

    Args:
        config_path: Path to the Nova configuration file.

    Raises:
        ConfigurationError: If the configuration is invalid.
        ConsolidationError: If an error occurs during consolidation.
    """
    logger.info(f"Loading configuration from {config_path}")

    # Check if consolidate-markdown is installed
    if not is_consolidate_markdown_installed():
        logger.error("ConsolidateMarkdown library not found")
        raise ConsolidationError(
            "ConsolidateMarkdown library not found. "
            "Install with: uv pip install -e ."
        )

    config_path = Path(config_path).resolve()
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            config_file=str(config_path),
        )

    # Load the unified configuration file
    try:
        with open(config_path, "rb") as f:
            try:
                import tomllib
                config_dict = tomllib.load(f)
            except ImportError:
                import toml
                config_dict = toml.load(f)

        # Check if the configuration has a consolidate section
        if "consolidate" not in config_dict:
            logger.error("Configuration file does not contain a 'consolidate' section")
            raise ConfigurationError(
                "Configuration file does not contain a 'consolidate' section",
                config_file=str(config_path),
            )

        # Extract the consolidate section
        consolidate_config = config_dict["consolidate"]

        # Create a temporary configuration file for consolidate-markdown
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as temp_file:
            temp_config_path = temp_file.name

            # Convert the nested consolidate config to a flat structure
            flat_config = {}

            # Add global section
            if "global" in consolidate_config:
                flat_config["global"] = consolidate_config["global"]

            # Add models section
            if "models" in consolidate_config:
                flat_config["models"] = consolidate_config["models"]

            # Add sources section
            if "sources" in consolidate_config:
                flat_config["sources"] = consolidate_config["sources"]

            # Write the configuration to the temporary file
            import toml
            toml.dump(flat_config, temp_file)

        logger.info(f"Created temporary configuration file: {temp_config_path}")

        # Run the consolidate-markdown command with the temporary configuration file
        logger.info(f"Running consolidate-markdown with configuration file: {temp_config_path}")

        try:
            # Use subprocess to run the consolidate-markdown command
            process = subprocess.run(
                ["uv", "run", "consolidate-markdown", "--config", temp_config_path],
                capture_output=True,
                text=True,
                check=True,
            )

            # Log the output
            for line in process.stdout.splitlines():
                logger.info(f"consolidate-markdown: {line}")

            logger.info("Markdown consolidation complete")
        except subprocess.CalledProcessError as e:
            # Log the error output
            for line in e.stderr.splitlines():
                logger.error(f"consolidate-markdown error: {line}")

            logger.error(f"Error during Markdown consolidation: {e}")
            raise ConsolidationError(f"Error during Markdown consolidation: {e}") from e
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_config_path)
                logger.info(f"Removed temporary configuration file: {temp_config_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary configuration file: {e}")
    except Exception as e:
        logger.error(f"Error during Markdown consolidation: {e}")
        raise ConsolidationError(f"Error during Markdown consolidation: {e}") from e
