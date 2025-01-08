"""Factory for creating metadata instances."""

import logging
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
    """Factory for creating metadata instances."""

    _handlers = {
        ".md": MarkdownMetadata,
        ".markdown": MarkdownMetadata,
        ".txt": DocumentMetadata,
        ".pdf": DocumentMetadata,
        ".doc": DocumentMetadata,
        ".docx": DocumentMetadata,
        ".html": HTMLMetadata,
        ".htm": HTMLMetadata,
        ".xls": SpreadsheetMetadata,
        ".xlsx": SpreadsheetMetadata,
        ".csv": SpreadsheetMetadata,
        ".jpg": ImageMetadata,
        ".jpeg": ImageMetadata,
        ".png": ImageMetadata,
        ".gif": ImageMetadata,
        ".bmp": ImageMetadata,
        ".tiff": ImageMetadata,
        ".webp": ImageMetadata,
    }

    @classmethod
    def create(
        cls,
        file_path: Path,
        handler_name: str,
        handler_version: str,
        file_type: Optional[str] = None,
        file_hash: Optional[str] = None,
    ) -> BaseMetadata:
        """Create metadata instance.

        Args:
            file_path: Path to file
            handler_name: Name of handler
            handler_version: Version of handler
            file_type: Optional file type
            file_hash: Optional file hash

        Returns:
            BaseMetadata: Metadata instance
        """
        try:
            # Get file extension
            extension = file_path.suffix.lower()
            
            # Get metadata class
            metadata_class = cls._handlers.get(extension, BaseMetadata)

            # Create metadata instance
            metadata = metadata_class(
                file_path=file_path,
                file_name=file_path.name,
                handler_name=handler_name,
                handler_version=handler_version,
                file_type=file_type or extension,
                file_hash=file_hash,
            )

            return metadata

        except Exception as e:
            logger.error(f"Failed to create metadata for {file_path}: {e}")
            return BaseMetadata(
                file_path=file_path,
                file_name=file_path.name,
                handler_name=handler_name,
                handler_version=handler_version,
                file_type=file_type or file_path.suffix.lower(),
                file_hash=file_hash,
            )

    @classmethod
    def register_handler(cls, extension: str, metadata_class: Type[BaseMetadata]) -> None:
        """Register a new metadata handler.

        Args:
            extension: File extension (with dot)
            metadata_class: Metadata class
        """
        cls._handlers[extension.lower()] = metadata_class 