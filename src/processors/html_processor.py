"""HTML processing and PDF generation."""

import asyncio
from pathlib import Path
import aiofiles
import pdfkit
import jinja2
import structlog

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
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=True
        )

    async def generate_pdf(self, html_content: str, output_path: Path) -> None:
        """Generate PDF from HTML content."""
        try:
            # Load default template
            template = self.jinja_env.get_template("default.html")
            
            # Render HTML with template
            rendered_html = template.render(
                content=html_content,
                title="Generated Document"
            )
            
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
                # Configure PDF options
                options = {
                    'page-size': 'A4',
                    'margin-top': '20mm',
                    'margin-right': '20mm',
                    'margin-bottom': '20mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8',
                    'enable-local-file-access': '',
                    'print-media-type': '',
                    'quiet': '',
                    'load-error-handling': 'ignore',
                    'load-media-error-handling': 'ignore',
                    'disable-smart-shrinking': '',
                    'dpi': '300'
                }
                
                # Convert HTML to PDF
                await asyncio.to_thread(
                    pdfkit.from_file,
                    temp_html_path,
                    str(output_path),
                    options=options
                )
                
                self.logger.info(
                    "Generated PDF file",
                    output=str(output_path)
                )
                
            finally:
                # Clean up temporary file
                temp_path = Path(temp_html_path)
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            self.logger.error(
                "PDF generation failed",
                error=str(e),
                output=str(output_path)
            )
            raise ProcessingError(f"Failed to generate PDF: {e}")
