"""Registry for document handlers."""

from pathlib import Path
from typing import Dict, List, Optional, Type, Union
import logging

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from .base import BaseHandler
from .document import DocumentHandler
from .image import ImageHandler
from .text import TextHandler
from .markdown import MarkdownHandler
from .spreadsheet import SpreadsheetHandler
from .html import HTMLHandler
from .video import VideoHandler


class HandlerRegistry:
    """Registry for document handlers."""
    
    # Files to ignore
    IGNORED_FILES = {".DS_Store"}
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize registry.
        
        Args:
            config: Nova configuration manager.
        """
        self.config = config
        self.handlers: Dict[str, BaseHandler] = {}
        self.logger = logging.getLogger(__name__)
        self._register_default_handlers()
    
    def register_handler(self, handler_class: Type[BaseHandler]) -> None:
        """Register a new handler.
        
        Args:
            handler_class: Handler class to register.
        """
        handler = handler_class(self.config)
        for file_type in handler.file_types:
            self.logger.debug(f"Registering {handler.name} for file type: {file_type}")
            self.handlers[file_type] = handler
    
    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        default_handlers = [
            DocumentHandler,
            ImageHandler,
            TextHandler,
            MarkdownHandler,
            SpreadsheetHandler,
            HTMLHandler,
            VideoHandler,
        ]
        
        for handler_class in default_handlers:
            self.register_handler(handler_class)
    
    def get_handler(self, file_path: Union[str, Path]) -> Optional[BaseHandler]:
        """Get handler for file.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Handler for file type, or None if no handler found.
        """
        try:
            file_path = Path(file_path)
            self.logger.debug(f"Getting handler for file: {file_path}")
            self.logger.debug(f"File exists: {file_path.exists()}")
            self.logger.debug(f"File is file: {file_path.is_file()}")
            
            # Skip ignored files
            if file_path.name in self.IGNORED_FILES:
                self.logger.debug(f"Skipping ignored file: {file_path.name}")
                return None
            
            # Try to get file type normally
            file_type = file_path.suffix.lstrip('.').lower()
            self.logger.debug(f"Looking for handler for file type: {file_type}")
            self.logger.debug(f"Available handlers: {list(self.handlers.keys())}")
            self.logger.debug(f"File path: {file_path}")
            self.logger.debug(f"File suffix: {file_path.suffix}")
            self.logger.debug(f"File type: {file_type}")
            self.logger.debug(f"File name: {file_path.name}")
            self.logger.debug(f"File stem: {file_path.stem}")
            
            # Get handler for file type
            handler = self.handlers.get(file_type)
            if handler is None:
                self.logger.debug(f"No handler found for file type: {file_type}")
            else:
                self.logger.debug(f"Found handler {handler.name} for file type: {file_type}")
            return handler
            
        except UnicodeError:
            # If that fails, try to handle paths with non-UTF-8 characters
            try:
                # Convert path to string with replacement of invalid chars
                file_str = str(file_path).encode('utf-8', errors='replace').decode('utf-8')
                file_type = Path(file_str).suffix.lstrip('.').lower()
                self.logger.debug(f"Looking for handler for file type (after unicode handling): {file_type}")
                return self.handlers.get(file_type)
            except Exception as e:
                self.logger.error(f"Failed to get file type from path: {str(e)}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get handler for file: {str(e)}")
            return None

    async def process_file(
        self,
        file_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
    ) -> Optional[DocumentMetadata]:
        """Process a file.
        
        Args:
            file_path: Path to file to process.
            output_dir: Optional output directory. If not provided,
                will use configured output directory.
                
        Returns:
            Document metadata, or None if file is ignored or processing fails.
        """
        try:
            # Log initial file path info
            self.logger.debug(f"process_file called with file_path: {file_path} (type: {type(file_path)})")
            
            # Convert to Path if needed
            if isinstance(file_path, str):
                self.logger.debug(f"Converting file_path from str to Path")
                file_path = Path(file_path)
            
            self.logger.debug(f"File path after conversion: {file_path}")
            self.logger.debug(f"File exists: {file_path.exists()}")
            self.logger.debug(f"File is file: {file_path.is_file()}")
            self.logger.debug(f"File suffix: {file_path.suffix}")
            self.logger.debug(f"File name: {file_path.name}")
            
            # Skip ignored files without creating metadata
            if file_path.name in self.IGNORED_FILES:
                self.logger.debug(f"Skipping ignored file: {file_path.name}")
                return None
            
            # Get handler for file
            self.logger.debug(f"Looking up handler for file type: {file_path.suffix}")
            handler = self.get_handler(file_path)
            self.logger.debug(f"Handler lookup result: {handler.name if handler else None}")
            
            if handler is None:
                # Create metadata for unsupported files
                self.logger.debug(f"No handler found, creating error metadata")
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name="registry",
                    handler_version="0.1.0",
                )
                metadata.processed = False
                metadata.add_error("registry", f"No handler found for file type: {file_path.suffix}")
                return metadata
            
            self.logger.info(f"Using {handler.name} handler for file: {file_path}")
            
            # Process file
            try:
                result = await handler.process(
                    file_path,
                    output_dir=output_dir,
                )
                self.logger.debug(f"Handler process result: {result}")
                return result
            except Exception as e:
                self.logger.exception(f"Handler {handler.name} failed to process file: {file_path}")
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name=handler.name,
                    handler_version=handler.version,
                )
                metadata.processed = False
                metadata.add_error(handler.name, str(e))
                return metadata
            
        except Exception as e:
            self.logger.exception(f"Failed to process file {file_path}: {str(e)}")
            metadata = DocumentMetadata.from_file(
                file_path=file_path,
                handler_name="registry",
                handler_version="0.1.0",
            )
            metadata.processed = False
            metadata.add_error("registry", str(e))
            return metadata 