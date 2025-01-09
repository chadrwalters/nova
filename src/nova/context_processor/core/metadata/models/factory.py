"""Factory for creating metadata instances."""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Type

from nova.context_processor.core.metadata.models.base import BaseMetadata
from nova.context_processor.core.metadata.models.types import (
    DocumentMetadata,
    HTMLMetadata,
    ImageMetadata,
    MarkdownMetadata,
    SpreadsheetMetadata,
)

logger = logging.getLogger(__name__)


class MetadataFactory:
    """Factory for creating metadata objects."""

    @staticmethod
    def get_metadata_class(file_path: Path) -> Type[BaseMetadata]:
        """Get metadata class for file type.

        Args:
            file_path: Path to file

        Returns:
            Type[BaseMetadata]: Metadata class for file type
        """
        extension = file_path.suffix.lower()

        if extension == ".md":
            return MarkdownMetadata
        elif extension in {".pdf", ".docx", ".txt"}:
            return DocumentMetadata
        elif extension in {".xlsx", ".csv"}:
            return SpreadsheetMetadata
        elif extension == ".html":
            return HTMLMetadata
        elif extension in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic", ".heif", ".svg"}:
            return ImageMetadata
        else:
            return BaseMetadata

    @staticmethod
    def create_metadata(file_path: Path) -> Optional[BaseMetadata]:
        """Create metadata object for file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseMetadata]: Metadata object if successful, None if failed
        """
        try:
            metadata_class = MetadataFactory.get_metadata_class(file_path)
            return metadata_class(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
                output_files=set(),
            )
        except Exception as e:
            logger.error(f"Failed to create metadata for {file_path}: {str(e)}")
            return None 