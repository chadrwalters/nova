"""Text file handler."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class TextHandler(BaseHandler):
    """Handler for text files."""
    
    name = "text"
    version = "0.1.0"
    file_types = ["txt", "log", "env", "json", "yaml", "yml", "ini", "conf", "cfg"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize text handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a text file.
        
        Args:
            file_path: Path to text file.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Get relative path from input directory
            relative_path = Path(os.path.relpath(file_path, self.config.input_dir))
            
            # Get output path using relative path
            output_path = self.output_manager.get_output_path_for_phase(
                relative_path,
                "parse",
                ".parsed.md"
            )
            
            # Read text file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Format content with code block
            content = f"Text content from {file_path.stem}\n\n```\n{text}\n```"
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata['text'] = text
            
            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Write the file
            self._safe_write_file(output_path, markdown_content)
            
            metadata.add_output_file(output_path)
            
            # Save metadata using relative path
            self._save_metadata(file_path, relative_path, metadata)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process text file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg)
            metadata.processed = False
            return metadata 