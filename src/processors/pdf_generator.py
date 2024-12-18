from fpdf import FPDF
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
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
import weasyprint
import markdown
from weasyprint import CSS, HTML
import os
import platform

logger = get_logger(__name__)

class NovaPDF(FPDF):
    """Custom PDF class with markdown support."""
    
    def __init__(self):
        # Initialize parent class with default values
        super().__init__(orientation='P', unit='mm', format='A4')
        
        # Get font paths based on OS
        font_paths = self._get_font_paths()
        
        # Add Unicode fonts if available
        if font_paths:
            self.add_font('Unicode', '', font_paths['regular'], uni=True)
            self.add_font('Unicode', 'B', font_paths['bold'], uni=True)
            self.set_font('Unicode', '', 11)
        else:
            # Fallback to built-in fonts
            logger.warning("unicode_fonts_not_found", 
                         message="Using built-in fonts. Unicode characters may not render correctly.")
            self.set_font('Helvetica', '', 11)
        
        # Set margins
        self.set_margins(left=20, top=25, right=20)
        # Set auto page break
        self.set_auto_page_break(auto=True, margin=15)
        
    def _get_font_paths(self) -> dict:
        """Get font paths based on operating system."""
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            base_paths = [
                Path('/Library/Fonts'),
                Path.home() / 'Library/Fonts',
                Path('/System/Library/Fonts')
            ]
            font_names = {
                'regular': ['Arial Unicode.ttf', 'Arial.ttf'],
                'bold': ['Arial Bold.ttf', 'Arial Bold.ttf']
            }
            
        elif system == 'Linux':
            base_paths = [
                Path('/usr/share/fonts/truetype'),
                Path('/usr/share/fonts/TTF'),
                Path('/usr/local/share/fonts')
            ]
            font_names = {
                'regular': ['DejaVuSans.ttf', 'Arial.ttf'],
                'bold': ['DejaVuSans-Bold.ttf', 'Arial-Bold.ttf']
            }
            
        else:  # Windows or other
            base_paths = [
                Path('C:/Windows/Fonts'),
                Path.home() / 'AppData/Local/Microsoft/Windows/Fonts'
            ]
            font_names = {
                'regular': ['arial.ttf'],
                'bold': ['arialbd.ttf']
            }
            
        # Find first available font
        fonts = {}
        for style, names in font_names.items():
            for base_path in base_paths:
                for name in names:
                    font_path = base_path / name
                    if font_path.exists():
                        fonts[style] = str(font_path)
                        break
                if style in fonts:
                    break
                    
        if len(fonts) < 2:
            logger.warning("font_not_found", 
                         message="Could not find required fonts",
                         system=system,
                         searched_paths=base_paths)
            return None
            
        return fonts
        
    def header(self):
        pass
        
    def footer(self):
        self.set_y(-15)
        if hasattr(self, 'unicode_font'):
            self.set_font('Unicode', '', 8)
        else:
            self.set_font('Helvetica', '', 8)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')
        
