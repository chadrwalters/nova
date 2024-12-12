"""Markdown processing and validation functionality."""

import base64
import hashlib
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, TypeAlias, Union
import mimetypes
import structlog
import aiofiles
from bs4 import BeautifulSoup
import markdown
import time
import shutil
import urllib.parse
from datetime import datetime

from src.core.exceptions import ValidationError, ProcessingError
from src.core.logging import get_logger
from src.processors.pdf_processor import PDFAttachmentHandler
from src.processors.word_processor import WordProcessor

logger = structlog.get_logger(__name__)

# Type aliases
MarkdownContent: TypeAlias = str
ValidationResult: TypeAlias = Dict[str, Union[bool, List[str], Dict[str, int]]]

class MarkdownProcessor:
    """Processes markdown content."""
    
    def __init__(self, temp_dir: Path, media_dir: Path, error_tolerance: bool = False) -> None:
        """Initialize markdown processor.
        
        Args:
            temp_dir: Directory for temporary files
            media_dir: Directory for media files
            error_tolerance: Whether to continue on non-critical errors
        """
        self.temp_dir = temp_dir
        self.media_dir = media_dir
        self.error_tolerance = error_tolerance
        self.logger = logger
        self.word_processor = WordProcessor(temp_dir)
        self.pdf_handler = PDFAttachmentHandler(temp_dir)
        
    async def convert_to_html(self, file_path: Path) -> str:
        """Convert markdown file to HTML.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Processed HTML content
        """
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                
            # Process embedded content
            content = await self._process_embedded_images(content, file_path)
            content = await self._process_word_attachments(content, file_path)
            content = await self._process_pdf_attachments(content, file_path)
            
            # Convert to HTML
            html = markdown.markdown(content, extensions=['extra', 'meta'])
            
            return html
            
        except Exception as e:
            self.logger.error("Markdown conversion failed",
                            file=str(file_path),
                            error=str(e))
            raise ProcessingError(f"Failed to convert markdown: {e}")
            
    async def _process_embedded_images(self, content: str, file_path: Path) -> str:
        """Process embedded images in markdown content."""
        try:
            # Find image references
            for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.(png|jpg|jpeg|gif))\)', content):
                link_text, image_path = match.groups()
                abs_path = (file_path.parent / urllib.parse.unquote(image_path)).resolve()
                
                if not abs_path.exists():
                    self.logger.warning("Image file not found", file=str(abs_path))
                    continue

                # Create a metadata dictionary for logging
                metadata = {
                    'source_file': str(file_path),
                    'operation': 'embedded_image_processing'
                }

                async with aiofiles.open(abs_path, 'rb') as f:
                    # Read only the header bytes needed for hash
                    hash_data = await f.read(8192)  # Read first 8KB for hash
                    
                    # Calculate hash without loading full content
                    file_hash = hashlib.md5(hash_data).hexdigest()
                    
                    # Update metadata with safe information
                    metadata.update({
                        'hash': file_hash,
                        'size': (await f.stat()).st_size
                    })
                    
                    self.logger.debug(
                        "Processing embedded image",
                        extra={'metadata': metadata}
                    )

                    # Process file in streaming chunks
                    output_path = self.media_dir / f"{file_hash}.png"
                    if not output_path.exists():
                        async with aiofiles.open(output_path, 'wb') as out_f:
                            # Reset file pointer to start
                            await f.seek(0)
                            while chunk := await f.read(8192):
                                await out_f.write(chunk)

                    self.logger.info(
                        "Processed embedded image",
                        extra={
                            'metadata': {
                                **metadata,
                                'output_path': str(output_path)
                            }
                        }
                    )

                    # Replace markdown link with new path
                    old_link = f"[{link_text}]({image_path})"
                    new_link = f"[{link_text}]({output_path})"
                    content = content.replace(old_link, new_link)
            
            return content
            
        except Exception as e:
            self.logger.error(
                "Failed to process embedded image",
                extra={
                    'file': str(file_path),
                    'error': str(e)
                }
            )
            raise
            
    async def _process_word_attachments(self, content: str, file_path: Path) -> str:
        """Process Word document attachments in markdown content."""
        try:
            # Find Word document references
            for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.docx?)\)', content):
                link_text, word_path = match.groups()
                abs_path = (file_path.parent / urllib.parse.unquote(word_path)).resolve()
                
                if abs_path.exists():
                    # Process Word file
                    processed = await self.word_processor.process_document(abs_path)
                    
                    if processed.target_path and processed.target_path.exists():
                        # Read the HTML content
                        async with aiofiles.open(processed.target_path, 'r', encoding='utf-8') as f:
                            html_content = await f.read()
                            
                        # Parse the HTML to extract just the body content
                        soup = BeautifulSoup(html_content, 'html.parser')
                        body_content = soup.find('body')
                        if body_content:
                            content_html = ''.join(str(tag) for tag in body_content.children)
                        else:
                            content_html = html_content
                        
                        # Create HTML structure with proper indentation
                        html = f'''<div class="word-document-content">
    <div class="word-document-header">
        <h2>{link_text}</h2>
        <div class="word-document-meta">
            <span>Last Modified: {datetime.fromtimestamp(abs_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}</span>
        </div>
    </div>
    <div class="word-document-body">
        {content_html}
    </div>
</div>'''
                        
                        # Replace markdown link with HTML
                        old_link = f"[{link_text}]({word_path})"
                        content = content.replace(old_link, html)
                        
                        self.logger.debug("Word document embedded",
                                       source=str(abs_path),
                                       target=str(processed.target_path))
                    else:
                        self.logger.warning("Word document processing failed",
                                          file=str(abs_path),
                                          error="HTML file not found")
                        continue
                else:
                    self.logger.warning("Word document not found",
                                      file=str(abs_path))
                    
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process Word attachments in {file_path}",
                            component="markdown_processor",
                            error=str(e))
            raise ProcessingError(f"Failed to process Word attachments: {e}")
            
    async def _find_pdf_attachments(self, content: str, file_path: Path) -> list[tuple[str, str, Path]]:
        """Find PDF attachments in markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to markdown file
            
        Returns:
            List of tuples containing (link_text, pdf_path, abs_path)
        """
        attachments = []
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.pdf)\)', content):
            link_text, pdf_path = match.groups()
            abs_path = (file_path.parent / urllib.parse.unquote(pdf_path)).resolve()
            attachments.append((link_text, pdf_path, abs_path))
        return attachments

    async def _process_pdf_attachments(self, content: str, file_path: Path) -> str:
        """Process PDF attachments in markdown content."""
        try:
            # Find PDF references
            attachments = await self._find_pdf_attachments(content, file_path)
            
            for link_text, pdf_path, abs_path in attachments:
                if abs_path.exists():
                    # Process PDF file
                    processed = await self.pdf_handler.process_pdf(abs_path)
                    
                    # Store the processed PDF path for later embedding
                    if not hasattr(self, 'pdf_attachments'):
                        self.pdf_attachments = []
                    self.pdf_attachments.append({
                        'path': processed.target_path,
                        'title': link_text
                    })
                    
                    # Replace markdown link with HTML comment placeholder
                    old_link = f"[{link_text}]({pdf_path})"
                    placeholder = f'<!-- PDF_EMBED_START:{processed.target_path}:{link_text} --><div class="pdf-placeholder">{link_text}</div><!-- PDF_EMBED_END:{processed.target_path} -->'
                    content = content.replace(old_link, placeholder)
                    
                    self.logger.info("PDF processed for embedding",
                                   source=str(abs_path),
                                   target=str(processed.target_path))
                else:
                    self.logger.warning("PDF file not found",
                                      file=str(abs_path))
                    
            return content
            
        except Exception as e:
            if self.error_tolerance:
                self.logger.warning("PDF processing failed",
                                  error=str(e))
                return content
            raise ProcessingError(f"Failed to process PDF attachments: {e}")

    async def _process_embedded_content(self, content: str, file_path: Path) -> str:
        """Process embedded content in markdown."""
        try:
            # Process Word documents in subdirectories
            for docx_file in file_path.parent.rglob('*.docx'):
                # Skip if not in a subdirectory of the markdown file
                if docx_file.parent == file_path.parent:
                    continue
                    
                docx_name = docx_file.stem
                content += f"\n\n[{docx_name}]({docx_file.relative_to(file_path.parent)})"
            
            # Process PDFs in subdirectories
            for pdf_file in file_path.parent.rglob('*.pdf'):
                # Skip if not in a subdirectory of the markdown file
                if pdf_file.parent == file_path.parent:
                    continue
                    
                pdf_name = pdf_file.stem
                html = await self._embed_pdf(pdf_file, pdf_name)
                content += f"\n\n{html}"
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process embedded content in {file_path}",
                            component="markdown_processor",
                            error=str(e))
            raise ProcessingError(f"Failed to process embedded content: {e}")

    async def process_markdown(self, file_path: Path) -> str:
        """Process a markdown file."""
        try:
            # Read markdown content
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            
            # First process embedded content from subdirectories
            content = await self._process_embedded_content(content, file_path)
            
            # Process attachments in order
            content = await self._process_word_attachments(content, file_path)
            content = await self._process_pdf_attachments(content, file_path)
            
            # Store the processed content for PDF generation
            self.processed_content = content
            
            # Convert markdown to HTML
            html = markdown.markdown(content, extensions=['extra'])
            
            return html
            
        except Exception as e:
            self.logger.error(f"Failed to process markdown file {file_path}",
                            component="markdown_processor",
                            error=str(e))
            raise ProcessingError(f"Failed to process markdown file: {e}")

    async def generate_final_pdf(self, html_content: str) -> bytes:
        """Generate final PDF with all embedded content.
        
        Args:
            html_content: HTML content to convert to PDF
            
        Returns:
            PDF content as bytes
            
        Raises:
            ProcessingError: If PDF generation fails
        """
        try:
            # Replace PDF placeholders with actual content
            if hasattr(self, 'pdf_attachments'):
                for attachment in self.pdf_attachments:
                    placeholder = f'[[PDF_EMBED:{attachment["path"]}:{attachment["title"]}]]'
                    # Read PDF content
                    async with aiofiles.open(attachment['path'], 'rb') as f:
                        pdf_content = await f.read()
                    # Convert to base64 for embedding
                    pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
                    # Replace placeholder with embedded PDF
                    html_content = html_content.replace(
                        placeholder,
                        f'<embed src="data:application/pdf;base64,{pdf_base64}" type="application/pdf" width="100%" height="600px">'
                    )
            
            # Use wkhtmltopdf to convert HTML to PDF
            # Note: Headers and footers are explicitly forbidden per pipeline rules
            options = {
                'enable-local-file-access': None,
                'quiet': None,
                'print-media-type': None,
                'no-outline': None,
                'margin-top': '0',
                'margin-right': '0',
                'margin-bottom': '0',
                'margin-left': '0',
                'encoding': 'UTF-8',
                'no-header-line': None,
                'no-footer-line': None,
                'disable-smart-shrinking': None
            }
            
            # Convert HTML to PDF using wkhtmltopdf
            import pdfkit
            pdf_bytes = pdfkit.from_string(html_content, False, options=options)
            
            return pdf_bytes
            
        except Exception as e:
            self.logger.error("Failed to generate final PDF",
                            error=str(e))
            raise ProcessingError(f"Failed to generate final PDF: {e}")
            
    async def convert_markdown_to_pdf(self, markdown_path: Path) -> bytes:
        """Convert markdown to PDF with all embedded content.
        
        Args:
            markdown_path: Path to markdown file
            
        Returns:
            PDF content as bytes
            
        Raises:
            ProcessingError: If conversion fails
        """
        # Process markdown to HTML
        html_content = await self.process_markdown(markdown_path)
        
        # Generate final PDF with embedded content
        pdf_content = await self.generate_final_pdf(html_content)
        
        return pdf_content
