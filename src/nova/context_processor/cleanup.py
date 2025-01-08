"""Nova cleanup utility."""

import argparse
import logging
import time
from pathlib import Path
from typing import Dict, Optional

from .config.manager import ConfigManager
from .core.directory import DirectoryManager

logger = logging.getLogger(__name__)


class CleanupManager:
    """Manager for Nova cleanup operations."""

    def __init__(self, config: ConfigManager):
        """Initialize cleanup manager.

        Args:
            config: Nova configuration manager
        """
        self.config = config
        self.directory_manager = DirectoryManager(config)
        self.start_time = None
        self.stats = {
            "files_removed": 0,
            "size_before": 0,
            "size_after": 0,
            "duration": 0,
        }

    def clean_all(self) -> bool:
        """Clean all directories.

        Returns:
            bool: True if successful, False otherwise
        """
        self.start_time = time.time()
        success = True

        try:
            # Create directory structure first
            self.directory_manager.create_structure()

            # Then validate it
            self.directory_manager.validate_structure()

            # Reset stats
            self.stats = {
                "files_removed": 0,
                "size_before": 0,
                "size_after": 0,
                "duration": 0,
            }

            # Clean directories
            success = success and self._clean_processing()
            success = success and self._clean_cache()
            success = success and self._clean_output()

            # Log summary
            self._log_summary()
            return success

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False

    def clean_processing(self) -> bool:
        """Clean processing directory.

        Returns:
            bool: True if successful, False otherwise
        """
        self.start_time = time.time()
        self.stats = {
            "files_removed": 0,
            "size_before": 0,
            "size_after": 0,
            "duration": 0,
        }
        success = self._clean_processing()
        self._log_summary()
        return success

    def clean_cache(self) -> bool:
        """Clean cache directory.

        Returns:
            bool: True if successful, False otherwise
        """
        self.start_time = time.time()
        self.stats = {
            "files_removed": 0,
            "size_before": 0,
            "size_after": 0,
            "duration": 0,
        }
        success = self._clean_cache()
        self._log_summary()
        return success

    def clean_output(self) -> bool:
        """Clean output directory.

        Returns:
            bool: True if successful, False otherwise
        """
        self.start_time = time.time()
        self.stats = {
            "files_removed": 0,
            "size_before": 0,
            "size_after": 0,
            "duration": 0,
        }
        success = self._clean_output()
        self._log_summary()
        return success

    def _clean_processing(self) -> bool:
        """Clean processing directory and subdirectories.

        Returns:
            bool: True if successful, False otherwise
        """
        success, stats = self.directory_manager.clean_directory(
            self.config.processing_dir, "Processing", recursive=True
        )
        if success:
            self._update_stats(stats)
        return success

    def _clean_cache(self) -> bool:
        """Clean cache directory.

        Returns:
            bool: True if successful, False otherwise
        """
        success, stats = self.directory_manager.clean_directory(
            self.config.cache.dir, "Cache", recursive=True
        )
        if success:
            self._update_stats(stats)
        return success

    def _clean_output(self) -> bool:
        """Clean output directory.

        Returns:
            bool: True if successful, False otherwise
        """
        success, stats = self.directory_manager.clean_directory(
            self.config.output_dir, "Output", recursive=True
        )
        if success:
            self._update_stats(stats)
        return success

    def _update_stats(self, new_stats: Dict[str, int]) -> None:
        """Update cleanup statistics.

        Args:
            new_stats: New statistics to add
        """
        self.stats["files_removed"] += new_stats["files_removed"]
        self.stats["size_before"] += new_stats["size_before"]
        self.stats["size_after"] += new_stats["size_after"]

    def _log_summary(self) -> None:
        """Log cleanup summary."""
        if self.start_time:
            self.stats["duration"] = time.time() - self.start_time
            logger.info(
                "\nCleanup Summary:\n"
                f"  Duration: {self.stats['duration']:.2f} seconds\n"
                f"  Files removed: {self.stats['files_removed']}\n"
                f"  Total size before: {self._format_size(self.stats['size_before'])}\n"
                f"  Total size after: {self._format_size(self.stats['size_after'])}"
            )

    def _format_size(self, size: int) -> str:
        """Format size in bytes to human readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


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
        cleanup = CleanupManager(config)

        success = True
        if args.all:
            success = cleanup.clean_all()
        else:
            if args.cache:
                success = success and cleanup.clean_cache()
            if args.processing:
                success = success and cleanup.clean_processing()
            if args.output:
                success = success and cleanup.clean_output()

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
