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
import json
from bs4 import Comment

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
            # Convert markdown to HTML
            html = self.md.convert(markdown_content)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Add first page
            self.pdf.add_page()
            
            # Split content into sections based on metadata comments
            sections = []
            current_section = {'metadata': None, 'content': []}
            
            for element in soup.children:
                if isinstance(element, Comment) and element.strip().startswith('Source:'):
                    if current_section['content']:
                        sections.append(current_section)
                        current_section = {'metadata': None, 'content': []}
                        
                    # Parse metadata
                    meta_lines = element.strip().split('\n')
                    metadata = {}
                    for line in meta_lines:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip()] = value.strip()
                    current_section['metadata'] = metadata
                else:
                    current_section['content'].append(element)
                    
            if current_section['content']:
                sections.append(current_section)
                
            # Process each section
            for section in sections:
                if section['metadata']:
                    content_soup = BeautifulSoup('', 'html.parser')
                    for element in section['content']:
                        content_soup.append(element)
                    await self._process_document_section(self.pdf, section['metadata'], content_soup)
                    
            # Output PDF
            self.pdf.output(str(output_file))
            logger.info("pdf_generated", output_path=str(output_file))
            
        except Exception as e:
            logger.error("pdf_generation_error",
                        error=str(e),
                        error_type=type(e).__name__,
                        traceback=traceback.format_exc())
            raise PDFGenerationError(f"Failed to generate PDF: {str(e)}")
            
    async def _process_document_section(self, pdf: NovaPDF, metadata: dict, content_soup: BeautifulSoup) -> None:
        """Process a complete document section with metadata and content."""
        try:
            # Add section separator if not first section
            if pdf.page_no() > 1 or pdf.get_y() > 30:
                pdf.add_page()  # Start each document on a new page
                
            # Add metadata block with better styling
            pdf.set_fill_color(246, 248, 250)  # Lighter gray background
            start_y = pdf.get_y()
            pdf.rect(pdf.get_x(), start_y, 190, 35, 'F')  # Taller box for metadata
            
            # Add title with better spacing
            if self.has_unicode:
                pdf.set_font('Unicode', 'B', 16)
            else:
                pdf.set_font('Helvetica', 'B', 16)
                
            pdf.set_x(pdf.get_x() + 8)  # Slightly more indent
            title = metadata.get('title', 'Untitled Document')
            pdf.write(10, title)
            pdf.ln(8)
            
            # Add metadata details with better layout
            if self.has_unicode:
                pdf.set_font('Unicode', 'I', 9)
            else:
                pdf.set_font('Helvetica', 'I', 9)
                
            pdf.set_x(pdf.get_x() + 8)
            pdf.set_text_color(80, 80, 80)  # Darker gray for metadata
            date = metadata.get('date', 'Unknown')
            filename = metadata.get('filename', 'Unknown')
            pdf.write(4, f"Date: {date}")
            pdf.ln(4)
            pdf.set_x(pdf.get_x() + 8)
            pdf.write(4, f"Source: {filename}")
            
            # Reset formatting
            pdf.set_text_color(0, 0, 0)
            if self.has_unicode:
                pdf.set_font('Unicode', '', 11)
            else:
                pdf.set_font('Helvetica', '', 11)
            pdf.ln(20)  # More space after metadata block
            
            # Add a subtle line under metadata
            pdf.line(pdf.get_x(), pdf.get_y() - 5, pdf.get_x() + 190, pdf.get_y() - 5)
            pdf.ln(10)
            
            # Process content
            await self._process_elements(pdf, content_soup)
            
        except Exception as e:
            logger.error("document_section_processing_error",
                        error=str(e),
                        metadata=metadata,
                        traceback=traceback.format_exc())

    async def _process_embedded_document(self, pdf: NovaPDF, element: BeautifulSoup) -> None:
        """Handle embedded document references with proper formatting."""
        try:
            # Parse link and metadata
            link = element.find('a')
            if not link:
                return
            
            # Parse JSON metadata from comment
            meta_comment = element.find(string=lambda text: isinstance(text, Comment))
            embed_meta = json.loads(meta_comment.strip()) if meta_comment else {}
            
            file_path = link['href']
            file_type = Path(file_path).suffix.lower()
            
            # Add document box
            start_y = pdf.get_y()
            pdf.rect(pdf.get_x(), start_y, 190, 30)
            pdf.ln(2)
            
            # Add icon and title
            if self.has_unicode:
                pdf.set_font('Unicode', 'B', 11)
            else:
                pdf.set_font('Helvetica', 'B', 11)
                
            icon = {
                '.pdf': '📄',
                '.docx': '📝',
                '.doc': '📝', 
                '.pptx': '📊',
                '.ppt': '📊'
            }.get(file_type, '📎')
            
            if not self.has_unicode:
                icon = f"[{file_type.upper()}]"
            
            pdf.set_x(pdf.get_x() + 5)  # Indent
            pdf.write(5, f"{icon} {Path(file_path).name}")
            pdf.ln(5)
            
            # Add metadata
            if self.has_unicode:
                pdf.set_font('Unicode', '', 9)
            else:
                pdf.set_font('Helvetica', '', 9)
                
            pdf.set_x(pdf.get_x() + 5)  # Indent
            if embed_meta.get('preview'):
                pdf.write(5, "📥 Preview available")
            if embed_meta.get('embed'):
                pdf.write(5, " 📎 Embedded content")
            pdf.ln(8)
            
            # Reset position
            pdf.ln(5)
            
        except Exception as e:
            logger.error("embedded_document_processing_error",
                        error=str(e),
                        element=str(element)[:100])

    async def _process_elements(self, pdf: NovaPDF, soup: BeautifulSoup) -> None:
        """Process HTML elements with improved formatting."""
        current_section = None
        list_level = 0
        in_code_block = False
        
        for element in soup.children:
            try:
                # Skip metadata comments - handled by _process_document_section
                if isinstance(element, Comment) and element.strip().startswith('Source:'):
                    continue
                    
                # Handle empty or None elements
                if not element or not hasattr(element, 'name'):
                    continue
                    
                # Handle empty content marker with better styling
                if element.name == 'p' and '[No content for' in element.get_text():
                    pdf.ln(5)
                    # Add light gray box with italic text
                    start_y = pdf.get_y()
                    pdf.set_fill_color(246, 248, 250)
                    height = 12  # Base height
                    pdf.rect(pdf.get_x(), start_y, 190, height, 'F')
                    
                    if self.has_unicode:
                        pdf.set_font('Unicode', 'I', 10)
                    else:
                        pdf.set_font('Helvetica', 'I', 10)
                    pdf.set_text_color(128, 128, 128)
                    
                    pdf.set_x(pdf.get_x() + 5)
                    pdf.write(8, element.get_text())
                    pdf.ln(10)
                    
                    # Reset formatting
                    pdf.set_text_color(0, 0, 0)
                    if self.has_unicode:
                        pdf.set_font('Unicode', '', 11)
                    else:
                        pdf.set_font('Helvetica', '', 11)
                    continue

                # Handle code blocks with dynamic height
                elif element.name == 'pre':
                    in_code_block = True
                    pdf.ln(5)
                    
                    # Calculate height based on content
                    text = await self._sanitize_text(element.get_text())
                    lines = text.split('\n')
                    height = len(lines) * 4 + 10  # 4pt per line + padding
                    
                    # Add gray background
                    start_y = pdf.get_y()
                    pdf.set_fill_color(246, 248, 250)
                    pdf.rect(pdf.get_x(), start_y, 190, height, 'F')
                    
                    # Add code with monospace font
                    pdf.set_font('Courier', '', 9)
                    for line in lines:
                        pdf.set_x(pdf.get_x() + 5)
                        pdf.write(4, line)
                        pdf.ln(4)
                    
                    pdf.ln(5)
                    in_code_block = False
                    
                    # Reset font
                    if self.has_unicode:
                        pdf.set_font('Unicode', '', 11)
                    else:
                        pdf.set_font('Helvetica', '', 11)
                    continue

                # Handle embedded documents with better spacing
                if element.name == 'a' and element.get('href', '').endswith(('.pdf', '.docx', '.pptx', '.doc', '.ppt')):
                    pdf.ln(8)  # Extra space before embedded doc
                    await self._process_embedded_document(pdf, element)
                    pdf.ln(8)  # Extra space after embedded doc
                    continue

                if element.name == 'hr':
                    # Section separator
                    pdf.ln(10)
                    pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
                    pdf.ln(10)
                    
                elif element.name and element.name.startswith('h'):
                    # Header processing
                    level = int(element.name[1])
                    if level == 1:
                        if current_section:
                            pdf.ln(15)
                        current_section = element.get_text()
                        if self.has_unicode:
                            pdf.set_font('Unicode', 'B', 16)
                        else:
                            pdf.set_font('Helvetica', 'B', 16)
                    else:
                        pdf.ln(10)
                        size = max(16 - (level * 2), 11)  # Decrease size with header level
                        if self.has_unicode:
                            pdf.set_font('Unicode', 'B', size)
                        else:
                            pdf.set_font('Helvetica', 'B', size)
                    
                    text = await self._sanitize_text(element.get_text())
                    pdf.write(8, text)
                    pdf.ln(8)
                    
                    # Reset font
                    if self.has_unicode:
                        pdf.set_font('Unicode', '', 11)
                    else:
                        pdf.set_font('Helvetica', '', 11)
                    
                elif element.name in ('ul', 'ol'):
                    list_level += 1
                    for item in element.find_all('li', recursive=False):
                        pdf.ln(2)
                        # Indent based on level
                        pdf.set_x(pdf.get_x() + (list_level * 5))
                        
                        if element.name == 'ol':
                            i = len(item.find_previous_siblings('li')) + 1
                            pdf.write(5, f"{i}. ")
                        else:
                            pdf.write(5, "* ")  # Use asterisk instead of bullet
                        
                        text = await self._sanitize_text(item.get_text())
                        pdf.write(5, text)
                        pdf.ln(5)
                    list_level -= 1
                    
                elif element.name == 'p' and not in_code_block:
                    text = await self._sanitize_text(element.get_text())
                    if text.strip():  # Only process non-empty paragraphs
                        pdf.write(5, text)
                        pdf.ln(8)
                    
                # Add extra spacing after each major section
                if element.name == 'hr':
                    pdf.ln(15)  # Extra space after section separator

            except Exception as e:
                logger.error("element_processing_error",
                           element_type=element.name if hasattr(element, 'name') else type(element),
                           error=str(e),
                           traceback=traceback.format_exc())

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