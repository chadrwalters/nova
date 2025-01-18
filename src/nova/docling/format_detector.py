"""Format detector class."""

import logging
import mimetypes
from pathlib import Path

import magic

from .datamodel import EXT_TO_FORMAT, MIME_TO_FORMAT, InputFormat

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)  # Set to WARNING to reduce noise


class FormatDetector:
    """Detects input format of files."""

    def __init__(self) -> None:
        """Initialize the format detector."""
        self._magic = magic.Magic(mime=True)

    def detect_format(self, file_path: Path) -> InputFormat | None:
        """Detect format of a file.

        Args:
            file_path: Path to file to detect format of.

        Returns:
            Detected format or None if format is not supported.
        """
        try:
            # First try extension-based detection for known formats
            ext = file_path.suffix.lower()
            if ext == ".md":
                return InputFormat.MD

            # Try to detect MIME type using magic
            mime_type = self._magic.from_file(str(file_path))

            # Special handling for text/plain files
            if mime_type == "text/plain":
                # Check if it's a markdown file by extension
                if ext == ".md":
                    return InputFormat.MD
                # Check if it's a known format by extension
                fmt = EXT_TO_FORMAT.get(ext)
                if fmt:
                    return fmt
                # Default to TEXT for unknown extensions
                return InputFormat.TEXT

            # Try to get format from MIME type
            fmt = MIME_TO_FORMAT.get(mime_type)
            if fmt:
                return fmt

            # Try to get format from file extension
            fmt = EXT_TO_FORMAT.get(ext)
            if fmt:
                return fmt

            # Try to get format from mimetypes module
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type:
                fmt = MIME_TO_FORMAT.get(mime_type)
                if fmt:
                    return fmt

            logger.warning(f"Unsupported format for {file_path} (MIME: {mime_type}, ext: {ext})")
            return None

        except Exception as e:
            logger.error(f"Failed to detect format for {file_path}: {e}")
            return None
