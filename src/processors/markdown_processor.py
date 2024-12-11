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

from src.core.exceptions import ValidationError, ProcessingError
from src.core.logging import get_logger
from src.processors.pdf_processor import PDFAttachmentHandler

logger = structlog.get_logger(__name__)

# Type aliases
MarkdownContent: TypeAlias = str
ValidationResult: TypeAlias = Dict[str, Union[bool, List[str], Dict[str, int]]]

class MarkdownValidator:
    """Validates markdown content before processing."""
    
    def __init__(self) -> None:
        """Initialize the validator."""
        self.logger = logger
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_line_length = 1000
        self.max_embedded_size = 5 * 1024 * 1024  # 5MB for embedded content
        
    def validate_file(self, file_path: Path) -> ValidationResult:
        """Validate a markdown file.
        
        Args:
            file_path: Path to the markdown file
            
        Returns:
            ValidationResult containing validation status and issues
            
        Raises:
            ValidationError: If validation fails critically
        """
        try:
            result = {
                "valid": True,
                "issues": [],
                "stats": {
                    "size": 0,
                    "lines": 0,
                    "embedded_items": 0
                }
            }
            
            # Check file existence and permissions
            if not file_path.exists():
                raise ValidationError(f"File does not exist: {file_path}")
            if not file_path.is_file():
                raise ValidationError(f"Not a file: {file_path}")
            if not os.access(file_path, os.R_OK):
                raise ValidationError(f"File not readable: {file_path}")
                
            # Check file size
            size = file_path.stat().st_size
            result["stats"]["size"] = size
            if size > self.max_file_size:
                result["valid"] = False
                result["issues"].append(f"File too large: {size} bytes (max {self.max_file_size})")
                
            # Read and validate content
            content = file_path.read_text(encoding='utf-8')
            
            # Validate line length and count
            lines = content.splitlines()
            result["stats"]["lines"] = len(lines)
            for i, line in enumerate(lines, 1):
                if len(line) > self.max_line_length:
                    result["valid"] = False
                    result["issues"].append(
                        f"Line {i} too long: {len(line)} chars (max {self.max_line_length})"
                    )
                    
            # Validate markdown syntax
            try:
                html = markdown(content)
                soup = BeautifulSoup(html, 'html.parser')
            except Exception as err:
                result["valid"] = False
                result["issues"].append(f"Invalid markdown syntax: {err}")
                
            # Check embedded content
            embedded = self._find_embedded_content(soup)
            result["stats"]["embedded_items"] = len(embedded)
            for item in embedded:
                if len(item) > self.max_embedded_size:
                    result["valid"] = False
                    result["issues"].append(
                        f"Embedded content too large: {len(item)} bytes (max {self.max_embedded_size})"
                    )
                    
            # Log validation result
            if result["valid"]:
                self.logger.info(
                    "File validation successful",
                    path=str(file_path),
                    stats=result["stats"]
                )
            else:
                self.logger.warning(
                    "File validation issues found",
                    path=str(file_path),
                    issues=result["issues"],
                    stats=result["stats"]
                )
                
            return result
            
        except Exception as err:
            self.logger.error("Validation failed", exc_info=err)
            raise ValidationError(f"Failed to validate {file_path}: {err}") from err
            
    def _find_embedded_content(self, soup: BeautifulSoup) -> List[str]:
        """Find all embedded content (base64, etc.) in HTML.
        
        Args:
            soup: BeautifulSoup object of HTML content
            
        Returns:
            List of embedded content strings
        """
        embedded = []
        
        # Find base64 images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.startswith('data:'):
                try:
                    content = src.split(',')[1]
                    embedded.append(content)
                except IndexError:
                    continue
                    
        return embedded

