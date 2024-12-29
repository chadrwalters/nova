"""Markdown file handler."""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.document import DocumentMetadata
from .base import BaseHandler
from ..config.manager import ConfigManager


class MarkdownHandler(BaseHandler):
    """Handler for markdown files."""
    
    name = "markdown"
    version = "0.1.0"
    file_types = ["md", "markdown"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize markdown handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
    
    def _update_image_links(self, content: str) -> str:
        """Update image links to point to .parsed.md files.
        
        Args:
            content: Original markdown content.
            
        Returns:
            Updated markdown content.
        """
        # Match both ![...](path) and [name](path) patterns
        def replace_link(match):
            full_match = match.group(0)
            path = match.group(2)
            
            # Skip if it's already a .parsed.md file
            if path.endswith('.parsed.md'):
                return full_match
                
            # Convert the path to point to the parsed markdown file
            new_path = path + '.parsed.md'
            
            # Replace the old path with the new one, preserving any metadata
            return full_match.replace(path, new_path)
            
        # Update both image and link patterns, including those with metadata
        pattern = r'(!?\[.*?\])\((.*?)\)(?:<!-- \{.*?\} -->)?'
        return re.sub(pattern, replace_link, content)

    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process a markdown file.
        
        Args:
            file_path: Path to markdown file.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Get output path from output manager
            output_file = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update image links to point to .parsed.md files
            updated_content = self._update_image_links(content)
            
            # Write the updated content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.output_files.append(output_file)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process markdown file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg)
            metadata.processed = False
            return metadata 