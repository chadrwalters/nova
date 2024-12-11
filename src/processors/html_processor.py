"""HTML processing and PDF generation."""

import asyncio
from pathlib import Path
import aiofiles
import pdfkit
import jinja2
import structlog
from bs4 import BeautifulSoup
import re

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
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=True
        )

    def clean_html(self, html_content: str) -> str:
        """Clean and normalize HTML content for PDF generation."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Fix list formatting
        for list_elem in soup.find_all(['ul', 'ol']):
            # Add proper list classes
            list_elem['class'] = list_elem.get('class', []) + ['pdf-list']
            
            # Fix nested lists
            for nested_list in list_elem.find_all(['ul', 'ol']):
                nested_list['class'] = nested_list.get('class', []) + ['pdf-nested-list']
                
            # Fix list items
            for item in list_elem.find_all('li'):
                item['class'] = item.get('class', []) + ['pdf-list-item']
        
        # Fix table formatting
        for table in soup.find_all('table'):
            table['class'] = table.get('class', []) + ['pdf-table']
            # Add wrapper for better control
            wrapper = soup.new_tag('div')
            wrapper['class'] = ['table-wrapper']
            table.wrap(wrapper)
        
        # Fix URL formatting
        for link in soup.find_all('a'):
            url = link.get('href', '')
            if url:
                # Wrap long URLs to prevent overflow
                link['class'] = link.get('class', []) + ['url-content']
        
        # Remove empty elements that could cause spacing issues
        for elem in soup.find_all(True):
            if len(elem.get_text(strip=True)) == 0 and not elem.find_all():
                elem.decompose()
        
        # Normalize whitespace while preserving code blocks
        for text in soup.find_all(text=True):
            if text.parent.name not in ['pre', 'code']:
                text.replace_with(re.sub(r'\s+', ' ', text.string.strip()))
        
        return str(soup)

    def apply_pdf_styles(self, html_content: str, css_path: Path) -> str:
        """Apply PDF-specific styles to HTML content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Ensure we have a head tag
        if not soup.head:
            soup.html.insert(0, soup.new_tag('head'))
        
        # Add meta charset
        meta = soup.new_tag('meta')
        meta['charset'] = 'utf-8'
        soup.head.append(meta)
        
        # Add viewport meta
        viewport = soup.new_tag('meta')
        viewport['name'] = 'viewport'
        viewport['content'] = 'width=device-width, initial-scale=1.0'
        soup.head.append(viewport)
        
        # Add PDF-specific stylesheet
        style_link = soup.new_tag('link')
        style_link['rel'] = 'stylesheet'
        style_link['href'] = str(css_path)
        soup.head.append(style_link)
        
        # Ensure we have a body tag
        if not soup.body:
            soup.html.append(soup.new_tag('body'))
            
        # Add header and footer divs
        if not soup.find('div', {'class': 'pdf-header'}):
            header = soup.new_tag('div')
            header['class'] = 'pdf-header'
            soup.body.insert(0, header)
            
        if not soup.find('div', {'class': 'pdf-footer'}):
            footer = soup.new_tag('div')
            footer['class'] = 'pdf-footer'
            soup.body.append(footer)
        
        return str(soup)

    async def generate_pdf(self, html_content: str, output_path: Path, css_path: Path) -> None:
        """Generate PDF from HTML content."""
        try:
            # Load default template
            template = self.jinja_env.get_template("default.html")
            
            # Clean HTML
            html_content = self.clean_html(html_content)
            
            # Render HTML with template
            rendered_html = template.render(
                content=html_content,
                title="Generated Document"
            )
            
            # Apply PDF styles
            rendered_html = self.apply_pdf_styles(rendered_html, css_path)
            
            # Create temporary HTML file
            async with aiofiles.tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.html',
                dir=self.temp_dir,
                delete=False
            ) as temp_html:
                await temp_html.write(rendered_html)
                temp_html_path = temp_html.name
            
            try:
                # Configure PDF options for better quality and optimization
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8',
                    'print-media-type': None,
                    'enable-local-file-access': None,
                    'header-html': str(self.template_dir / 'header.html'),
                    'footer-html': str(self.template_dir / 'footer.html'),
                    'header-spacing': '5',
                    'footer-spacing': '5',
                    'dpi': '300',
                    'image-dpi': '300',
                    'image-quality': '100',
                    'title': 'Nova Documentation',
                    'grayscale': None,
                    'log-level': 'info'
                }
                
                # Generate PDF
                pdfkit.from_file(
                    temp_html_path,
                    str(output_path),
                    options=options,
                    css=str(css_path)
                )
                
                self.logger.info(
                    "Generated PDF file",
                    output=str(output_path)
                )
                
            finally:
                # Clean up temporary file
                Path(temp_html_path).unlink(missing_ok=True)
                
        except Exception as e:
            self.logger.error(
                "PDF generation failed",
                error=str(e)
            )
            raise ProcessingError(f"Failed to generate PDF: {e}")