class PDFGenerator:
    """Handles PDF generation using FPDF2."""
    
    def __init__(self, config: NovaConfig):
        """Initialize PDF generator with configuration."""
        self.config = config
        self.md = markdown.Markdown(extensions=['extra', 'meta'])
        self.pdf = NovaPDF()
        # Store whether we have Unicode font support
        self.has_unicode = hasattr(self.pdf, 'unicode_font')
        
    async def _sanitize_text(self, text: str) -> str:
        """Sanitize text for non-Unicode fonts."""
        if not self.has_unicode:
            # Replace common Unicode characters with ASCII equivalents
            replacements = {
                '"': '"',
                '"': '"',
                ''': "'",
                ''': "'",
                '…': '...',
                '–': '-',
                '—': '-',
                'ć': 'c',
                'č': 'c',
                'š': 's',
                'ž': 'z',
                'đ': 'd',
                '•': '*',  # Replace bullet with asterisk
                '·': '*',  # Alternative bullet
                '○': 'o',  # Open bullet
                '►': '>',  # Right arrow
                '▪': '-',  # Square bullet
                '◦': 'o',  # White bullet
                # Add more mappings as needed
            }
            for unicode_char, ascii_char in replacements.items():
                text = text.replace(unicode_char, ascii_char)
                
            # Remove any remaining non-ASCII characters
            text = text.encode('ascii', 'replace').decode('ascii')
            
        return text
        
    async def debug_unicode_characters(self, text: str) -> List[tuple]:
        """Find non-ASCII characters in text."""
        non_ascii = []
        for i, char in enumerate(text):
            if ord(char) > 127:  # ASCII range is 0-127
                non_ascii.append((i, char, hex(ord(char))))
        return non_ascii
        
    async def generate_pdf(self, markdown_content: str, output_file: Union[str, Path]) -> None:
        """Generate PDF from markdown content."""
        try:
            # Debug unicode characters in markdown content
            non_ascii = await self.debug_unicode_characters(markdown_content)
            if non_ascii:
                logger.warning("unicode_characters_in_markdown", 
                             count=len(non_ascii),
                             first_10=non_ascii[:10])
            
            # Convert output_file to Path if it's a string
            output_file = Path(str(output_file))
            
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert markdown to HTML
            html = self.md.convert(markdown_content)
            
            # Debug unicode characters in HTML
            non_ascii_html = await self.debug_unicode_characters(html)
            if non_ascii_html:
                logger.warning("unicode_characters_in_html", 
                             count=len(non_ascii_html),
                             first_10=non_ascii_html[:10])
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Add first page
            self.pdf.add_page()
            
            # Process HTML elements
            await self._process_elements(self.pdf, soup)
            
            # Output PDF
            self.pdf.output(str(output_file))
            
        except Exception as e:
            logger.error("pdf_generation_error", 
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
            
    async def _process_elements(self, pdf: NovaPDF, soup: BeautifulSoup) -> None:
        """Process HTML elements and add them to PDF."""
        for element in soup.children:
            try:
                if element.name is None:
                    # Handle text content
                    if isinstance(element, str) and element.strip():
                        text = await self._sanitize_text(str(element.strip()))
                        pdf.write(5, text)
                    continue
                    
                # Log element type for debugging
                logger.debug("processing_element", 
                            element_type=element.name,
                            text_preview=element.get_text()[:50] if element.get_text() else None)
                
                if element.name == 'hr':
                    # Handle horizontal rule
                    pdf.ln(5)
                    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
                    pdf.ln(5)
                    
                elif element.name and element.name.startswith('h') and len(element.name) == 2:
                    # Handle headers (h1, h2, etc)
                    try:
                        level = int(element.name[1])
                        text = await self._sanitize_text(str(element.get_text()))
                        font_size = {1: 24, 2: 20, 3: 16}.get(level, 14)
                        
                        # Use Unicode font if available, otherwise Helvetica
                        if self.has_unicode:
                            pdf.set_font('Unicode', 'B', font_size)
                        else:
                            pdf.set_font('Helvetica', 'B', font_size)
                            
                        pdf.ln(10)
                        pdf.write(8, text)
                        pdf.ln(10)
                        
                        # Reset to regular style
                        if self.has_unicode:
                            pdf.set_font('Unicode', '', font_size)
                        else:
                            pdf.set_font('Helvetica', '', font_size)
                            
                    except ValueError:
                        logger.warning("invalid_header_level", 
                                     element_name=element.name,
                                     text=element.get_text()[:50])
                        continue
                    
                elif element.name == 'p':
                    # Handle paragraphs
                    text = await self._sanitize_text(str(element.get_text()))
                    pdf.write(5, text)
                    pdf.ln(8)
                    
                elif element.name in ('ul', 'ol'):
                    # Handle lists
                    for i, item in enumerate(element.find_all('li'), 1):
                        if element.name == 'ol':
                            pdf.write(5, f"{i}. ")
                        else:
                            pdf.write(5, "* ")  # Use asterisk instead of bullet
                        text = await self._sanitize_text(str(item.get_text()))
                        pdf.write(5, text)
                        pdf.ln(5)
                    pdf.ln(3)
                    
                elif element.name == 'pre':
                    # Handle code blocks with monospace font
                    if self.has_unicode:
                        pdf.set_font('Unicode', '', 9)
                    else:
                        pdf.set_font('Courier', '', 9)
                    text = await self._sanitize_text(str(element.get_text()))
                    pdf.write(5, text)
                    pdf.ln(8)
                    # Reset font
                    if self.has_unicode:
                        pdf.set_font('Unicode', '', 11)
                    else:
                        pdf.set_font('Helvetica', '', 11)
                    
            except Exception as e:
                logger.error("element_processing_error",
                           element_type=element.name if hasattr(element, 'name') else type(element),
                           error=str(e),
                           traceback=traceback.format_exc())
                raise

async def generate_pdf_files(config: NovaConfig) -> bool:
    """Generate PDF files from consolidated markdown."""
    try:
        # Get input and output paths
        input_dir = Path(config.processing.phase_markdown_consolidate)
        # Use the output directory from environment variable
        output_dir = Path(os.getenv('NOVA_OUTPUT_DIR', config.processing.processing_dir))
        
        # Define input and output files
        input_file = input_dir / "consolidated.md"
        output_file = output_dir / "consolidated.pdf"
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if not input_file.exists():
            logger.error("input_file_not_found", path=str(input_file))
            return False
            
        # Call the PDF generator with proper Path objects
        success = await generate_pdf(
            input_file=input_file,
            output_file=output_file,
            config=config
        )
        
        return success
        
    except Exception as e:
        logger.error("pdf_generation_failed", 
                    error=str(e),
                    traceback=traceback.format_exc())
        return False

async def generate_pdf(input_file: Path, output_file: Path, config: NovaConfig) -> bool:
    """Generate PDF from markdown file."""
    try:
        # Create PDF generator instance
        pdf_generator = PDFGenerator(config)
        
        # Read markdown content
        async with aiofiles.open(str(input_file), 'r', encoding='utf-8') as f:
            markdown_content = await f.read()
            
        # Generate PDF
        await pdf_generator.generate_pdf(markdown_content, output_file)
        
        logger.info("pdf_generated", output_path=str(output_file))
        return True
        
    except Exception as e:
        logger.error("pdf_generation_failed", error=str(e))
        return False