"""Factory for creating document handlers."""

import logging
from pathlib import Path
from typing import Dict, Optional, Type

from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.handlers.document import DocumentHandler
from nova.context_processor.handlers.html import HTMLHandler
from nova.context_processor.handlers.image import ImageHandler
from nova.context_processor.handlers.markdown import MarkdownHandler
from nova.context_processor.handlers.spreadsheet import SpreadsheetHandler

logger = logging.getLogger(__name__)


class HandlerFactory:
    """Factory for creating document handlers."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize factory.

        Args:
            config: Nova configuration
        """
        self.config = config
        self.handlers: Dict[str, Type[BaseHandler]] = {
            ".md": MarkdownHandler,
            ".markdown": MarkdownHandler,
            ".txt": DocumentHandler,
            ".pdf": DocumentHandler,
            ".doc": DocumentHandler,
            ".docx": DocumentHandler,
            ".html": HTMLHandler,
            ".htm": HTMLHandler,
            ".xls": SpreadsheetHandler,
            ".xlsx": SpreadsheetHandler,
            ".csv": SpreadsheetHandler,
            ".jpg": ImageHandler,
            ".jpeg": ImageHandler,
            ".png": ImageHandler,
            ".gif": ImageHandler,
            ".bmp": ImageHandler,
            ".tiff": ImageHandler,
            ".webp": ImageHandler,
            ".heic": ImageHandler,
            ".heif": ImageHandler,
            ".svg": ImageHandler,
        }

    def get_handler(self, file_path: Path) -> Optional[BaseHandler]:
        """Get handler for file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseHandler]: Handler if found, None otherwise
        """
        try:
            # Get file extension
            extension = file_path.suffix.lower()
            
            # Get handler class
            handler_class = self.handlers.get(extension)
            if not handler_class:
                logger.warning(f"No handler found for extension {extension}")
                return None

            # Create handler instance
            return handler_class(self.config)

        except Exception as e:
            logger.error(f"Failed to get handler for {file_path}: {e}")
            return None

    def register_handler(self, extension: str, handler_class: Type[BaseHandler]) -> None:
        """Register a new handler.

        Args:
            extension: File extension (with dot)
            handler_class: Handler class
        """
        self.handlers[extension.lower()] = handler_class 