"""HTML handler for Nova pipeline."""

import logging
from pathlib import Path
from typing import Optional
import shutil
from bs4 import BeautifulSoup
import os

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
    
    async def _process_content(self, file_path: Path) -> str:
        """Process HTML content.
        
        Args:
            file_path: Path to HTML file.
            
        Returns:
            Processed content as markdown.
        """
        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html = f.read()
                
            # Convert to markdown
            return self._convert_html_to_markdown(html)
            
        except Exception as e:
            raise ValueError(f"Failed to process HTML content: {str(e)}")
    
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
        
    async def process_file_impl(
        self,
        file_path: Path,
        output_path: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an HTML file.
        
        Args:
            file_path: Path to HTML file.
            output_path: Path to write output.
            metadata: Document metadata.
            
        Returns:
            Document metadata.
        """
        try:
            # Read HTML file
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title = soup.title.string if soup.title else file_path.stem
            
            # Extract text content
            text = soup.get_text(separator='\n\n')
            
            # Format content
            content = f"HTML content from {file_path.stem}\n\n{text}"
            
            # Update metadata
            metadata.title = title
            metadata.processed = True
            metadata.metadata['html'] = html_content
            
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
            return metadata
            
        except Exception as e:
            error_msg = f"Failed to process HTML file {file_path}: {str(e)}"
            self.logger.error(error_msg)
            metadata.add_error(self.name, error_msg)
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