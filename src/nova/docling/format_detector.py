"""Format detector for docling."""

import magic  # type: ignore
from pathlib import Path

from .datamodel import InputFormat, MIME_TO_FORMAT, EXT_TO_FORMAT

class FormatDetector:
    """Format detector for docling."""

    def __init__(self) -> None:
        """Initialize format detector."""
        self._magic = magic.Magic(mime=True)

    def detect_format(self, file_path: Path) -> InputFormat:
        """Detect format of file.

        Args:
            file_path: Path to file.

        Returns:
            InputFormat: Detected format.

        Raises:
            ValueError: If format is not supported.
        """
        # Get MIME type
        mime_type = self._magic.from_file(str(file_path))

        # Try to get format from MIME type
        if mime_type in MIME_TO_FORMAT:
            return MIME_TO_FORMAT[mime_type]

        # Try to get format from extension
        ext = file_path.suffix.lower()
        if ext in EXT_TO_FORMAT:
            return EXT_TO_FORMAT[ext]

        # Format not supported
        raise ValueError(f"Unsupported format: {mime_type} for file {file_path}")
