"""Directory management for Nova."""

import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..config.manager import ConfigManager
from ..core.errors import ResourceError

logger = logging.getLogger(__name__)


class DirectoryManager:
    """Manager for directory operations."""

    # Required subdirectories in processing directory
    PROCESSING_SUBDIRS = {
        "cache": "cache/",
        "metadata": "metadata/",
        "index": "index/",
        "notes": "notes/",
        "attachments": "attachments/",
    }

    # Patterns to exclude from cleanup
    EXCLUDE_PATTERNS = [
        ".gitkeep",
        ".git",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".DS_Store",
        ".env",
        ".venv",
        "venv",
        "ENV",
    ]

    # Patterns for temporary files to clean
    TEMP_PATTERNS = [
        "*.parsed.md",
        "*.parsed",
        "*.metadata",
        "*.png.png",  # Duplicate image conversions
        "*.svg.png.png",
        "*.jpg.png",
        "*.jpeg.png",
        "*.svg.png",  # Additional image conversion patterns
        "*.svg.jpg",
        "*.png.jpg",
        "*.jpg.jpg",
        "*.jpeg.jpg",
        "*.heic.jpg",
        "*.heic.png",
        "*.webp.jpg",
        "*.webp.png",
        "*.bmp.jpg",
        "*.bmp.png",
        "*.tiff.jpg",
        "*.tiff.png",
        "*.gif.jpg",
        "*.gif.png",
        "*.tmp",  # Temporary files
        "*.temp",
        "*.bak",
        "~*",  # Backup files
        "*.swp",  # Vim swap files
        "*.swo",
        "*.swn",
        "*.swm",
        "*.swl",
        "*.swk",
        "*.swj",
        "*.swi",
        "*.swh",
        "*.swg",
        "*.swf",
        "*.swe",
        "*.swd",
        "*.swc",
        "*.swb",
        "*.swa",
    ]

    def __init__(self, config: ConfigManager):
        """Initialize directory manager.

        Args:
            config: Nova configuration manager
        """
        self.config = config
        self.base_dir = config.base_dir
        self.input_dir = config.input_dir
        self.output_dir = config.output_dir
        self.processing_dir = config.processing_dir

    def validate_structure(self) -> None:
        """Validate directory structure.

        Raises:
            ResourceError: If directory structure is invalid
        """
        # Check base directories
        self._validate_directory(self.base_dir, "Base")
        self._validate_directory(self.input_dir, "Input")
        self._validate_directory(self.output_dir, "Output")
        self._validate_directory(self.processing_dir, "Processing")

        # Check processing subdirectories
        for name, path in self.PROCESSING_SUBDIRS.items():
            subdir = self.processing_dir / path
            self._validate_directory(subdir, f"Processing {name}")

    def create_structure(self) -> None:
        """Create directory structure if it doesn't exist."""
        # Create base directories
        self._create_directory(self.base_dir, "Base")
        self._create_directory(self.input_dir, "Input")
        self._create_directory(self.output_dir, "Output")
        self._create_directory(self.processing_dir, "Processing")

        # Create processing subdirectories
        for name, path in self.PROCESSING_SUBDIRS.items():
            subdir = self.processing_dir / path
            self._create_directory(subdir, f"Processing {name}")

    def clean_directory(self, path: Path, name: str, recursive: bool = True) -> tuple[bool, Dict[str, int]]:
        """Clean a directory.

        Args:
            path: Directory path to clean
            name: Name of directory for logging
            recursive: Whether to clean subdirectories

        Returns:
            Tuple of (success, stats) where stats contains files_removed, size_before, size_after
        """
        try:
            if not path.exists():
                logger.info(f"{name} directory already clean")
                return True, {"files_removed": 0, "size_before": 0, "size_after": 0}

            # Get directory stats before cleanup
            stats_before = self._get_directory_stats(path)
            total_files_removed = 0

            # Remove temporary files first
            files_removed = 0
            for pattern in self.TEMP_PATTERNS:
                for item in path.glob("**/" + pattern if recursive else pattern):
                    if item.is_file() and not self._should_exclude(item):
                        item.unlink()
                        files_removed += 1
                        total_files_removed += 1
                        logger.debug(f"Removed temporary file: {item}")

            # Remove empty .parsed.md directories
            if recursive:
                for parsed_dir in path.glob("**/*.parsed.md"):
                    if parsed_dir.is_dir() and not any(parsed_dir.iterdir()):
                        parsed_dir.rmdir()
                        logger.debug(f"Removed empty parsed directory: {parsed_dir}")

            # Remove duplicate directories
            if recursive:
                seen_names = set()
                for subdir in path.glob("**/*"):
                    if subdir.is_dir() and not self._should_exclude(subdir):
                        # Get the base name without any extensions
                        base_name = subdir.name
                        while "." in base_name:
                            base_name = base_name.rsplit(".", 1)[0]

                        # If we've seen this base name before, it's a duplicate
                        if base_name in seen_names:
                            try:
                                # Move any files to the original directory
                                original_dir = next(path.glob(f"**/{base_name}"))
                                if original_dir != subdir:  # Don't try to move to itself
                                    for item in subdir.iterdir():
                                        if item.is_file():
                                            try:
                                                item.rename(original_dir / item.name)
                                            except OSError:
                                                # If rename fails (e.g., file exists), just remove it
                                                item.unlink()
                                                files_removed += 1
                                                total_files_removed += 1
                                    # Remove the empty duplicate directory
                                    subdir.rmdir()
                                    logger.debug(f"Removed duplicate directory: {subdir}")
                            except Exception as e:
                                logger.warning(f"Failed to clean up duplicate directory {subdir}: {e}")
                        else:
                            seen_names.add(base_name)

            # Remove regular files
            for item in path.iterdir():
                if item.is_file() and not self._should_exclude(item):
                    item.unlink()
                    files_removed += 1
                    total_files_removed += 1

            if recursive:
                # Clean subdirectories
                for subdir in path.iterdir():
                    if subdir.is_dir() and not self._should_exclude(subdir):
                        success, sub_stats = self.clean_directory(subdir, f"{name}/{subdir.name}")
                        if not success:
                            return False, {}
                        total_files_removed += sub_stats["files_removed"]

            # Get directory stats after cleanup
            stats_after = self._get_directory_stats(path)

            # Remove empty directories (except excluded ones)
            if recursive:
                for subdir in reversed(list(path.glob("**/*"))):
                    if subdir.is_dir() and not self._should_exclude(subdir) and not any(subdir.iterdir()):
                        try:
                            subdir.rmdir()
                            logger.debug(f"Removed empty directory: {subdir}")
                        except OSError:
                            pass  # Directory not empty or permission denied

            # Prepare stats
            stats = {
                "files_removed": total_files_removed,
                "size_before": stats_before["size"],
                "size_after": stats_after["size"]
            }

            # Log cleanup results
            logger.info(
                f"{name} directory cleaned successfully:\n"
                f"  - Files removed: {files_removed}\n"
                f"  - Size before: {self._format_size(stats_before['size'])}\n"
                f"  - Size after: {self._format_size(stats_after['size'])}"
            )

            return True, stats

        except Exception as e:
            logger.error(f"Failed to clean {name} directory: {e}")
            return False, {}

    def _validate_directory(self, path: Path, name: str) -> None:
        """Validate a directory.

        Args:
            path: Directory path to validate
            name: Name of directory for logging

        Raises:
            ResourceError: If directory is invalid
        """
        try:
            if not path.exists():
                raise ResourceError(
                    message=f"{name} directory does not exist: {path}",
                    file_path=path,
                    recovery_hint=f"Create the {name.lower()} directory.",
                )

            if not path.is_dir():
                raise ResourceError(
                    message=f"{name} path is not a directory: {path}",
                    file_path=path,
                    recovery_hint=f"Remove the file and create a directory for {name.lower()}.",
                )

            if not os.access(path, os.R_OK | os.W_OK):
                raise ResourceError(
                    message=f"{name} directory is not readable/writable: {path}",
                    file_path=path,
                    recovery_hint=f"Check permissions for the {name.lower()} directory.",
                )

        except Exception as e:
            if not isinstance(e, ResourceError):
                raise ResourceError(
                    message=f"Failed to validate {name.lower()} directory: {e}",
                    file_path=path,
                    recovery_hint=f"Check the {name.lower()} directory configuration.",
                    original_error=e,
                )
            raise

    def _create_directory(self, path: Path, name: str) -> None:
        """Create a directory if it doesn't exist.

        Args:
            path: Directory path to create
            name: Name of directory for logging
        """
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created {name.lower()} directory: {path}")
            else:
                logger.debug(f"{name} directory exists: {path}")

        except Exception as e:
            logger.error(f"Failed to create {name.lower()} directory: {e}")
            raise ResourceError(
                message=f"Failed to create {name.lower()} directory: {e}",
                file_path=path,
                recovery_hint=f"Check permissions and try creating the {name.lower()} directory manually.",
                original_error=e,
            )

    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from cleanup.

        Args:
            path: Path to check

        Returns:
            bool: True if path should be excluded
        """
        name = path.name
        return any(name == pattern or path.match(pattern) for pattern in self.EXCLUDE_PATTERNS)

    def _get_directory_stats(self, path: Path) -> Dict[str, int]:
        """Get directory statistics.

        Args:
            path: Directory path

        Returns:
            Dict with directory statistics
        """
        total_size = 0
        total_files = 0
        total_dirs = 0

        for item in path.rglob("*"):
            if item.is_file():
                total_size += item.stat().st_size
                total_files += 1
            elif item.is_dir():
                total_dirs += 1

        return {
            "size": total_size,
            "files": total_files,
            "dirs": total_dirs,
        }

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