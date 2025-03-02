#!/usr/bin/env python
"""
Import markdown files to Graphlit.

This script imports markdown files from a directory to Graphlit.
"""

import argparse
import glob
import os
import sys
from typing import List, Optional

from nova.config.settings import get_settings
from nova.services.graphlit.client import GraphlitClient
from nova.services.graphlit.feed import FeedManager
from nova.services.graphlit.document import DocumentManager
from nova.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Import markdown files to Graphlit")

    parser.add_argument(
        "--input-dir",
        type=str,
        help="Directory containing markdown files to import",
    )

    parser.add_argument(
        "--feed-name",
        type=str,
        default="Nova Knowledge Base",
        help="Name of the Graphlit feed to create or use",
    )

    parser.add_argument(
        "--feed-description",
        type=str,
        default="Processed markdown files from consolidate-markdown",
        help="Description of the Graphlit feed",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of files to process in each batch",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser.parse_args()


def get_markdown_files(directory: str) -> List[str]:
    """Get all markdown files in a directory.

    Args:
        directory: The directory to search for markdown files.

    Returns:
        A list of paths to markdown files.
    """
    if not os.path.isdir(directory):
        logger.error(f"Directory does not exist: {directory}")
        return []

    markdown_files = glob.glob(os.path.join(directory, "*.md"))
    logger.info(f"Found {len(markdown_files)} markdown files in {directory}")

    return markdown_files


def process_in_batches(items: List[str], batch_size: int, processor_func, *args, **kwargs) -> List[str]:
    """Process items in batches.

    Args:
        items: The items to process.
        batch_size: The number of items to process in each batch.
        processor_func: The function to process each batch.
        *args: Additional arguments to pass to the processor function.
        **kwargs: Additional keyword arguments to pass to the processor function.

    Returns:
        A list of results from the processor function.
    """
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_num = i // batch_size + 1

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

        batch_results = processor_func(batch, *args, **kwargs)
        results.extend(batch_results)

        logger.info(f"Completed batch {batch_num}/{total_batches}")

    return results


def import_markdown_files(
    input_dir: str,
    feed_name: str,
    feed_description: str,
    batch_size: int = 10
) -> Optional[str]:
    """Import markdown files to Graphlit.

    Args:
        input_dir: The directory containing markdown files to import.
        feed_name: The name of the Graphlit feed to create or use.
        feed_description: The description of the Graphlit feed.
        batch_size: The number of files to process in each batch.

    Returns:
        The ID of the created feed, or None if the import failed.
    """
    try:
        # Initialize Graphlit client
        client = GraphlitClient()
        feed_manager = FeedManager(client)
        document_manager = DocumentManager(client)

        # Create feed
        feed_id = feed_manager.create_feed(feed_name, feed_description)
        logger.info(f"Created feed with ID: {feed_id}")

        # Get markdown files
        markdown_files = get_markdown_files(input_dir)
        if not markdown_files:
            logger.error(f"No markdown files found in {input_dir}")
            return None

        # Process files in batches
        def process_batch(batch: List[str]) -> List[str]:
            return document_manager.upload_batch(feed_id, batch)

        content_ids = process_in_batches(markdown_files, batch_size, process_batch)

        logger.info(f"Import complete. Imported {len(content_ids)}/{len(markdown_files)} files")

        return feed_id

    except Exception as e:
        logger.error(f"Error importing markdown files: {str(e)}")
        return None


def main() -> int:
    """Main entry point.

    Returns:
        The exit code.
    """
    args = parse_args()

    # Set up logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(log_level)

    # Get input directory from args or config
    input_dir = args.input_dir
    if not input_dir:
        settings = get_settings()
        input_dir = settings.output_dir
        logger.info(f"Using input directory from config: {input_dir}")

    # Import markdown files
    feed_id = import_markdown_files(
        input_dir=input_dir,
        feed_name=args.feed_name,
        feed_description=args.feed_description,
        batch_size=args.batch_size
    )

    if feed_id:
        logger.info(f"Successfully imported markdown files to feed: {feed_id}")
        return 0
    else:
        logger.error("Failed to import markdown files")
        return 1


if __name__ == "__main__":
    sys.exit(main())
