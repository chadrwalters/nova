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
            
        Raises:
            UnicodeDecodeError: If file contains invalid UTF-8.
        """
        # Read file content
        with open(file_path, 'rb') as f:
            raw_content = f.read()
            
        # Try to decode as UTF-8
        try:
            content = raw_content.decode('utf-8')
        except UnicodeDecodeError:
            # Try to detect encoding
            detected = chardet.detect(raw_content)
            if detected['encoding'] is None:
                raise UnicodeDecodeError(
                    'utf-8', raw_content, 0, len(raw_content),
                    'File contains invalid or binary data'
                )
            content = raw_content.decode(detected['encoding'])
        
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
            # Get output path from output manager
            markdown_path = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Read text file
            text = await self._process_content(file_path)
            
            # Write markdown file with text content
            content = f"""# {file_path.stem}

--==SUMMARY==--
Text content from {file_path.stem}

--==RAW NOTES==--
```
{text}
```
"""
            # Write with UTF-8 encoding and replace any invalid characters
            self._safe_write_file(markdown_path, content, encoding='utf-8')
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.metadata['text'] = text
            metadata.output_files.add(markdown_path)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process text file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg)
            metadata.processed = False
            return None 