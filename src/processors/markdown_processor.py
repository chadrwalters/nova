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
from src.processors.powerpoint_processor import PowerPointProcessor

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
        self.powerpoint_processor = PowerPointProcessor(temp_dir)
        
    async def convert_to_html(self, file_path: Path) -> str:
        """Convert markdown file to HTML."""
        try:
            # Add CSS for document boundaries and embedded content
            css = """
            <style>
            .markdown-document {
                border: 2px solid #2196F3;
                border-radius: 4px;
                padding: 20px;
                margin: 20px 0;
                background: #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .markdown-content {
                position: relative;
                padding: 15px;
                background: #FAFAFA;
                border-left: 4px solid #2196F3;
                margin: 15px 0;
                border-radius: 4px;
            }
            .markdown-content:before {
                content: "Markdown";
                position: absolute;
                top: -10px;
                left: 10px;
                background: #2196F3;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 12px;
            }
            .word-document-wrapper {
                position: relative;
                margin: 15px 0;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: white;
            }
            .word-document-wrapper:before {
                content: "Embedded Word Document";
                position: absolute;
                top: -10px;
                left: 10px;
                background: #FF9800;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 12px;
            }
            .attachment-container {
                display: flex;
                align-items: center;
                padding: 12px 15px;
                margin: 10px 0;
                background: #F5F5F5;
                border-left: 4px solid #FF9800;
                border-radius: 4px;
            }
            .attachment-icon {
                font-size: 24px;
                margin-right: 12px;
            }
            .attachment-title {
                font-weight: 500;
                color: #1976D2;
                text-decoration: none;
                margin-right: 12px;
            }
            .attachment-meta {
                color: #666;
                font-size: 14px;
                margin-left: auto;
            }
            .pptx-container {
                position: relative;
                margin: 15px 0;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: white;
            }
            .pptx-container:before {
                content: "PowerPoint Presentation";
                position: absolute;
                top: -10px;
                left: 10px;
                background: #4CAF50;
                color: white;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 12px;
            }
            .slides-wrapper {
                padding: 20px;
            }
            .slide {
                border: 1px solid #ddd;
                margin: 10px 0;
                padding: 15px;
                background: #fff;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .shape {
                margin: 10px 0;
            }
            .text-content {
                font-size: 16px;
                line-height: 1.5;
            }
            .image-content img {
                max-width: 100%;
                height: auto;
            }
            </style>
            """

            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                
            # Process embedded content
            content = await self._process_embedded_images(content, file_path)
            content = await self._process_word_attachments(content, file_path)
            content = await self._process_powerpoint_attachments(content, file_path)
            content = await self._process_pdf_attachments(content, file_path)
            
            # Convert to HTML with preserved HTML blocks
            html = markdown.markdown(content, extensions=['extra', 'meta'], output_format='html5')
            
            # Wrap initial markdown content
            html = f'<div class="markdown-content">{html}</div>'
            
            # Wrap everything in document container
            wrapped_html = f"""
            {css}
            <div class="markdown-document">
                <div class="document-title">{file_path.stem}</div>
                {html}
            </div>
            """
            
            return wrapped_html
            
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
                link_text, image_path, _ = match.groups()
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
                    # Process Word file to get HTML content
                    processed = await self.word_processor.process_document(abs_path)
                    
                    if processed.target_path and processed.target_path.exists():
                        # Read the HTML content
                        async with aiofiles.open(processed.target_path, 'r', encoding='utf-8') as f:
                            word_content = await f.read()
                            
                        # Parse the HTML to extract just the body content
                        soup = BeautifulSoup(word_content, 'html.parser')
                        body_content = soup.find('body')
                        if body_content:
                            content_html = ''.join(str(tag) for tag in body_content.children)
                        else:
                            content_html = word_content

                        # Close the current markdown section before embedded content
                        attachment_html = '</div>\n'  # Close markdown-content div
                        
                        # Add the Word document
                        attachment_html += f"""
<div class="word-document-wrapper">
    <div class="attachment-container">
        <span class="attachment-icon">📄</span>
        <span class="attachment-title">{link_text}</span>
        <span class="attachment-meta">Word Document • Modified {datetime.fromtimestamp(abs_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}</span>
    </div>
    <div class="word-content">
        {content_html}
    </div>
</div>
"""
                        # Start a new markdown section after embedded content
                        attachment_html += '\n<div class="markdown-content">'
                        
                        # Replace markdown link with HTML content
                        old_link = f"[{link_text}]({word_path})"
                        content = content.replace(old_link, attachment_html)

            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process Word attachments in {file_path}",
                            error=str(e))
            if self.error_tolerance:
                return content
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
            for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.pdf)\)', content):
                link_text, pdf_path = match.groups()
                
                # Check if it's a URL
                if pdf_path.startswith(('http://', 'https://')):
                    # For URLs, just preserve the link
                    self.logger.info("Skipping external PDF URL", url=pdf_path)
                    continue
                    
                abs_path = (file_path.parent / urllib.parse.unquote(pdf_path)).resolve()
                
                if abs_path.exists():
                    # Create HTML-style attachment block that will be preserved
                    modified_time = datetime.fromtimestamp(abs_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')
                    attachment_html = f"""
<div class="attachment-container">
    <span class="attachment-icon">📑</span>
    <a href="{pdf_path}" class="attachment-title">{link_text}</a>
    <span class="attachment-meta">PDF Document • Modified {modified_time}</span>
</div>
"""
                    # Replace markdown link with HTML
                    old_link = f"[{link_text}]({pdf_path})"
                    content = content.replace(old_link, attachment_html)
                else:
                    self.logger.warning("PDF file not found", file=str(abs_path))

            return content
            
        except Exception as e:
            self.logger.error("PDF processing failed", error=str(e))
            if self.error_tolerance:
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
            
            # Process PowerPoint files in subdirectories
            for pptx_file in file_path.parent.rglob('*.pptx'):
                # Skip if not in a subdirectory of the markdown file
                if pptx_file.parent == file_path.parent:
                    continue
                    
                pptx_name = pptx_file.stem
                content += f"\n\n[{pptx_name}]({pptx_file.relative_to(file_path.parent)})"
            
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
            content = await self._process_powerpoint_attachments(content, file_path)
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
        """Generate final PDF with all embedded content."""
        try:
            self.logger.info("Starting PDF generation", content_length=len(html_content))
            
            # Add debug logging for PowerPoint content
            pptx_matches = re.findall(r'<div class="pptx-container".*?</div></div>', html_content, re.DOTALL)
            self.logger.info("Found PowerPoint content", count=len(pptx_matches))
            
            # Use wkhtmltopdf to convert HTML to PDF
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
                'disable-smart-shrinking': None,
                # Add these options to better handle PowerPoint content
                'enable-javascript': None,
                'javascript-delay': '1000',  # Wait for any JavaScript to complete
                'load-error-handling': 'ignore'
            }
            
            import pdfkit
            pdf_bytes = pdfkit.from_string(html_content, False, options=options)
            
            self.logger.info("PDF generation complete", pdf_size=len(pdf_bytes))
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

    async def _process_powerpoint_attachments(self, content: str, file_path: Path) -> str:
        """Process PowerPoint attachments in markdown content."""
        try:
            # Find PowerPoint references
            for match in re.finditer(r'\[([^\]]+)\]\(([^)]+\.pptx?)\)', content):
                link_text, pptx_path = match.groups()
                abs_path = (file_path.parent / urllib.parse.unquote(pptx_path)).resolve()
                
                if abs_path.exists():
                    # Process PowerPoint file
                    processed = await self.powerpoint_processor.process_presentation(abs_path)
                    
                    if processed.target_path and processed.target_path.exists():
                        # Read the HTML content
                        async with aiofiles.open(processed.target_path, 'r', encoding='utf-8') as f:
                            pptx_content = await f.read()

                        # Close the current markdown section before embedded content
                        attachment_html = '</div>\n'  # Close markdown-content div
                        
                        # Add the PowerPoint content
                        attachment_html += f"""
<div class="pptx-container">
    <div class="attachment-container">
        <span class="attachment-icon">📊</span>
        <span class="attachment-title">{link_text}</span>
        <span class="attachment-meta">PowerPoint • {processed.slide_count} slides • Modified {datetime.fromtimestamp(abs_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}</span>
    </div>
    {pptx_content}
</div>
"""
                        # Start a new markdown section after embedded content
                        attachment_html += '\n<div class="markdown-content">'
                        
                        # Replace markdown link with HTML content
                        old_link = f"[{link_text}]({pptx_path})"
                        content = content.replace(old_link, attachment_html)

            return content
            
        except Exception as e:
            self.logger.error(f"Failed to process PowerPoint attachments in {file_path}",
                            error=str(e))
            if self.error_tolerance:
                return content
            raise ProcessingError(f"Failed to process PowerPoint attachments: {e}")
