"""HTML handler for Nova pipeline."""

import logging
from pathlib import Path
from typing import Optional
import shutil
from bs4 import BeautifulSoup

from ..config.manager import ConfigManager
from ..models.document import DocumentMetadata
from .base import BaseHandler


class HTMLHandler(BaseHandler):
    """HTML handler for Nova pipeline."""
    
    name = "html"
    version = "0.1.0"
    file_types = ["html", "htm"]
    
    def __init__(self, config: ConfigManager) -> None:
        """Initialize HTML handler.
        
        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.logger = logging.getLogger("nova.handlers.html")
    
    def _write_markdown(self, output_path: Path, title: str, file_path: Path, content: str) -> bool:
        """Write markdown file with HTML content.
        
        Args:
            output_path: Path to write markdown file.
            title: Title for markdown file.
            file_path: Path to original file.
            content: Processed content.
            
        Returns:
            True if file was written, False if unchanged.
        """
        markdown_content = f"""# {title}

## Content

{content}
"""
        return self._safe_write_file(output_path, markdown_content)
    
    async def process_impl(
        self,
        file_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an HTML file.
        
        Args:
            file_path: Path to file.
            metadata: Document metadata.
                
        Returns:
            Document metadata, or None if file is ignored.
            
        Raises:
            ValueError: If file cannot be processed.
        """
        try:
            # Get output path from output manager
            output_path = self.output_manager.get_output_path_for_phase(
                file_path,
                "parse",
                ".parsed.md"
            )
            
            # Process content
            content = await self._process_content(file_path)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.processed = True
            
            # Write markdown using MarkdownWriter
            markdown_content = self.markdown_writer.write_document(
                title=metadata.title,
                content=content,
                metadata=metadata.metadata,
                file_path=file_path,
                output_path=output_path
            )
            
            # Write the file
            was_written = self._safe_write_file(output_path, markdown_content)
            
            metadata.unchanged = not was_written
            metadata.add_output_file(output_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process HTML file {file_path}: {str(e)}")
            metadata.add_error(self.name, str(e))
            return metadata
    
    def _convert_html_to_markdown(self, html: str) -> str:
        """Convert HTML to markdown.
        
        Args:
            html: HTML content.
            
        Returns:
            Markdown representation of HTML content.
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract text
            text = soup.get_text()
            
            # Clean up text
            lines = []
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    lines.append(line)
            
            # Join lines back together
            return "\n".join(lines)
            
        except Exception as e:
            return f"Error converting HTML to markdown: {str(e)}" 