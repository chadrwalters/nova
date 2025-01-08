"""Command-line interface for Nova document processor."""

import argparse
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from .config.manager import ConfigManager
from .core.nova import Nova

logger = logging.getLogger(__name__)
console = Console()


def setup_logging() -> None:
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Nova document processor")
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file",
        default=os.environ.get("NOVA_CONFIG_PATH"),
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        help="Input directory",
        default=None,
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory",
        default=None,
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Process directories recursively",
        default=True,
    )
    return parser.parse_args()


def count_processable_files(directory: Path) -> int:
    """Count files that should be processed.

    Args:
        directory: Directory to count files in

    Returns:
        int: Number of processable files
    """
    count = 0
    for file_path in directory.rglob("*"):
        if file_path.is_file() and file_path.name != ".DS_Store":
            count += 1
    return count


async def main() -> None:
    """Main entry point."""
    try:
        # Set up logging
        setup_logging()

        # Parse arguments
        args = parse_args()

        # Initialize config
        config = ConfigManager(args.config)

        # Initialize Nova
        nova = Nova(config)

        # Process input directory
        input_dir = Path(args.input_dir) if args.input_dir else config.input_dir
        output_dir = Path(args.output_dir) if args.output_dir else config.output_dir

        # Count processable files
        total_files = count_processable_files(input_dir)

        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            # Create overall progress
            overall_task = progress.add_task(
                "[cyan]Processing files",
                total=total_files
            )

            # Process each file
            for file_path in input_dir.rglob("*"):
                if file_path.is_file():
                    # Skip .DS_Store files silently
                    if file_path.name == ".DS_Store":
                        continue

                    # Update progress description
                    progress.update(
                        overall_task,
                        description=f"[cyan]Processing {file_path.name}"
                    )

                    # Process file
                    await nova.process_file(file_path)

                    # Update progress
                    progress.advance(overall_task)

        # Run finalization
        nova.finalize()

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
