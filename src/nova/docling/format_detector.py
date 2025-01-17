"""Format detector for docling."""

from pathlib import Path

import magic

from .datamodel import EXT_TO_FORMAT, MIME_TO_FORMAT, InputFormat


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
        # Try to get format from extension first
        ext = file_path.suffix.lower()
        if ext in EXT_TO_FORMAT:
            return EXT_TO_FORMAT[ext]

        # Fall back to MIME type detection
        mime_type = self._magic.from_file(str(file_path))
        if mime_type in MIME_TO_FORMAT:
            return MIME_TO_FORMAT[mime_type]

        # Format not supported
        raise ValueError(f"Unsupported format: {mime_type} for file {file_path}")
