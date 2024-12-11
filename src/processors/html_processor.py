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

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)

class HTMLProcessor:
    """Handles HTML processing and PDF generation."""

    def __init__(self, temp_dir: Path, template_dir: Path):
        """Initialize HTML processor.
        
        Args:
            temp_dir: Directory for temporary files
            template_dir: Directory containing HTML templates
        """
        self.temp_dir = temp_dir
        self.template_dir = template_dir
        self.logger = logger.bind(component="html_processor")
        
        # Find wkhtmltopdf path
        wkhtmltopdf_path = shutil.which('wkhtmltopdf')
        if not wkhtmltopdf_path:
            raise ProcessingError("wkhtmltopdf not found in system PATH")
        self.wkhtmltopdf_path = wkhtmltopdf_path
        
        # Initialize Jinja2 environment with custom filters
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Configure PDF options for better layout
        self.pdf_options = {
            'page-size': 'A4',
            'margin-top': '20mm',
            'margin-right': '20mm',
            'margin-bottom': '20mm',
            'margin-left': '20mm',
            'encoding': 'UTF-8',
            'enable-local-file-access': '',
            'allow': [self.temp_dir, self.template_dir],
            'dpi': '300',
            'image-dpi': '300',
            'image-quality': '100',
            'javascript-delay': '1000',
            'no-stop-slow-scripts': '',
            'debug-javascript': '',
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            'quiet': ''
        }

    def _wrap_html_content(self, html_content: str) -> str:
        """Wrap HTML content in proper structure with meta tags."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova Documentation</title>
</head>
<body>
{html_content}
</body>
</html>"""

    async def generate_pdf(self, html_content: str, output_path: Path, css_path: Path) -> Path:
        """Generate PDF from HTML with optimized settings."""
        temp_files = []
        try:
            self.logger.info("Generating PDF", output=str(output_path))
            
            # Clean and wrap HTML
            cleaned_html = self.clean_html(html_content)
            wrapped_html = self._wrap_html_content(cleaned_html)
            
            # Write cleaned HTML to temporary file
            temp_html = self.temp_dir / f"temp_{output_path.stem}.html"
            async with aiofiles.open(temp_html, 'w', encoding='utf-8') as f:
                await f.write(wrapped_html)
            temp_files.append(temp_html)
            
            # Update PDF options
            pdf_options = self.pdf_options.copy()
            pdf_options['user-style-sheet'] = str(css_path)
            
            # Configure wkhtmltopdf
            config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
            
            self.logger.info("Starting PDF generation", 
                           temp_file=str(temp_html),
                           css_file=str(css_path),
                           wkhtmltopdf_path=self.wkhtmltopdf_path)
            
            # Generate PDF
            pdfkit.from_file(
                str(temp_html),
                str(output_path),
                options=pdf_options,
                configuration=config,
                verbose=True
            )
            
            # Verify PDF was generated
            if not output_path.exists() or output_path.stat().st_size == 0:
                raise ProcessingError("PDF file was not generated or is empty")
            
            self.logger.info("PDF generation complete", 
                           output=str(output_path),
                           size=output_path.stat().st_size)
            
            return output_path
            
        except Exception as e:
            self.logger.error("PDF generation failed",
                            error=str(e),
                            temp_file=str(temp_html) if 'temp_html' in locals() else None)
            
            # Keep temp file for debugging if generation failed
            if 'temp_html' in locals() and temp_html.exists():
                debug_html = self.temp_dir / f"debug_{output_path.stem}.html"
                temp_html.rename(debug_html)
                self.logger.info("Saved debug HTML file", debug_file=str(debug_html))
            
            raise ProcessingError(f"PDF generation failed: {str(e)}")
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                try:
                    if temp_file.exists():
                        temp_file.unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temporary file: {str(e)}")

    def clean_html(self, html_content: str) -> str:
        """Clean and normalize HTML content for PDF generation."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Fix list formatting
        for list_elem in soup.find_all(['ul', 'ol']):
            list_elem['class'] = list_elem.get('class', []) + ['pdf-list']
            
            # Fix nested lists
            for nested_list in list_elem.find_all(['ul', 'ol']):
                nested_list['class'] = nested_list.get('class', []) + ['pdf-nested-list']
        
        # Fix code blocks
        for pre in soup.find_all('pre'):
            pre['class'] = pre.get('class', []) + ['code-block']
            # Ensure code blocks don't overflow
            if pre.string:
                pre.string = self._wrap_long_lines(pre.string)
        
        # Fix tables
        for table in soup.find_all('table'):
            table['class'] = table.get('class', []) + ['pdf-table']
            # Add wrapper for overflow handling
            wrapper = soup.new_tag('div', attrs={'class': 'table-wrapper'})
            table.wrap(wrapper)
        
        # Fix links
        for link in soup.find_all('a'):
            if 'href' in link.attrs:
                link['class'] = link.get('class', []) + ['pdf-link']
                # Handle long URLs
                if len(link['href']) > 50:
                    link.string = self._truncate_url(link['href'])
        
        # Add page breaks before major sections
        for header in soup.find_all(['h1', 'h2']):
            header['class'] = header.get('class', []) + ['section-header']
            if header.name == 'h1':
                page_break = soup.new_tag('div', attrs={'class': 'page-break'})
                header.insert_before(page_break)
        
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
