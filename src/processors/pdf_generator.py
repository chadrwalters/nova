from fpdf import FPDF
from pathlib import Path
from typing import Dict, List, Optional, Any
from ..core.logging import get_logger
from markdown_it import MarkdownIt
from bs4 import BeautifulSoup
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
import aiofiles
import asyncio
from ..core.errors import PDFError, PDFGenerationError, PDFStyleError, PDFContentError
from ..core.config import NovaConfig
import re
import traceback

logger = get_logger(__name__)

class NovaPDF(FPDF):
    """Custom PDF class with markdown support."""
    
    def __init__(self):
        super().__init__()
        # Initialize with Times font
        self.set_font('Times', size=11)
        # Set margins
        self.set_margins(left=20, top=25, right=20)
        # Set auto page break
        self.set_auto_page_break(auto=True, margin=15)
        
    def header(self):
        pass
        
    def footer(self):
        self.set_y(-15)
        self.set_font('Times', size=8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        
class PDFGenerator:
    """Handles PDF generation using FPDF2."""
    
    def __init__(self, config: NovaConfig):
        """Initialize PDF generator with configuration."""
        self.config = config
        self.style_config = config.output.style
        self.default_font_size = self.style_config.font_size
        self.default_font_family = self.style_config.font_family
        self.md = MarkdownIt('commonmark', {
            'typographer': True,
            'linkify': True,
            'breaks': True,
            'html': True
        })
        
    async def generate_pdf(self, content: str, output_path: Path) -> None:
        """Generate PDF from markdown content."""
        try:
            logger.debug("generating_pdf", output_path=str(output_path))
            
            # Convert markdown to HTML
            html = self.md.render(content)
            logger.debug("markdown_to_html", html_preview=html[:500] if html else None)
            
            # Parse HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # Create PDF
            pdf = NovaPDF()
            pdf.set_font(self.default_font_family, size=self.default_font_size)
            
            # Set margins from config
            margins = self.style_config.margins
            pdf.set_margins(left=margins.left, top=margins.top, right=margins.right)
            pdf.set_auto_page_break(auto=True, margin=margins.bottom)
            
            pdf.add_page()
            
            # Process content
            await self._process_elements(pdf, soup)
            
            # Save PDF - Fix bytearray encoding issue
            output_bytes = pdf.output(dest='S')
            if isinstance(output_bytes, bytearray):
                output_bytes = bytes(output_bytes)
            elif isinstance(output_bytes, str):
                output_bytes = output_bytes.encode('latin1')
                
            async with aiofiles.open(str(output_path), 'wb') as f:
                await f.write(output_bytes)
            
            logger.info("pdf_generated", output_path=str(output_path))
            
        except Exception as e:
            logger.error("pdf_generation_failed", error=str(e))
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
            
    async def _process_elements(self, pdf: NovaPDF, soup: BeautifulSoup) -> None:
        """Process HTML elements and add them to PDF."""
        for element in soup.children:
            if element.name is None:
                # Handle text content with formatting
                if isinstance(element, str) and element.strip():
                    try:
                        text = element.strip()
                        if element.parent and element.parent.name in ['strong', 'b']:
                            pdf.set_font(self.default_font_family, style='B')
                        elif element.parent and element.parent.name in ['em', 'i']:
                            pdf.set_font(self.default_font_family, style='I')
                        pdf.write(self.style_config.line_height, text)
                        pdf.set_font(self.default_font_family)
                    except Exception as e:
                        logger.error("text_write_failed", error=str(e))
                continue
                
            try:
                if element.name.startswith('h'):
                    level = int(element.name[1])
                    header_size = getattr(self.style_config.headers, f'h{level}_size', None)
                    if header_size is None:
                        header_size = 24 - (level * 2)
                    pdf.set_font(self.style_config.headers.font_family, size=header_size, style='B')
                    pdf.ln(10)
                    pdf.write(8, element.get_text())
                    pdf.ln(10)
                    pdf.set_font(self.default_font_family, size=self.default_font_size)
                elif element.name == 'p':
                    # Process paragraph with inline formatting
                    for child in element.children:
                        if isinstance(child, str):
                            pdf.write(self.style_config.line_height, child)
                        elif child.name in ['strong', 'b']:
                            pdf.set_font(self.default_font_family, style='B')
                            pdf.write(self.style_config.line_height, child.get_text())
                            pdf.set_font(self.default_font_family)
                        elif child.name in ['em', 'i']:
                            pdf.set_font(self.default_font_family, style='I')
                            pdf.write(self.style_config.line_height, child.get_text())
                            pdf.set_font(self.default_font_family)
                        elif child.name == 'code':
                            pdf.set_font(self.style_config.code.font_family, size=self.style_config.code.font_size)
                            pdf.set_fill_color(int(self.style_config.code.background[1:3], 16),
                                            int(self.style_config.code.background[3:5], 16),
                                            int(self.style_config.code.background[5:7], 16))
                            pdf.write(self.style_config.line_height, f" {child.get_text()} ", fill=True)
                            pdf.set_font(self.default_font_family, size=self.default_font_size)
                    pdf.ln(8)
                elif element.name == 'pre':
                    # Handle code blocks with syntax highlighting
                    code_element = element.find('code')
                    if code_element and 'class' in code_element.attrs:
                        lang = code_element.attrs['class'][0].replace('language-', '')
                        try:
                            lexer = get_lexer_by_name(lang)
                            formatter = HtmlFormatter(style='monokai')
                            highlighted = highlight(code_element.get_text(), lexer, formatter)
                            highlighted_soup = BeautifulSoup(highlighted, 'html.parser')
                            
                            pdf.set_font(self.style_config.code.font_family, size=self.style_config.code.font_size)
                            pdf.set_fill_color(int(self.style_config.code.background[1:3], 16),
                                            int(self.style_config.code.background[3:5], 16),
                                            int(self.style_config.code.background[5:7], 16))
                            
                            for span in highlighted_soup.find_all('span', class_=True):
                                style = formatter.style_defs[span['class'][0]]
                                if 'color: ' in style:
                                    color = style.split('color: ')[1].split(';')[0]
                                    if color.startswith('#'):
                                        r, g, b = self._parse_hex_color(color)
                                        pdf.set_text_color(r, g, b)
                                pdf.write(5, span.get_text())
                                
                            pdf.set_text_color(0, 0, 0)  # Reset text color
                        except Exception as e:
                            logger.warning("syntax_highlighting_failed", error=str(e))
                            pdf.write(5, code_element.get_text())
                    else:
                        pdf.write(5, element.get_text())
                        
                    pdf.ln(8)
                    pdf.set_font(self.default_font_family, size=self.default_font_size)
                elif element.name in ('ul', 'ol'):
                    for i, item in enumerate(element.find_all('li'), 1):
                        if element.name == 'ol':
                            pdf.write(self.style_config.line_height, f"{i}. ")
                        else:
                            pdf.write(self.style_config.line_height, "• ")
                        # Process list item with inline formatting
                        for child in item.children:
                            if isinstance(child, str):
                                pdf.write(self.style_config.line_height, child)
                            elif child.name in ['strong', 'b']:
                                pdf.set_font(self.default_font_family, style='B')
                                pdf.write(self.style_config.line_height, child.get_text())
                                pdf.set_font(self.default_font_family)
                            elif child.name in ['em', 'i']:
                                pdf.set_font(self.default_font_family, style='I')
                                pdf.write(self.style_config.line_height, child.get_text())
                                pdf.set_font(self.default_font_family)
                        pdf.ln(5)
                    pdf.ln(3)
                elif element.name == 'table':
                    # Get table data with formatting
                    rows = []
                    for row in element.find_all('tr'):
                        cells = []
                        for cell in row.find_all(['td', 'th']):
                            formatted_text = []
                            for child in cell.children:
                                if isinstance(child, str):
                                    formatted_text.append(('normal', child.strip()))
                                elif child.name in ['strong', 'b']:
                                    formatted_text.append(('B', child.get_text().strip()))
                                elif child.name in ['em', 'i']:
                                    formatted_text.append(('I', child.get_text().strip()))
                            cells.append(formatted_text)
                        rows.append(cells)
                        
                    if rows:
                        # Calculate column widths
                        num_cols = len(rows[0])
                        col_width = (pdf.get_page_width() - pdf.get_l_margin() - pdf.get_r_margin()) / num_cols
                        
                        # Add headers
                        pdf.set_font(self.default_font_family, size=self.default_font_size, style='B')
                        for cell in rows[0]:
                            text = ''.join(t[1] for t in cell)
                            pdf.cell(col_width, 10, text, border=1)
                        pdf.ln()
                        
                        # Add data rows with formatting
                        for row in rows[1:]:
                            max_height = 10
                            for cell in row:
                                x = pdf.get_x()
                                y = pdf.get_y()
                                for style, text in cell:
                                    pdf.set_font(self.default_font_family, size=self.default_font_size, 
                                               style=style if style != 'normal' else '')
                                    pdf.write(self.style_config.line_height, text + ' ')
                                height = pdf.get_y() - y
                                max_height = max(max_height, height)
                                pdf.set_xy(x + col_width, y)
                            pdf.ln(max_height)
                elif element.name == 'hr':
                    pdf.ln(4)
                    x1 = pdf.get_x()
                    x2 = pdf.get_page_width() - pdf.get_r_margin()
                    y = pdf.get_y()
                    pdf.set_draw_color(*self._parse_hex_color(self.style_config.hr.color))
                    pdf.set_line_width(self._convert_numeric(str(self.style_config.hr.width)))
                    pdf.line(x1, y, x2, y)
                    pdf.ln(4)
            except Exception as e:
                logger.warning("element_processing_failed", 
                             element=element.name, 
                             error=str(e))
                             
            # Reset text properties after each element
            pdf.set_text_color(0, 0, 0)
            pdf.set_font(self.default_font_family, size=self.default_font_size)

    def _parse_hex_color(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _convert_numeric(self, value: str) -> int:
        """Convert numeric value with optional units to integer.
        
        Args:
            value: String value that may include units (e.g. '1.5r', '2pt', '10px')
            
        Returns:
            Integer value normalized to PDF units
        """
        if not value:
            return 1
            
        # Handle relative units by converting to base value
        clean_value = str(value).lower().strip()
        
        # Extract numeric part and unit
        match = re.match(r'^([\d.]+)([a-z%]+)?$', clean_value)
        if not match:
            return 1
            
        numeric_str, unit = match.groups()
        unit = unit or ''
        
        try:
            # Convert numeric part to float
            numeric_value = float(numeric_str)
            
            # Handle different units
            if unit == 'r':  # Relative unit
                base = 1
                result = int(numeric_value * base)
            elif unit == 'pt':  # Points
                result = int(numeric_value)
            elif unit == 'px':  # Pixels
                result = int(numeric_value * 0.75)  # Convert px to pt
            elif unit == '%':  # Percentage
                result = int(numeric_value * 0.01)
            else:  # Default to points
                result = int(numeric_value)
                
            # Ensure result is within valid range
            return max(1, min(result, 5))
            
        except (ValueError, TypeError):
            return 1  # Default to 1 on conversion error