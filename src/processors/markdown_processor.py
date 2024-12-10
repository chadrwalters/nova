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

from src.core.exceptions import ValidationError, ProcessingError
from src.core.logging import get_logger

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

    async def convert_to_html(self, markdown_file: Path) -> str:
        """Convert markdown to HTML and process embedded content."""
        try:
            async with aiofiles.open(markdown_file, 'r', encoding='utf-8') as f:
                content = await f.read()

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
