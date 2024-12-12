"""Word document processing functionality."""

import asyncio
from pathlib import Path
import aiofiles
import structlog
from docx import Document
import mammoth
import shutil
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from bs4 import BeautifulSoup
import uuid

from src.core.exceptions import ProcessingError
from src.core.types import ProcessedAttachment

logger = structlog.get_logger(__name__)

class WordProcessor:
    """Handles Word document processing and conversion."""
    
    def __init__(self, temp_dir: Path) -> None:
        """Initialize Word processor.
        
        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir
        self.attachments_dir = temp_dir.parent / "attachments"
        self.attachments_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        self.word_embeddings: List[Dict[str, str]] = []
        
    async def process_document(self, docx_path: Path) -> ProcessedAttachment:
        """Process a Word document and return the processed result."""
        try:
            # Create target paths
            docx_name = docx_path.stem
            docx_target = self.attachments_dir / 'word' / f"{docx_name}_{uuid.uuid4().hex[:12]}.docx"
            html_target = docx_target.with_suffix('.html')
            
            # Create directories
            docx_target.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy DOCX file
            shutil.copy2(docx_path, docx_target)
            
            # Convert to HTML
            warnings = self._convert_docx_to_html(docx_target, html_target)
            
            # Log warnings if any
            if warnings:
                self.logger.warning("Word document processed with warnings",
                                  docx_target=str(docx_target),
                                  html_target=str(html_target),
                                  warnings=len(warnings))
            
            # Log success
            self.logger.info("Word file processed",
                           source=str(docx_path),
                           docx_target=str(docx_target),
                           html_target=str(html_target),
                           warnings=len(warnings))
            
            return ProcessedAttachment(
                source_path=docx_path,
                target_path=html_target,
                metadata={
                    "title": docx_name,
                    "warnings": len(warnings),
                    "has_images": bool(docx_target.stat().st_size > 0),
                    "size": docx_target.stat().st_size
                },
                is_valid=True,
                error=None
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process Word document {docx_path}",
                            component="word_processor",
                            error=str(e))
            raise ProcessingError(f"Failed to process Word document: {e}")

    def _convert_docx_to_html(self, docx_path: Path, html_path: Path) -> List[str]:
        """Convert DOCX file to HTML using mammoth."""
        warnings = []
        
        try:
            with open(docx_path, 'rb') as docx_file:
                # Configure mammoth style map
                style_map = """
                p[style-name='Heading 1'] => h1.word-heading-1:fresh
                p[style-name='Heading 2'] => h2.word-heading-2:fresh
                p[style-name='Heading 3'] => h3.word-heading-3:fresh
                p[style-name='List Paragraph'] => p.word-list-paragraph:fresh
                r[style-name='Strong'] => strong
                r[style-name='Emphasis'] => em
                table => table.word-table
                tr => tr
                td => td.word-table-cell
                th => th.word-table-cell
                ul => ul.word-list
                ol => ol.word-list
                li => li.word-list-item
                """
                
                # Convert DOCX to HTML
                result = mammoth.convert_to_html(
                    docx_file,
                    style_map=style_map,
                    convert_image=mammoth.images.data_uri
                )
                html = result.value
                warnings.extend(result.messages)
                
                # Clean up HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Add classes to elements
                for p in soup.find_all('p'):
                    if not p.get('class'):
                        p['class'] = 'word-paragraph'
                    
                for table in soup.find_all('table'):
                    if not table.get('class'):
                        table['class'] = 'word-table'
                    
                for ul in soup.find_all('ul'):
                    if not ul.get('class'):
                        ul['class'] = 'word-list'
                    
                for ol in soup.find_all('ol'):
                    if not ol.get('class'):
                        ol['class'] = 'word-list'
                    
                for h1 in soup.find_all('h1'):
                    if not h1.get('class'):
                        h1['class'] = 'word-heading-1'
                    
                for h2 in soup.find_all('h2'):
                    if not h2.get('class'):
                        h2['class'] = 'word-heading-2'
                    
                for h3 in soup.find_all('h3'):
                    if not h3.get('class'):
                        h3['class'] = 'word-heading-3'
                    
                # Remove empty elements
                for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'li']):
                    if not element.get_text(strip=True) and not element.find('img'):
                        element.decompose()
                
                # Write HTML to file
                with open(html_path, 'w', encoding='utf-8') as html_file:
                    html_file.write(str(soup))
                    
        except Exception as e:
            self.logger.error("Failed to convert DOCX to HTML",
                            component="word_processor",
                            error=str(e))
            raise ProcessingError(f"Failed to convert DOCX to HTML: {e}")
            
        return warnings

    def _save_image(self, image: Any) -> str:
        """Save an image from a Word document and return its path."""
        try:
            # Generate a unique filename for the image
            image_name = f"word_image_{uuid.uuid4().hex[:12]}.{image.content_type.split('/')[-1]}"
            image_path = self.attachments_dir / 'images' / image_name
            
            # Create images directory
            image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write image to file
            with open(image_path, 'wb') as f:
                f.write(image.content)
            
            # Return image path
            return str(image_path)
            
        except Exception as e:
            self.logger.error("Failed to save Word document image",
                            component="word_processor",
                            error=str(e))
            return ''