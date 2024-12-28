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
    
    def _register_default_handlers(self) -> None:
        """Register default handlers."""
        handlers = [
            DocumentHandler(self.config),
            ImageHandler(self.config),
            TextHandler(self.config),
            MarkdownHandler(self.config),
            SpreadsheetHandler(self.config),
            HTMLHandler(self.config),
        ]
        
        for handler in handlers:
            for file_type in handler.file_types:
                self.logger.debug(f"Registering {handler.name} for file type: {file_type}")
                self.handlers[file_type] = handler
    
    def get_handler(self, file_path: Union[str, Path]) -> Optional[BaseHandler]:
        """Get handler for file.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Handler for file type, or None if no handler found.
        """
        file_path = Path(file_path)
        
        # Skip ignored files
        if file_path.name in self.IGNORED_FILES:
            return None
        
        try:
            # Try to get file type normally
            file_type = file_path.suffix.lstrip('.').lower()
        except UnicodeError:
            # If that fails, try to handle paths with non-UTF-8 characters
            try:
                # Convert path to string with replacement of invalid chars
                file_str = str(file_path).encode('utf-8', errors='replace').decode('utf-8')
                file_type = Path(file_str).suffix.lstrip('.').lower()
            except Exception as e:
                self.logger.error(f"Failed to get file type from path: {str(e)}")
                return None
        
        return self.handlers.get(file_type) 

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
            file_path = Path(file_path)
            
            # Skip ignored files without creating metadata
            if file_path.name in self.IGNORED_FILES:
                self.logger.debug(f"Skipping ignored file: {file_path.name}")
                return None
            
            # Get handler for file
            handler = self.get_handler(file_path)
            
            if handler is None:
                # Create metadata for unsupported files
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
            return await handler.process(
                file_path,
                output_dir=output_dir,
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process file {file_path}: {str(e)}")
            metadata = DocumentMetadata.from_file(
                file_path=file_path,
                handler_name="registry",
                handler_version="0.1.0",
            )
            metadata.processed = False
            metadata.add_error("registry", str(e))
            return metadata 