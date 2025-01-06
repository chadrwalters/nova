"""Nova cleanup utility."""
import argparse
import logging
import shutil
from pathlib import Path

from nova.context_processor.config.manager import ConfigManager

logger = logging.getLogger(__name__)


def clean_processing(config: ConfigManager) -> bool:
    """Clean processing directory.

    Args:
        config: Nova configuration manager

    Returns:
        True if successful, False otherwise
    """
    try:
        processing_dir = config.processing_dir
        if processing_dir.exists():
            shutil.rmtree(processing_dir)
            processing_dir.mkdir(parents=True, exist_ok=True)
            logger.info("Processing directory cleaned successfully")
            return True
        else:
            logger.info("Processing directory already clean")
            return True
    except Exception as e:
        logger.error(f"Failed to clean processing directory: {e}")
        return False


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
    parser.add_argument("--config", type=Path, help="Path to config file")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.all and not args.processing:
        parser.print_help()
        return 1

    try:
        # Load configuration
        config = ConfigManager(args.config)

        success = True
        if args.all or args.processing:
            success = clean_processing(config)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
