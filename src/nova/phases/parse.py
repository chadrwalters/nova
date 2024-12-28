"""Parse phase of the Nova pipeline."""

import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union
import os

from ..config.manager import ConfigManager
from ..handlers.registry import HandlerRegistry
from ..models.document import DocumentMetadata
from ..cache.manager import CacheManager


class ParsePhase:
    """Parse phase of the Nova pipeline."""
    
    # Files to ignore
    IGNORED_FILES = {".DS_Store"}
    
    def __init__(
        self,
        config: ConfigManager,
        handler_registry: HandlerRegistry,
    ) -> None:
        """Initialize parse phase.
        
        Args:
            config: Nova configuration manager.
            handler_registry: Handler registry.
        """
        self.config = config
        self.handler_registry = handler_registry
        self.logger = logging.getLogger(__name__)
        self.cache_manager = CacheManager(config)
    
    def _write_error_markdown(self, markdown_path: Path, title: str, relative_path: str, error_msg: str) -> None:
        """Write error message to markdown file.
        
        Args:
            markdown_path: Path to markdown file.
            title: Title for markdown file.
            relative_path: Relative path to original file.
            error_msg: Error message.
        """
        # Force replacement of any invalid unicode chars in the error message
        safe_error_msg = error_msg.encode("utf-8", errors="replace").decode("utf-8")

        content = f"""# {title}

[Download Original]({relative_path})

## Error

{safe_error_msg}
"""
        # Write with UTF-8 encoding and replace any invalid characters
        with open(markdown_path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(content)
    
    async def process(
        self,
        file_path: Union[str, Path],
        output_path: Union[str, Path],
        metadata: Optional[DocumentMetadata] = None,
    ) -> Optional[DocumentMetadata]:
        """Process a file through the parse phase.
        
        Args:
            file_path: Path to file to process.
            output_path: Path to output file.
            metadata: Optional metadata from previous phase.
            
        Returns:
            Updated document metadata, or None if file is ignored.
        """
        # Convert paths safely
        file_path = Path(str(file_path).encode("utf-8", errors="replace").decode("utf-8"))
        output_path = Path(str(output_path).encode("utf-8", errors="replace").decode("utf-8"))
        
        self.logger.debug(f"Processing file in parse phase: {file_path}")
        
        # Check if file should be ignored
        if file_path.name in self.IGNORED_FILES:
            self.logger.debug(f"Ignoring file: {file_path}")
            return None
            
        # Get handler for file type
        handler = self.handler_registry.get_handler(file_path)
        if handler is None:
            self.logger.debug(f"No handler found for file: {file_path}")
            return metadata
            
        # Create output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get relative path from input directory
        rel_path = file_path.relative_to(Path(self.config.input_dir))
        
        # Process file with handler
        try:
            # Process file using the handler
            metadata = await handler.process(
                file_path=file_path,
                output_dir=Path(self.config.processing_dir) / "phases" / "parse" / rel_path.parent,
                metadata=metadata,
            )
            
            if metadata is None:
                metadata = DocumentMetadata.from_file(
                    file_path=file_path,
                    handler_name=handler.name,
                    handler_version=handler.version,
                )
            
            metadata.processed = True
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error processing file: {str(e)}")
            if metadata is not None:
                metadata.add_error("parse", str(e))
            
            return metadata 