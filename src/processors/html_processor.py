"""HTML processing and PDF generation."""

import asyncio
from pathlib import Path
import aiofiles
import pdfkit
import jinja2
import structlog
from bs4 import BeautifulSoup
import re
import textwrap
import shutil
from datetime import datetime
from PyPDF2 import PdfMerger, PdfReader, PdfWriter
import urllib.parse
import pikepdf
import subprocess
import os
from typing import Dict, List, Optional
import fitz  # PyMuPDF

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)

class HTMLProcessor:
    """Handles HTML processing and PDF generation."""

    def __init__(self, temp_dir: Path, wkhtmltopdf_path: str = '/usr/local/bin/wkhtmltopdf') -> None:
        """Initialize HTML processor.
        
        Args:
            temp_dir: Directory for temporary files
            wkhtmltopdf_path: Path to wkhtmltopdf executable
        """
        self.temp_dir = temp_dir
        self.wkhtmltopdf_path = wkhtmltopdf_path
        self.logger = logger
        
        # Configure PDF generation options
        self.pdf_options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'enable-local-file-access': None
        }

    def _wrap_html_content(self, html_content: str) -> str:
        """Wrap HTML content in proper structure with meta tags."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Nova Document</title>
</head>
<body>
{html_content}
</body>
</html>"""

    async def _convert_pdf_to_images(self, pdf_path: Path) -> List[Path]:
        """Convert PDF pages to images."""
        try:
            # Open the PDF
            pdf_doc = fitz.open(str(pdf_path))
            
            # Create a directory for the images
            images_dir = self.temp_dir / "pdf_images"
            images_dir.mkdir(exist_ok=True)
            
            # Convert each page to an image
            image_paths = []
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Get the page as an image with high resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Save the image
                image_path = images_dir / f"page_{page_num}.png"
                pix.save(str(image_path))
                image_paths.append(image_path)
                
                self.logger.info("Converted PDF page to image",
                               page=page_num,
                               size=image_path.stat().st_size)
            
            return image_paths
            
        except Exception as e:
            self.logger.error("Failed to convert PDF to images", error=str(e))
            raise ProcessingError(f"Failed to convert PDF to images: {e}")

    async def _embed_pdf_as_images(self, input_html: str, pdf_path: Path, marker_id: str) -> str:
        """Embed a PDF as a series of images in the HTML."""
        try:
            # Convert PDF to images
            image_paths = await self._convert_pdf_to_images(pdf_path)
            
            # Create HTML for the images
            images_html = []
            for image_path in image_paths:
                # Copy image to the media directory
                media_dir = self.temp_dir / "media"
                media_dir.mkdir(exist_ok=True)
                
                image_name = f"pdf_page_{image_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                target_path = media_dir / image_name
                shutil.copy2(image_path, target_path)
                
                # Add image HTML
                images_html.append(f'<img src="{target_path}" class="pdf-page" style="width: 100%; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">')
            
            # Replace marker with images
            marker = f"<<<{marker_id}>>>"
            return input_html.replace(marker, "\n".join(images_html))
            
        except Exception as e:
            self.logger.error("Failed to embed PDF as images", error=str(e))
            raise ProcessingError(f"Failed to embed PDF as images: {e}")

    async def generate_pdf(self, html_content: str, output_file: Path, css_file: Path) -> None:
        """Generate PDF from HTML content."""
        self.logger.info("Starting PDF generation", 
                        component="html_processor",
                        css_file=str(css_file),
                        wkhtmltopdf_path=str(self.wkhtmltopdf_path))
        
        # Create a local temp directory for initial output
        local_temp = Path("/tmp/nova_output")
        local_temp.mkdir(parents=True, exist_ok=True)
        local_output = local_temp / "temp_output.pdf"

        try:
            # Write HTML to temp file
            temp_html = self.temp_dir / "temp_consolidated.html"
            async with aiofiles.open(temp_html, 'w', encoding='utf-8') as f:
                await f.write(html_content)

            # Configure PDF options
            options = {
                'page-size': 'Letter',
                'margin-top': '20mm',
                'margin-right': '20mm',
                'margin-bottom': '20mm',
                'margin-left': '20mm',
                'encoding': 'UTF-8',
                'no-outline': None,
                'enable-local-file-access': None,
                'quiet': None
            }

            # Generate PDF to local temp first
            pdfkit.from_file(str(temp_html), str(local_output), options=options, css=str(css_file))

            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy to final destination with proper permissions
            import shutil
            shutil.copy2(local_output, output_file)
            output_file.chmod(0o644)  # Set standard read permissions

            self.logger.info("PDF generation complete",
                           component="html_processor",
                           final_size=output_file.stat().st_size,
                           output=str(output_file))

        except Exception as e:
            self.logger.error("PDF generation failed",
                            component="html_processor",
                            error=str(e))
            raise ProcessingError(f"PDF generation failed: {e}")
        finally:
            # Cleanup temp files
            if local_output.exists():
                local_output.unlink()
            if local_temp.exists():
                local_temp.rmdir()

    def clean_html(self, html_content: str) -> str:
        """Clean and format HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Track PDF embeddings
        self.pdf_embeddings = []
        
        # Fix links and handle PDF embeddings
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href.endswith('.pdf'):
                # URL decode the path
                href = urllib.parse.unquote(href)
                
                # Try multiple possible locations for the PDF file
                possible_paths = [
                    self.temp_dir / href.lstrip('../'),  # Direct path
                    self.temp_dir.parent / href.lstrip('../'),  # Parent directory
                    self.temp_dir.parent / "attachments" / "pdf" / Path(href).name,  # Attachments directory
                    self.temp_dir / "attachments" / "pdf" / Path(href).name,  # Temp attachments
                ]
                
                # Also try with hash suffix
                base_name = Path(href).stem
                hash_files = list((self.temp_dir.parent / "attachments" / "pdf").glob(f"{base_name}_*.pdf"))
                if hash_files:
                    possible_paths.append(hash_files[0])
                
                # Also try looking for the file in a directory with the same name
                if '/' in href:
                    dir_path, file_name = href.rsplit('/', 1)
                    if dir_path.endswith('.pdf'):
                        possible_paths.extend([
                            self.temp_dir.parent / dir_path / file_name,  # Full path with directory
                            self.temp_dir / dir_path / file_name,  # Temp path with directory
                            self.temp_dir.parent / "attachments" / "pdf" / file_name,  # Just the file in attachments
                            self.temp_dir / "attachments" / "pdf" / file_name  # Just the file in temp attachments
                        ])
                        
                        # Also try with hash suffix for the file name
                        base_name = Path(file_name).stem
                        hash_files = list((self.temp_dir.parent / "attachments" / "pdf").glob(f"{base_name}_*.pdf"))
                        if hash_files:
                            possible_paths.append(hash_files[0])
                
                pdf_path = None
                for path in possible_paths:
                    if path.exists():
                        pdf_path = path
                        break
                
                if pdf_path:
                    # Generate unique marker ID
                    marker_id = f"PDF_EMBED_{len(self.pdf_embeddings):04d}"
                    self.pdf_embeddings.append({
                        'marker_id': marker_id,
                        'pdf_path': str(pdf_path.absolute()),
                        'title': link.string or Path(href).stem
                    })
                    
                    # Replace link with marker page
                    marker_div = soup.new_tag('div')
                    marker_div['class'] = ['pdf-embed-marker']
                    marker_div['style'] = 'page-break-before: always; page-break-after: always;'
                    marker_div['data-marker-id'] = marker_id
                    
                    # Add visible header for marker page
                    header = soup.new_tag('h2')
                    header.string = f"Embedded PDF: {link.string or Path(href).stem}"
                    marker_div.append(header)
                    
                    # Add machine-readable marker
                    marker_text = soup.new_tag('div')
                    marker_text['style'] = 'color: white; font-size: 1px;'
                    marker_text.string = f"<<<{marker_id}>>>"
                    marker_div.append(marker_text)
                    
                    link.replace_with(marker_div)
                    
                    self.logger.info("Added PDF embedding marker", 
                                   marker_id=marker_id,
                                   pdf_path=str(pdf_path.absolute()))
                else:
                    self.logger.warning("PDF file not found", 
                                      original_path=href,
                                      attempted_paths=[str(p) for p in possible_paths])
                    # Keep the link but mark it as broken
                    link['class'] = link.get('class', []) + ['broken-pdf-link']
                    link['style'] = 'color: #dc3545; text-decoration: line-through;'
                    link.string = f"{link.string} (PDF not found)"
        
        # Add page breaks before major sections
        for header in soup.find_all(['h1', 'h2']):
            if 'pdf-embed-marker' not in header.parent.get('class', []):
                header['style'] = header.get('style', '') + '; page-break-before: always;'
        
        return str(soup)

    def _wrap_long_lines(self, text: str, max_length: int = 80) -> str:
        """Wrap long lines of code to prevent overflow."""
        lines = text.split('\n')
        wrapped_lines = []
        for line in lines:
            if len(line) > max_length:
                # Preserve indentation
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                wrapped = textwrap.fill(
                    line.lstrip(),
                    width=max_length - indent,
                    subsequent_indent=indent_str,
                    break_long_words=False,
                    break_on_hyphens=False
                )
                wrapped_lines.append(wrapped)
            else:
                wrapped_lines.append(line)
        return '\n'.join(wrapped_lines)

    def _truncate_url(self, url: str, max_length: int = 50) -> str:
        """Truncate long URLs for display."""
        if len(url) <= max_length:
            return url
        return url[:max_length//2] + '...' + url[-max_length//2:]
