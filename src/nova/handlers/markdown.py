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
    
    def _update_links(self, content: str) -> str:
        """Update links to use simple reference markers.
        
        Args:
            content: Original markdown content.
            
        Returns:
            Updated markdown content.
        """
        # First remove any existing HTML comments
        content = re.sub(r'<!--.*?-->', '', content)
        
        def replace_link(match):
            full_match = match.group(0)
            is_image = full_match.startswith('!')
            text = match.group(2)
            path = match.group(3)
            
            # Skip if it's not a file link
            if path.startswith(('http://', 'https://', '#', '/')):
                return full_match
                
            # Get file type from extension
            ext = Path(path).suffix.lower()
            type_map = {
                '.pdf': 'PDF',
                '.doc': 'DOC',
                '.docx': 'DOC',
                '.jpg': 'IMAGE',
                '.jpeg': 'IMAGE',
                '.png': 'IMAGE',
                '.heic': 'IMAGE',
                '.xlsx': 'EXCEL',
                '.xls': 'EXCEL',
                '.csv': 'EXCEL',
                '.txt': 'TXT',
                '.json': 'JSON',
                '.html': 'DOC',
                '.md': 'DOC'
            }
            file_type = type_map.get(ext, 'OTHER')
            
            # Create reference marker
            filename = Path(path).stem
            ref = f"[ATTACH:{file_type}:{filename}]"
            
            # For images, preserve the ! prefix
            if is_image:
                ref = "!" + ref
            
            # Return the reference marker
            return ref
        
        # Update all links using the pattern
        link_pattern = r'(!?\[([^\]]*)\]\(([^)]+)\))'
        content = re.sub(link_pattern, replace_link, content)
        
        return content
        
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
            
            # Update links to use reference markers
            updated_content = self._update_links(content)
            
            # Write the updated content
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.processed = True
            metadata.output_files.add(output_file)
            
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process markdown file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg)
            metadata.processed = False
            return metadata 