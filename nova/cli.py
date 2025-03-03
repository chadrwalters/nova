"""
Main CLI entry point for the Nova CLI tool.

This module provides the main entry point for the Nova CLI tool, including
command-line argument parsing and dispatching to appropriate command handlers.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Optional

from nova import __version__
from nova.commands import consolidate_markdown_command, upload_markdown_command
from nova.config import MainConfig, load_config
from nova.exceptions import ConfigurationError, NovaError
from nova.utils import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args(args: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.

    Args:
        args: Command-line arguments to parse. If None, sys.argv[1:] is used.

    Returns:
        Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Nova CLI - A tool for processing and uploading Markdown files to Graphlit."
    )
    parser.add_argument(
        "--version", action="version", version=f"Nova CLI v{__version__}"
    )

    subparsers = parser.add_subparsers(title="commands", dest="command")

    # Add consolidate-markdown command
    consolidate_parser = subparsers.add_parser(
        "consolidate-markdown",
        help="Process Markdown files from a source directory to an output directory.",
    )
    consolidate_parser.add_argument(
        "--config",
        default="config/consolidate-markdown.toml",
        help="Path to the consolidate-markdown configuration file.",
    )

    # Add upload-markdown command
    upload_parser = subparsers.add_parser(
        "upload-markdown", help="Upload Markdown files to Graphlit."
    )
    upload_parser.add_argument(
        "--config",
        default="config.toml",
        help="Path to the Graphlit configuration file.",
    )
    upload_parser.add_argument(
        "--output-dir",
        default="output",
        help="Directory containing Markdown files to upload.",
    )
    upload_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files to upload without uploading.",
    )

    return parser.parse_args(args)


async def main_async(args: Optional[List[str]] = None) -> int:
    """
    Main async entry point for the Nova CLI tool.

    Args:
        args: Command-line arguments to parse. If None, sys.argv[1:] is used.

    Returns:
        Exit code.
    """
    parsed_args = parse_args(args)

    # Set up logging
    try:
        if parsed_args.command == "upload-markdown":
            # Load logging configuration from config.toml
            config_path = Path(parsed_args.config).resolve()
            if config_path.exists():
                config = load_config(str(config_path), MainConfig)
                setup_logging(level=config.logging.level)
            else:
                setup_logging()  # Use default logging configuration
        else:
            setup_logging()  # Use default logging configuration
    except Exception as e:
        # If logging setup fails, fall back to basic logging
        print(f"Warning: Failed to set up logging: {e}", file=sys.stderr)
        setup_logging(level="INFO", structured=False)

    # Dispatch to appropriate command
    try:
        if parsed_args.command == "consolidate-markdown":
            logger.info("Starting consolidate-markdown command")
            await consolidate_markdown_command(parsed_args.config)
            logger.info("Consolidate-markdown command completed successfully")
            return 0
        elif parsed_args.command == "upload-markdown":
            logger.info("Starting upload-markdown command")
            await upload_markdown_command(
                parsed_args.config, parsed_args.output_dir, parsed_args.dry_run
            )
            logger.info("Upload-markdown command completed successfully")
            return 0
        else:
            logger.error("No command specified")
            parse_args(["--help"])
            return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.message}")
        return e.exit_code
    except NovaError as e:
        logger.error(f"Error: {e.message}")
        return e.exit_code
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return 1

    return 0


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the Nova CLI tool.

    Args:
        args: Command-line arguments to parse. If None, sys.argv[1:] is used.

    Returns:
        Exit code.
    """
    try:
        return asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("Operation cancelled by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
