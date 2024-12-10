"""Module for converting markdown to PDF."""

from pathlib import Path
from typing import Optional
import tempfile

from weasyprint import CSS, HTML

from src.core.exceptions import ConversionError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.resources.templates.template_manager import TemplateManager
from src.core.logging import get_logger

logger = get_logger(__name__)

def convert_markdown_to_pdf(
    input_path: Path,
    output_path: Path,
    media_dir: Path,
    template_dir: Path,
    processing_dir: Optional[Path] = None,
    css_path: Optional[Path] = None,
    template_name: str = "default.html"
) -> None:
    """Convert a markdown file to PDF.
    
    Args:
        input_path: Path to input markdown file
        output_path: Path to output PDF file
        media_dir: Directory containing media files
        template_dir: Directory containing templates
        processing_dir: Optional directory for processing output
        css_path: Optional path to CSS file
        template_name: Name of HTML template to use
        
    Raises:
        ConversionError: If conversion fails
    """
    try:
        # Use processing directory if available, otherwise use temp directory
        temp_dir = processing_dir / "temp" if processing_dir else Path(tempfile.mkdtemp())
        
        # Initialize processors
        markdown_processor = MarkdownProcessor(
            temp_dir=temp_dir,
            media_dir=media_dir,
            error_tolerance=True
        )
        html_processor = HTMLProcessor(
            temp_dir=temp_dir,
            template_dir=template_dir,
            error_tolerance=True
        )
        
        # Process markdown
        markdown_content = markdown_processor.process_file(input_path)
        if not markdown_content:
            raise ConversionError(f"Failed to process markdown file: {input_path}")
        
        # Convert to HTML
        temp_html = temp_dir / "input.html"
        html_processor.convert_to_html(markdown_content, temp_html)
        
        # Read HTML content
        html_content = temp_html.read_text()
        html_content = html_content.replace('\u2029', '\n').replace('\u2028', '\n')
        
        # Convert HTML to PDF
        html = HTML(string=html_content)
        css = None if not css_path else CSS(filename=str(css_path))
        
        html.write_pdf(output_path, stylesheets=[css] if css else None)
        
        # Clean up if using temp directory
        if not processing_dir:
            temp_dir.unlink()
        
    except Exception as e:
        raise ConversionError(f"Failed to convert {input_path} to PDF: {str(e)}") from e