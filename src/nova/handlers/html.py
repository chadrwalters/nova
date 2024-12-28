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
    
    async def process_impl(
        self,
        file_path: Path,
        output_dir: Path,
        metadata: DocumentMetadata,
    ) -> Optional[DocumentMetadata]:
        """Process an HTML file.
        
        Args:
            file_path: Path to HTML file.
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
            
            # Convert HTML to markdown
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                html = f.read()
            markdown = self._convert_html_to_markdown(html)
            
            # Write markdown file with converted content and reference to original
            self._write_markdown(markdown_path, file_path.stem, file_path, markdown)
            
            # Update metadata
            metadata.title = file_path.stem
            metadata.metadata['original_path'] = str(file_path)
            metadata.metadata['markdown'] = markdown
            metadata.processed = True
            metadata.add_output_file(markdown_path)
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Failed to process HTML file {file_path}: {str(e)}")
            return None 
    
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