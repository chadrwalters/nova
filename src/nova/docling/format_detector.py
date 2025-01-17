"""Format detector for docling."""

from pathlib import Path

import magic
import logging

from .datamodel import EXT_TO_FORMAT, MIME_TO_FORMAT, InputFormat

logger = logging.getLogger(__name__)


class FormatDetector:
    """Format detector for docling."""

    def __init__(self) -> None:
        """Initialize format detector."""
        self._magic = magic.Magic(mime=True)

    def detect_format(self, file_path: Path) -> InputFormat | None:
        """Detect the format of a file.

        Args:
            file_path: Path to the file

        Returns:
            InputFormat if detected, None otherwise
        """
        # Skip system files
        if file_path.name.startswith('.'):
            logger.debug(f"Skipping system file: {file_path}")
            return None

        try:
            # Get MIME type
            mime_type = magic.from_file(str(file_path), mime=True)
            logger.debug(f"Detected MIME type {mime_type} for file {file_path}")

            # Map MIME type to format
            if mime_type in MIME_TO_FORMAT:
                return MIME_TO_FORMAT[mime_type]

            logger.error(f"Unsupported format: {mime_type} for file {file_path}")
            return None

        except Exception as e:
            logger.error(f"Failed to detect format for {file_path}: {e}")
            return None
