"""Nova cleanup utility."""
import argparse
import logging
import shutil
from pathlib import Path

from nova.context_processor.config.manager import ConfigManager

logger = logging.getLogger(__name__)


def clean_directory(path: Path, name: str) -> bool:
    """Clean a directory.

    Args:
        path: Directory path to clean
        name: Name of directory for logging

    Returns:
        True if successful, False otherwise
    """
    try:
        if path.exists():
            shutil.rmtree(path)
            path.mkdir(parents=True, exist_ok=True)
            logger.info(f"{name} directory cleaned successfully")
            return True
        else:
            logger.info(f"{name} directory already clean")
            return True
    except Exception as e:
        logger.error(f"Failed to clean {name} directory: {e}")
        return False


def clean_processing(config: ConfigManager) -> bool:
    """Clean processing directory.

    Args:
        config: Nova configuration manager

    Returns:
        True if successful, False otherwise
    """
    return clean_directory(config.processing_dir, "Processing")


def clean_cache(config: ConfigManager) -> bool:
    """Clean cache directory.

    Args:
        config: Nova configuration manager

    Returns:
        True if successful, False otherwise
    """
    return clean_directory(config.cache.dir, "Cache")


def clean_output(config: ConfigManager) -> bool:
    """Clean output directory.

    Args:
        config: Nova configuration manager

    Returns:
        True if successful, False otherwise
    """
    return clean_directory(config.output_dir, "Output")


def main() -> int:
    """Main entry point for cleanup utility.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(description="Nova cleanup utility")
    parser.add_argument("-a", "--all", action="store_true", help="Clean everything")
    parser.add_argument(
        "-p",
        "--processing",
        action="store_true",
        help="Clean processing directory only",
    )
    parser.add_argument(
        "-c",
        "--cache",
        action="store_true",
        help="Clean cache directory only",
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store_true",
        help="Clean output directory",
    )
    parser.add_argument("--config", type=Path, help="Path to config file")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not any([args.all, args.processing, args.cache, args.output]):
        parser.print_help()
        return 1

    try:
        # Load configuration
        config = ConfigManager(args.config)

        success = True
        if args.all or args.processing:
            success = success and clean_processing(config)
        if args.all or args.cache:
            success = success and clean_cache(config)
        if args.all or args.output:
            success = success and clean_output(config)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
