import mimetypes
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import magic

from src.core.exceptions import ProcessingError
from src.core.logging import get_logger


@dataclass
class ProcessedAttachment:
    """Represents a processed attachment with its metadata."""

    source_path: Path
    target_path: Path
    size: int
    content_type: str = "application/octet-stream"
    preview_path: Optional[Path] = None
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class AttachmentProcessor:
    """Processes attachments in markdown documents."""

    def __init__(self, media_dir: Path, error_tolerance: bool = False) -> None:
        """Initialize the attachment processor.

        Args:
            media_dir: Directory for media files
            error_tolerance: Whether to continue on errors
        """
        self.media_dir = media_dir
        self.error_tolerance = error_tolerance
        self.logger = get_logger()

        # Create media directory
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def process_attachment(
        self, file_path: Path, target_name: Optional[str] = None
    ) -> Optional[ProcessedAttachment]:
        """Process an attachment file.

        Args:
            file_path: Path to the attachment file
            target_name: Optional target filename

        Returns:
            ProcessedAttachment object with processed file information
        """
        try:
            # Generate target path
            if target_name is None:
                target_name = file_path.name
            target_path = self.media_dir / target_name

            # Copy file to media directory
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target_path)

            # Get file metadata
            content_type = magic.from_file(str(file_path), mime=True)
            size = file_path.stat().st_size

            return ProcessedAttachment(
                source_path=file_path,
                target_path=target_path,
                size=size,
                content_type=content_type,
                metadata={
                    "mime_type": content_type,
                    "original_name": file_path.name,
                },
            )

        except Exception as err:
            self.logger.error(f"Error processing attachment {file_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to process attachment {file_path}"
                ) from err
            return None

    def _get_relative_media_path(self, file_path: Path) -> str:
        """Get relative path for media reference.

        Args:
            file_path: Path to the media file

        Returns:
            Relative path from media directory
        """
        try:
            return str(file_path.relative_to(self.media_dir))
        except ValueError as err:
            self.logger.error(
                f"Error getting relative path for {file_path}", exc_info=err
            )
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to get relative path for {file_path}"
                ) from err
            return str(file_path)
