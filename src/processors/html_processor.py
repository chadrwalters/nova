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
from typing import Dict, List, Optional, Tuple
import fitz  # PyMuPDF
import base64

from src.core.exceptions import ProcessingError
from src.processors.pdf_processor import PDFGenerator

logger = structlog.get_logger(__name__)

class HTMLProcessor:
    """Handles HTML processing and PDF generation."""

    def __init__(self, temp_dir: Path, template_dir: Path) -> None:
        """Initialize HTML processor.
        
        Args:
            temp_dir: Directory for temporary files
            template_dir: Directory containing templates
        """
        self.temp_dir = temp_dir
        self.template_dir = template_dir
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

    def _wrap_html_content(self, html_content: str, resources_dir: Path, css_file: Path) -> str:
        """Wrap HTML content in proper structure with meta tags."""
        # Read CSS content
        with open(css_file, 'r') as f:
            css_content = f.read()
            
        # Convert relative paths to absolute
        html_content = html_content.replace('../attachments', str(resources_dir))
        
        # Replace PDF placeholders with embedded PDFs
        pattern = r'<!-- PDF_EMBED_START:([^:]+):([^-]+) --><div class="pdf-placeholder">[^<]+</div><!-- PDF_EMBED_END:\1 -->'
        for match in re.finditer(pattern, html_content):
            pdf_path, title = match.groups()
            # Read PDF content and convert to base64
            with open(pdf_path, 'rb') as f:
                pdf_content = f.read()
                pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Replace placeholder with embedded PDF
            placeholder = match.group(0)
            embed_html = f'''
            <div class="pdf-embed">
                <div class="pdf-title">{title}</div>
                <embed src="data:application/pdf;base64,{pdf_base64}" 
                       type="application/pdf" 
                       width="100%" 
                       height="800px">
            </div>'''
            html_content = html_content.replace(placeholder, embed_html)
            
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova Document</title>
    <style>
        {css_content}
        
        /* PDF Embed Styles */
        .pdf-embed {{
            margin: 2em 0;
            padding: 1em;
            border: 1px solid #ddd;
            background: #fff;
        }}
        
        .pdf-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 1em;
            color: #333;
        }}
        
        .pdf-placeholder {{
            display: none;
        }}
        
        /* Word Document Styles */
        .word-document-content {{
            margin: 2em 0;
            padding: 1em;
            border: 1px solid #ddd;
            background: #fff;
            font-family: "Times New Roman", Times, serif;
        }}
        
        .word-document-header {{
            margin-bottom: 1em;
            padding-bottom: 1em;
            border-bottom: 1px solid #eee;
        }}
        
        .word-document-header h2 {{
            margin: 0;
            padding: 0;
            color: #333;
            font-size: 1.5em;
            font-weight: bold;
        }}
        
        .word-document-meta {{
            color: #666;
            font-size: 0.9em;
            margin-top: 0.5em;
            font-style: italic;
        }}
        
        .word-document-body {{
            line-height: 1.6;
            font-family: "Times New Roman", Times, serif;
        }}
        
        .word-document-body p {{
            margin: 1em 0;
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}
        
        .word-document-body h1,
        .word-document-body h2,
        .word-document-body h3,
        .word-document-body h4,
        .word-document-body h5,
        .word-document-body h6 {{
            color: #333;
            margin: 1.5em 0 0.8em;
        }}
        
        .word-document-body table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1em 0;
        }}
        
        .word-document-body th,
        .word-document-body td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
            vertical-align: top;
        }}
        
        .word-document-body th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        
        .word-document-body ul,
        .word-document-body ol {{
            margin: 1em 0;
            padding-left: 2em;
        }}
        
        .word-document-body li {{
            margin: 0.5em 0;
        }}
        
        .word-document-body img {{
            max-width: 100%;
            height: auto;
            margin: 1em 0;
        }}
        
        /* Print-specific Word document styles */
        @media print {{
            .word-document-content {{
                margin: 2em 0;
                padding: 0;
                border: none;
                break-inside: auto;
            }}
            
            .word-document-header {{
                break-inside: avoid;
                break-after: avoid;
                margin-bottom: 1em;
            }}
            
            .word-document-body {{
                break-inside: auto;
            }}
            
            .word-document-body table {{
                break-inside: avoid;
            }}
            
            .word-document-body h1,
            .word-document-body h2,
            .word-document-body h3,
            .word-document-body h4,
            .word-document-body h5,
            .word-document-body h6 {{
                break-after: avoid;
            }}
            
            .word-document-body p {{
                orphans: 3;
                widows: 3;
            }}
            
            .word-document-body img {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""

    async def _convert_pdf_to_images(self, pdf_path: Path, resources_dir: Path) -> List[Path]:
        """Convert PDF pages to images."""
        try:
            # Open the PDF
            pdf_doc = fitz.open(str(pdf_path))
            
            # Create a directory for the images
            images_dir = resources_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Convert each page to an image
            image_paths = []
            for page_num in range(len(pdf_doc)):
                page = pdf_doc[page_num]
                
                # Get the page as an image with high resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                
                # Save the image directly to disk
                image_path = images_dir / f"page_{page_num}.png"
                pix.save(str(image_path))
                image_paths.append(image_path)
                
                # Free memory
                pix = None
                page = None
                
                self.logger.debug("Converted PDF page to image",
                               page=page_num,
                               target=str(image_path))
            
            # Close the PDF
            pdf_doc.close()
            return image_paths
            
        except Exception as e:
            self.logger.error("Failed to convert PDF to images", error=str(e))
            raise ProcessingError(f"Failed to convert PDF to images: {e}")

    async def _embed_pdf_as_images(self, input_html: str, pdf_path: Path, marker_id: str, resources_dir: Path) -> str:
        """Embed a PDF as a series of images in the HTML."""
        try:
            # Convert PDF to images
            image_paths = await self._convert_pdf_to_images(pdf_path, resources_dir)
            
            # Create HTML for the images
            images_html = []
            for image_path in image_paths:
                # Use relative path from resources directory
                rel_path = image_path.relative_to(resources_dir)
                
                # Add image HTML with relative path
                images_html.append(f'<img src="{rel_path}" class="pdf-page" style="width: 100%; margin: 10px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">')
            
            # Replace marker with images
            marker = f"<<<{marker_id}>>>"
            return input_html.replace(marker, "\n".join(images_html))
            
        except Exception as e:
            self.logger.error("Failed to embed PDF as images", error=str(e))
            raise ProcessingError(f"Failed to embed PDF as images: {e}")

    async def _prepare_resources(self, html_content: str, css_file: Path) -> Tuple[str, List[Path]]:
        """Prepare resources for HTML generation."""
        # Extract and process embedded content
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process Word document content
        for div in soup.find_all('div', class_='word-document-content'):
            # Get the HTML file path from the iframe
            iframe = div.find('iframe')
            if iframe and iframe.get('src', '').startswith('../attachments/word/'):
                html_file = iframe.get('src', '').replace('../attachments/', '')
                html_path = Path("/tmp/nova_output/resources") / html_file
                
                try:
                    # Read the Word document HTML content
                    if html_path.exists():
                        with open(html_path, 'r', encoding='utf-8') as f:
                            word_content = f.read()
                            
                        # Parse the Word document HTML
                        word_soup = BeautifulSoup(word_content, 'html.parser')
                        
                        # Extract metadata from the Word document
                        meta_div = div.find('div', class_='word-document-meta')
                        if meta_div:
                            meta_div.clear()  # Remove existing content
                            
                            # Add formatted metadata
                            last_modified = datetime.fromtimestamp(html_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                            meta_div.append(f"Last Modified: {last_modified}")
                        
                        # Extract the body content
                        body_content = word_soup.find('body')
                        if body_content:
                            # Create a new div for the Word content
                            word_div = soup.new_tag('div')
                            word_div['class'] = 'word-document-body'
                            
                            # Process and copy content from the Word document body
                            for child in body_content.children:
                                if isinstance(child, str):
                                    if child.strip():  # Only append non-empty strings
                                        p = soup.new_tag('p')
                                        p['class'] = 'word-paragraph'
                                        p.string = child.strip()
                                        word_div.append(p)
                                else:
                                    # Clean up and format the element
                                    if child.name == 'p':
                                        child['class'] = 'word-paragraph'
                                        # Remove empty paragraphs
                                        if not child.get_text(strip=True):
                                            continue
                                    elif child.name == 'table':
                                        child['class'] = 'word-table'
                                        # Add classes to table cells
                                        for td in child.find_all(['td', 'th']):
                                            td['class'] = 'word-table-cell'
                                    elif child.name in ['ul', 'ol']:
                                        child['class'] = 'word-list'
                                        # Add classes to list items
                                        for li in child.find_all('li'):
                                            li['class'] = 'word-list-item'
                                    elif child.name == 'h1':
                                        child['class'] = 'word-heading-1'
                                    elif child.name == 'h2':
                                        child['class'] = 'word-heading-2'
                                    elif child.name == 'h3':
                                        child['class'] = 'word-heading-3'
                                    
                                    # Process images
                                    for img in child.find_all('img'):
                                        src = img.get('src', '')
                                        if src.startswith('data:'):
                                            continue  # Skip data URLs
                                            
                                        try:
                                            # Get source path
                                            src_path = Path(src)
                                            if not src_path.is_absolute():
                                                src_path = Path("/tmp/nova_output") / src
                                            
                                            if src_path.exists():
                                                # Copy to resources directory
                                                target_name = f"{src_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{src_path.suffix}"
                                                target_path = Path("/tmp/nova_output/resources") / target_name
                                                target_path.parent.mkdir(parents=True, exist_ok=True)
                                                shutil.copy2(src_path, target_path)
                                                
                                                # Update src to absolute path
                                                img['src'] = f'file://{str(target_path)}'
                                        except Exception as e:
                                            self.logger.warning(f"Failed to process image {src}", error=str(e))
                                    
                                    # Clean up any empty elements
                                    if child.get_text(strip=True) or child.find('img'):
                                        # Copy the element and its children
                                        new_child = soup.new_tag(child.name)
                                        new_child.attrs = child.attrs
                                        for content in child.contents:
                                            new_child.append(content.copy())
                                        word_div.append(new_child)
                            
                            # Replace the iframe with the actual content
                            iframe.replace_with(word_div)
                except Exception as e:
                    self.logger.error(f"Failed to process Word document {html_file}",
                                    component="html_processor",
                                    error=str(e))
        
        # Process PDF embeds
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if src.startswith('../attachments/pdf/'):
                # Get the PDF file name
                pdf_name = src.split('/')[-1]
                
                # Create an object tag for the PDF
                obj = soup.new_tag('object')
                obj['data'] = f'file://{str(Path("/tmp/nova_output/resources") / pdf_name)}'
                obj['type'] = 'application/pdf'
                obj['width'] = '100%'
                obj['height'] = '800px'
                
                # Add fallback content
                embed = soup.new_tag('embed')
                embed['src'] = obj['data']
                embed['type'] = 'application/pdf'
                embed['width'] = '100%'
                embed['height'] = '800px'
                obj.append(embed)
                
                # Replace iframe with object
                iframe.replace_with(obj)
        
        # Process images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src.startswith('data:'):
                continue  # Skip data URLs
                
            try:
                # Get source path
                src_path = Path(src)
                if not src_path.is_absolute():
                    src_path = Path("/tmp/nova_output") / src
                
                if src_path.exists():
                    # Copy to resources directory
                    target_name = f"{src_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{src_path.suffix}"
                    target_path = Path("/tmp/nova_output/resources") / target_name
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_path, target_path)
                    
                    # Update src to absolute path
                    img['src'] = f'file://{str(target_path)}'
            except Exception as e:
                self.logger.warning(f"Failed to process image {src}", error=str(e))
        
        # Process other resources
        processed_resources = []
        
        return str(soup), processed_resources

    async def generate_pdf(
        self,
        html_content: str,
        output_file: Path,
        css_file: Path
    ) -> None:
        """Generate PDF from HTML content.

        Args:
            html_content: HTML content to convert
            output_file: Output PDF file path
            css_file: CSS file path

        Raises:
            ProcessingError: If PDF generation fails
        """
        try:
            # Create PDF generator
            pdf_generator = PDFGenerator(self.template_dir)

            # Generate PDF
            await pdf_generator.generate_pdf(
                html_content,
                output_file,
                css_files=[css_file],
                base_url=str(self.temp_dir)
            )

        except Exception as e:
            self.logger.error("PDF generation failed",
                            error=str(e))
            raise ProcessingError(f"Failed to generate PDF: {e}")

    def _make_paths_absolute(self, html_content: str, base_dir: Path) -> str:
        """Convert relative paths to absolute paths."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Handle images
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src and not src.startswith(('data:', 'http:', 'https:')):
                img['src'] = str(base_dir / src)
                
        # Handle links
        for link in soup.find_all('a'):
            href = link.get('href', '')
            if href and not href.startswith(('http:', 'https:', 'mailto:', '#')):
                link['href'] = str(base_dir / href)
                
        # Handle iframes
        for iframe in soup.find_all('iframe'):
            src = iframe.get('src', '')
            if src and not src.startswith(('http:', 'https:')):
                iframe['src'] = str(base_dir / src)
                
        return str(soup)

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
