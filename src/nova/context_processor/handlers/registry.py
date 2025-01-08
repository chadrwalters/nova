"""Handler registry for document processing."""

import logging
import mimetypes
from pathlib import Path
from typing import Dict, Optional, Type, TYPE_CHECKING

from ..core.metadata import BaseMetadata, MetadataFactory
from .archive import ArchiveHandler
from .audio import AudioHandler
from .base import BaseHandler
from .document import DocumentHandler
from .html import HTMLHandler
from .image import ImageHandler
from .markdown import MarkdownHandler
from .spreadsheet import SpreadsheetHandler
from .video import VideoHandler

if TYPE_CHECKING:
    from ..config.manager import ConfigManager
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Registry of document handlers."""

    def __init__(self, config: "ConfigManager", pipeline: "NovaPipeline"):
        """Initialize handler registry.
        
        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        self.config = config
        self.pipeline = pipeline
        self.handlers: Dict[str, Type[BaseHandler]] = {}
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        # Register handlers by file extension
        self.register_handler(".md", MarkdownHandler)
        self.register_handler(".txt", DocumentHandler)
        self.register_handler(".docx", DocumentHandler)
        self.register_handler(".doc", DocumentHandler)
        self.register_handler(".rtf", DocumentHandler)
        self.register_handler(".odt", DocumentHandler)
        self.register_handler(".pdf", DocumentHandler)
        
        # Image handlers
        self.register_handler(".jpg", ImageHandler)
        self.register_handler(".jpeg", ImageHandler)
        self.register_handler(".png", ImageHandler)
        self.register_handler(".gif", ImageHandler)
        self.register_handler(".heic", ImageHandler)
        self.register_handler(".webp", ImageHandler)
        
        # Audio handlers
        self.register_handler(".mp3", AudioHandler)
        self.register_handler(".wav", AudioHandler)
        self.register_handler(".m4a", AudioHandler)
        self.register_handler(".ogg", AudioHandler)
        
        # Video handlers
        self.register_handler(".mp4", VideoHandler)
        self.register_handler(".mov", VideoHandler)
        self.register_handler(".avi", VideoHandler)
        self.register_handler(".mkv", VideoHandler)
        
        # Spreadsheet handlers
        self.register_handler(".xlsx", SpreadsheetHandler)
        self.register_handler(".xls", SpreadsheetHandler)
        self.register_handler(".csv", SpreadsheetHandler)
        
        # HTML handlers
        self.register_handler(".html", HTMLHandler)
        self.register_handler(".htm", HTMLHandler)
        
        # Archive handlers
        self.register_handler(".zip", ArchiveHandler)
        self.register_handler(".tar", ArchiveHandler)
        self.register_handler(".gz", ArchiveHandler)
        self.register_handler(".7z", ArchiveHandler)

    def register_handler(self, extension: str, handler_class: Type[BaseHandler]) -> None:
        """Register a handler for a file extension.

        Args:
            extension: File extension (with dot)
            handler_class: Handler class to register
        """
        self.handlers[extension.lower()] = handler_class

    def get_handler_for_file(self, file_path: Path) -> Optional[BaseHandler]:
        """Get appropriate handler for a file.

        Args:
            file_path: Path to file

        Returns:
            Handler instance if found, None otherwise
        """
        extension = file_path.suffix.lower()
        handler_class = self.handlers.get(extension)
        
        if handler_class:
            return handler_class(self.config, self.pipeline)
            
        return None

    def process_file(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: Optional[BaseMetadata] = None,
    ) -> Optional[BaseMetadata]:
        """Process a file with the appropriate handler.

        Args:
            file_path: Path to file to process
            output_dir: Output directory
            metadata: Optional metadata from previous processing

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Get file type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if not mime_type:
                mime_type = "application/octet-stream"

            # Get handler
            handler = self.get_handler_for_file(file_path)
            if not handler:
                logger.warning(f"No handler found for {file_path}")
                return None

            # Create metadata if not provided
            if not metadata:
                metadata = MetadataFactory.create(
                    file_path=file_path,
                    file_type=mime_type,
                    handler_name=handler.__class__.__name__,
                    handler_version=handler.version,
                )

            # Process file
            return handler.process_file(file_path, output_dir, metadata)

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            if metadata:
                metadata.add_error("HandlerRegistry", str(e))
            return None
