"""Handler registry for file processing."""

import logging
from pathlib import Path
from typing import Dict, Optional, Type, TYPE_CHECKING

from ..config.manager import ConfigManager
from ..handlers.archive import ArchiveHandler
from ..handlers.base import BaseHandler
from ..handlers.document import DocumentHandler
from ..handlers.html import HTMLHandler
from ..handlers.image import ImageHandler
from ..handlers.markdown import MarkdownHandler
from ..handlers.spreadsheet import SpreadsheetHandler
from ..handlers.text import TextHandler
from ..handlers.video import VideoHandler

if TYPE_CHECKING:
    from ..core.pipeline import NovaPipeline

logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Registry for file handlers."""

    def __init__(self, config: ConfigManager, pipeline: "NovaPipeline"):
        """Initialize registry.

        Args:
            config: Configuration manager
            pipeline: Pipeline instance
        """
        self.config = config
        self.pipeline = pipeline
        self.handlers: Dict[str, Type[BaseHandler]] = {
            "archive": ArchiveHandler,
            "document": DocumentHandler,
            "html": HTMLHandler,
            "image": ImageHandler,
            "markdown": MarkdownHandler,
            "spreadsheet": SpreadsheetHandler,
            "text": TextHandler,
            "video": VideoHandler,
        }

    def get_handler_for_file(self, file_path: Path) -> Optional[BaseHandler]:
        """Get handler for file.

        Args:
            file_path: Path to file

        Returns:
            Optional[BaseHandler]: Handler if found, None if not
        """
        extension = file_path.suffix.lower()

        # Try each handler
        for handler_class in self.handlers.values():
            handler = handler_class(self.config, self.pipeline)
            if hasattr(handler, "supported_extensions") and extension in handler.supported_extensions:
                return handler

        return None 