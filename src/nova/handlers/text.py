"""Text file handler."""

import csv
import io
import os
import re
import chardet
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class TextHandler(BaseHandler):
    """Handler for text files."""
    
    name = "text"
    version = "0.1.0"
    file_types = ["txt", "json", "xml"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize text handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    async def _process_content(self, file_path: Path) -> str:
        """Process text file content.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Processed content.
        """
        # Read file content
        content = self._safe_read_file(file_path)
        
        # Split into lines and remove trailing whitespace
        lines = [line.rstrip() for line in content.splitlines()]
        
        # Remove empty lines at start and end
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        # Join lines back together
        return "\n".join(lines) 
    
    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a text file.
        
        Args:
            file_path: Path to text file.
            output_dir: Directory to write output files.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Create output directory
            output_dir = Path(str(output_dir))
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create markdown file
            markdown_path = output_dir / f"{file_path.stem}.parsed.md"
            
            # Read text file
            text = self._safe_read_file(file_path)
            
            # Write markdown file with text content and reference to original
            self._write_markdown(markdown_path, file_path.stem, file_path, f"```\n{text}\n```")
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['text'] = text
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process text file {file_path}: {str(e)}")
            return None 