class MarkdownProcessor:
    """Processor for markdown files with validation and error handling."""

    def __init__(
        self, temp_dir: Path, media_dir: Path, error_tolerance: bool = False
    ) -> None:
        """Initialize the markdown processor.

        Args:
            temp_dir: Directory for temporary files
            media_dir: Directory for media files
            error_tolerance: Whether to continue on non-critical errors
        """
        self.temp_dir = temp_dir
        self.media_dir = media_dir
        self.error_tolerance = error_tolerance
        self.logger = logger
        self.validator = MarkdownValidator()
        
        # Use the parent of temp_dir as the processing directory
        processing_dir = temp_dir.parent
        self.pdf_handler = PDFAttachmentHandler(processing_dir)
        
        # Initialize markdown converter
        self.md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'tables',
                'toc',
                'footnotes'
            ]
        )
        
        # Create required directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: Path) -> MarkdownContent:
        """Process a markdown file with validation.

        Args:
            file_path: Path to the markdown file

        Returns:
            Processed markdown content

        Raises:
            ProcessingError: If processing fails
            ValidationError: If validation fails critically
        """
        try:
            # Validate file first
            validation = self.validator.validate_file(file_path)
            if not validation["valid"] and not self.error_tolerance:
                raise ValidationError(
                    f"Validation failed for {file_path}: {validation['issues']}"
                )
            
            # Read content
            self.logger.info(f"Reading content from: {file_path}")
            content = file_path.read_text(encoding='utf-8')
            self.logger.info(
                f"Successfully read {len(content)} characters from {file_path}"
            )
            
            # Process content
            self.logger.info(f"Processing content from {file_path}")
            processed_content = self._process_content(content)
            self.logger.info(
                f"Successfully processed {file_path}, output length: {len(processed_content)}"
            )
            
            return processed_content

        except Exception as err:
            self.logger.error("Processing failed", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(f"Failed to process {file_path}: {err}") from err
            return ""

    def _process_content(self, content: str) -> str:
        """Process markdown content.
        
        Args:
            content: Raw markdown content
            
        Returns:
            Processed HTML content
            
        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Convert markdown to HTML
            html = markdown(
                content,
                extensions=[
                    'markdown.extensions.fenced_code',
                    'markdown.extensions.tables',
                    'markdown.extensions.toc',
                    'markdown.extensions.footnotes'
                ]
            )
            
            # Parse with BeautifulSoup for additional processing
            soup = BeautifulSoup(html, 'html.parser')
            
            # Process images
            for img in soup.find_all('img'):
                src = img.get('src', '')
                if src.startswith('data:'):
                    # Handle base64 images
                    try:
                        content_type = src.split(';')[0].split(':')[1]
                        content = src.split(',')[1]
                        ext = content_type.split('/')[-1]
                        
                        # Generate unique filename
                        hash_value = hashlib.sha256(content.encode()).hexdigest()[:12]
                        filename = f"img_{hash_value}.{ext}"
                        
                        # Save to media directory
                        img_path = self.media_dir / filename
                        img_path.write_bytes(base64.b64decode(content))
                        
                        # Update src
                        img['src'] = f"../media/{filename}"
                        
                    except Exception as err:
                        self.logger.warning(f"Failed to process embedded image: {err}")
                        if not self.error_tolerance:
                            raise
                            
            return str(soup)
            
        except Exception as err:
            raise ProcessingError(f"Failed to process markdown content: {err}") from err

    async def _find_pdf_attachments(self, content: str, base_path: Path) -> dict[str, Path]:
        """Find and process PDF attachments in markdown content.
        
        Args:
            content: Markdown content
            base_path: Base path for resolving relative paths
            
        Returns:
            Dictionary mapping original paths to processed paths
        """
        pdf_map = {}
        
        # Log start of PDF attachment search
        self.logger.info("Searching for PDF attachments", file=str(base_path))
        
        try:
            # Find PDF links in markdown content
            pdf_pattern = r'\[([^\]]+)\]\(([^)]+\.pdf(?:/[^)]+\.pdf)?)\)'
            matches = re.finditer(pdf_pattern, content, re.IGNORECASE)
            
            for match in matches:
                link_text, pdf_path = match.groups()
                
                # URL decode the path
                pdf_path = urllib.parse.unquote(pdf_path)
                
                # Handle PDF in directory case
                if '.pdf/' in pdf_path:
                    dir_path, file_name = pdf_path.split('.pdf/', 1)
                    dir_path = dir_path + '.pdf'
                    pdf_file = base_path.parent / dir_path / file_name
                else:
                    pdf_file = Path(pdf_path)
                    if not pdf_file.is_absolute():
                        pdf_file = base_path.parent / pdf_file
                
                self.logger.info("Found PDF reference", 
                               link_text=link_text,
                               pdf_path=str(pdf_file))
                
                # Process PDF if it exists
                if pdf_file.exists():
                    if pdf_file.is_dir():
                        # If it's a directory ending in .pdf, look for the PDF file inside
                        actual_pdf = pdf_file / pdf_file.name
                        if actual_pdf.exists() and actual_pdf.is_file():
                            self.logger.info("Found PDF in directory", 
                                           dir=str(pdf_file),
                                           file=str(actual_pdf))
                            pdf_file = actual_pdf
                    
                    if pdf_file.is_file():
                        self.logger.info("Processing PDF attachment", file=str(pdf_file))
                        processed = self.pdf_handler.process_pdf(pdf_file)
                        pdf_map[pdf_path] = processed.target_path
                        self.logger.info("PDF processed successfully",
                                       source=str(pdf_file),
                                       target=str(processed.target_path),
                                       size=processed.size)
                    else:
                        self.logger.warning("PDF file not found or invalid", file=str(pdf_file))
                else:
                    self.logger.warning("PDF file not found", file=str(pdf_file))
            
            # Also check for PDF files in the same directory
            for file in base_path.parent.glob('**/*.pdf'):
                if file.is_file():
                    # Check if this is a PDF file in a directory with the same name
                    if file.parent.name.endswith('.pdf'):
                        parent_pdf = file.parent
                        if parent_pdf.name == file.name:
                            # This is a PDF file inside a directory with the same name
                            self.logger.info("Found PDF in directory with same name", file=str(file))
                            processed = self.pdf_handler.process_pdf(file)
                            relative_path = f"{parent_pdf.relative_to(base_path.parent)}/{file.name}"
                            pdf_map[str(relative_path)] = processed.target_path
                            self.logger.info("PDF from directory processed",
                                           source=str(file),
                                           target=str(processed.target_path),
                                           size=processed.size)
                    elif file.name not in [Path(p).name for p in pdf_map.keys()]:
                        # This is a standalone PDF file
                        self.logger.info("Found additional PDF file", file=str(file))
                        processed = self.pdf_handler.process_pdf(file)
                        relative_path = file.relative_to(base_path.parent)
                        pdf_map[str(relative_path)] = processed.target_path
                        self.logger.info("Additional PDF processed",
                                       source=str(file),
                                       target=str(processed.target_path),
                                       size=processed.size)
            
            self.logger.info("PDF attachment search complete",
                           found=len(pdf_map),
                           file=str(base_path))
            
            return pdf_map
            
        except Exception as e:
            self.logger.error("Failed to process PDF attachments",
                            error=str(e),
                            file=str(base_path))
            if not self.error_tolerance:
                raise ProcessingError(f"Failed to process PDF attachments: {e}")
            return pdf_map

    async def convert_to_html(self, markdown_file: Path) -> str:
        """Convert markdown to HTML and process embedded content."""
        try:
            async with aiofiles.open(markdown_file, 'r', encoding='utf-8') as f:
                content = await f.read()

            # Find and process PDF attachments
            pdf_map = await self._find_pdf_attachments(content, markdown_file)
            
            # Update PDF references
            if pdf_map:
                content = self.pdf_handler.update_pdf_references(content, pdf_map)

            # Convert to HTML
            html = self.md.convert(content)
            
            # Process the HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Process images and save them to media directory
            await self._process_images(soup)
            
            # Reset markdown converter for next use
            self.md.reset()
            
            return str(soup)
            
        except Exception as e:
            self.logger.error(
                "Markdown conversion failed",
                file=str(markdown_file),
                error=str(e)
            )
            raise ProcessingError(f"Failed to convert markdown: {e}")

    async def _process_images(self, soup: BeautifulSoup) -> None:
        """Process and save images from HTML content."""
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if not src:
                continue

            if src.startswith('data:'):
                try:
                    # Parse the data URI
                    header, data = src.split(',', 1)
                    mime_type = header.split(';')[0].split(':')[1]
                    
                    # Determine file extension
                    extension = mimetypes.guess_extension(mime_type) or '.png'
                    
                    # Generate unique filename
                    hash_value = hashlib.sha256(data.encode()).hexdigest()[:12]
                    filename = f"img_{hash_value}{extension}"
                    
                    # Save image to media directory
                    image_path = self.media_dir / filename
                    image_data = base64.b64decode(data)
                    
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(image_data)
                    
                    # Update image source to point to saved file
                    img['src'] = f"../media/{filename}"
                    
                    self.logger.info(
                        "Processed embedded image",
                        filename=filename,
                        size=len(image_data)
                    )
                    
                except Exception as e:
                    self.logger.error(
                        "Failed to process embedded image",
                        error=str(e)
                    )
                    if not self.error_tolerance:
                        raise ProcessingError(f"Failed to process embedded image: {e}")

    def _process_file_with_retry(self, file_path: Path, retries: int = 3) -> str:
        """Process a markdown file with retries.
        
        Args:
            file_path: Path to markdown file
            retries: Number of retries
            
        Returns:
            Processed markdown content
        """
        for attempt in range(retries):
            try:
                # Read markdown content
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Process embedded images
                content = self._process_embedded_images(content, file_path)
                
                # Process PDF attachments
                content = self._process_pdf_attachments(content, file_path)
                
                # Add metadata
                content = self._add_metadata(content, file_path)
                
                return content
                
            except Exception as e:
                if attempt == retries - 1:
                    raise ProcessingError(f"Failed to process {file_path}: {e}")
                self.logger.warning(f"Retry {attempt + 1} for {file_path}: {e}")
                time.sleep(1)
    
    def _process_pdf_attachments(self, content: str, file_path: Path) -> str:
        """Process PDF attachments in markdown content.
        
        Args:
            content: Markdown content
            file_path: Path to markdown file
            
        Returns:
            Processed markdown content
        """
        # Find all PDF links
        pdf_pattern = r'\[([^\]]+)\]\(([^)]+\.pdf)\)'
        matches = re.finditer(pdf_pattern, content)
        
        for match in matches:
            link_text = match.group(1)
            pdf_path = match.group(2)
            
            self.logger.info("Found PDF reference",
                           link_text=link_text,
                           pdf_path=pdf_path)
            
            # Convert relative path to absolute
            if pdf_path.startswith('..'):
                abs_path = file_path.parent / pdf_path.lstrip('../')
            else:
                abs_path = file_path.parent / pdf_path
            
            if abs_path.exists():
                # Copy PDF to attachments directory
                pdf_name = abs_path.name
                pdf_hash = hashlib.sha256(str(abs_path).encode()).hexdigest()[:12]
                pdf_name_with_hash = f"{pdf_name.rsplit('.', 1)[0]}_{pdf_hash}.pdf"
                
                target_path = self.temp_dir / "attachments/pdf" / pdf_name_with_hash
                if not target_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(abs_path, target_path)
                    self.logger.info("PDF file copied to processing directory",
                                   size=target_path.stat().st_size,
                                   source=str(abs_path),
                                   target=str(target_path))
                
                # Update link in content
                old_link = f"[{link_text}]({pdf_path})"
                new_link = f'<a href="../attachments/pdf/{pdf_name_with_hash}" class="pdf-attachment" target="_blank">{link_text}</a>'
                content = content.replace(old_link, new_link)
                
                self.logger.info("Additional PDF processed",
                               size=target_path.stat().st_size,
                               source=str(abs_path),
                               target=str(target_path))
            else:
                self.logger.warning("PDF file not found", file=str(abs_path))
        
        return content
