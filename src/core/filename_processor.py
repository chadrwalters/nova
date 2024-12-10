"""Filename processing functionality."""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, TypeAlias, Union

import structlog

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)

# Type aliases
DateStr: TypeAlias = str
TitleStr: TypeAlias = str
ErrorStr: TypeAlias = str
ProcessingResult: TypeAlias = Union[str, ErrorStr]


@dataclass
class ProcessedFilename:
    """Result of filename processing."""

    original_path: Path
    processed_path: Path
    date: Optional[datetime] = None
    title: Optional[str] = None
    error: Optional[str] = None


class FilenameProcessor:
    """Processor for handling filenames and paths."""

    def __init__(self, error_tolerance: bool = False) -> None:
        """Initialize the filename processor.

        Args:
            error_tolerance: Whether to continue on errors
        """
        self.error_tolerance = error_tolerance
        self.logger = logger

    def process_filename(self, path: Path) -> ProcessedFilename:
        """Process a filename to extract metadata and normalize.

        Args:
            path: Path to process

        Returns:
            Processed filename result

        Raises:
            ProcessingError: If processing fails and error_tolerance is False
        """
        try:
            # Extract date and title from filename
            date, title = self._parse_filename(path.stem)

            # Create processed path
            processed_path = self._create_processed_path(path, date, title)

            return ProcessedFilename(
                original_path=path,
                processed_path=processed_path,
                date=date,
                title=title,
            )

        except Exception as err:
            error_msg = f"Failed to process filename: {path}"
            self.logger.error(error_msg, exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(error_msg) from err
            return ProcessedFilename(
                original_path=path,
                processed_path=path,
                error=str(err),
            )

    def _parse_filename(
        self, filename: str
    ) -> tuple[Optional[datetime], Optional[str]]:
        """Parse a filename to extract date and title.

        Args:
            filename: Filename to parse

        Returns:
            Tuple of (date, title) if found, (None, None) otherwise

        Raises:
            ValueError: If date parsing fails
        """
        # Try to extract date from filename
        date_match = re.match(
            r"^(\d{4})[-_]?(\d{2})[-_]?(\d{2})[-_\s]*(.*?)$", filename
        )

        if date_match:
            year, month, day = map(int, date_match.groups()[:3])
            try:
                date = datetime(year, month, day)
                title = date_match.group(4).strip()
                return date, title or None
            except ValueError as err:
                self.logger.warning(
                    "Invalid date in filename",
                    filename=filename,
                    error=str(err),
                )
                return None, None

        # Try to extract title without date
        title_match = re.match(r"^[\w-]+(?:\s+[\w-]+)*$", filename)
        if title_match:
            return None, filename

        return None, None

    def _create_processed_path(
        self,
        original_path: Path,
        date: Optional[datetime],
        title: Optional[str],
    ) -> Path:
        """Create a processed path from components.

        Args:
            original_path: Original file path
            date: Extracted date
            title: Extracted title

        Returns:
            Processed path
        """
        # Start with the parent directory
        parent = original_path.parent

        # Create new filename
        if date and title:
            new_name = f"{date.strftime('%Y-%m-%d')}_{title}"
        elif title:
            new_name = title
        else:
            new_name = original_path.stem

        # Clean up filename
        new_name = self._clean_filename(new_name)

        # Add extension
        new_name = f"{new_name}{original_path.suffix}"

        return parent / new_name

    def _clean_filename(self, filename: str) -> str:
        """Clean a filename to be filesystem safe.

        Args:
            filename: Filename to clean

        Returns:
            Cleaned filename

        Raises:
            ValueError: If filename is empty after cleaning
        """
        # Replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

        # Replace multiple spaces/underscores with single underscore
        filename = re.sub(r"[\s_]+", "_", filename)

        # Remove leading/trailing spaces and dots
        filename = filename.strip(". ")

        # Ensure filename is not empty
        if not filename:
            filename = "unnamed"

        return filename


# Type hints for exports
__all__: list[str] = ["FilenameProcessor", "ProcessedFilename"]
