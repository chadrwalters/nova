"""
Consolidate Markdown command handler.

This module provides the command handler for the consolidate-markdown command.
"""

from pathlib import Path
from typing import Any, Dict

from nova.config import ConsolidateMarkdownConfig, load_config
from nova.exceptions import ConfigurationError, ConsolidationError
from nova.utils import get_logger

logger = get_logger(__name__)


async def consolidate_markdown_command(config_path: str) -> None:
    """
    Consolidate Markdown files based on the configuration file.

    Args:
        config_path: Path to the consolidate-markdown configuration file.

    Raises:
        ConfigurationError: If the configuration is invalid.
        ConsolidationError: If an error occurs during consolidation.
    """
    logger.info(f"Loading configuration from {config_path}")

    try:
        # Load and validate configuration
        config_path = Path(config_path).resolve()
        config = load_config(str(config_path), ConsolidateMarkdownConfig)

        # Log configuration details
        logger.info(
            f"Configuration loaded successfully: "
            f"source={config.source.directory}, "
            f"output={config.output.directory}"
        )

        # Initialize Runner with validated configuration
        try:
            # Import here to avoid circular imports
            from consolidate_markdown.runner import Runner

            # Convert Pydantic model to dictionary for Runner
            config_dict: Dict[str, Any] = {
                "global_config": {
                    "log_level": (
                        config.logging.level if hasattr(config, "logging") else "INFO"
                    ),
                },
                "source": {
                    "directory": config.source.directory,
                    "include_patterns": config.source.include_patterns,
                    "exclude_patterns": config.source.exclude_patterns,
                },
                "output": {
                    "directory": config.output.directory,
                },
            }

            logger.info("Initializing Runner")
            runner = Runner(config=config_dict)

            # Run consolidation
            logger.info("Starting Markdown consolidation")
            await runner.run()

            logger.info("Markdown consolidation complete")
        except ImportError as e:
            logger.error("Failed to import ConsolidateMarkdown library")
            raise ConsolidationError(
                "ConsolidateMarkdown library not found. "
                "Install with: uv pip install -e ."
            ) from e
        except Exception as e:
            logger.error(f"Error during Markdown consolidation: {e}")
            raise ConsolidationError(f"Error during Markdown consolidation: {e}") from e

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {config_path}")
        raise ConfigurationError(
            f"Configuration file not found: {config_path}",
            config_file=str(config_path),
        ) from e
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise ConfigurationError(
            f"Invalid configuration: {e}",
            config_file=str(config_path),
        ) from e
