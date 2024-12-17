import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import structlog
import aiofiles
from datetime import datetime
from weasyprint import HTML, CSS
from jinja2 import Environment, FileSystemLoader
import tempfile
import shutil
import re
import base64

from src.core.models import ConsolidatedDocument, ProcessingConfig
from src.core.exceptions import PDFGenerationError
from src.processors.attachment_processor import AttachmentProcessor

logger = structlog.get_logger(__name__)

class PDFGenerator:
    """Generates PDF from consolidated markdown."""

    def __init__(self, config: ProcessingConfig):
        """Initialize the PDF generator.
        
        Args:
            config: Processing configuration
        """
        self.config = config
        self.template_dir = config.template_dir
        self.output_dir = config.output_dir
        
        # Initialize Jinja environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir))
        )
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def generate(
        self,
        consolidated: ConsolidatedDocument,
        output_path: Optional[Path] = None
    ) -> Path:
        """Generate PDF from consolidated document."""
        try:
            if output_path is None:
                output_path = self.output_dir / "output.pdf"
            
            # Get base path from first document
            base_path = consolidated.documents[0].source_path.parent
            logger.info(
                "Starting PDF generation",
                base_path=str(base_path),
                output_path=str(output_path)
            )
            
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create media directory structure
                media_dir = temp_path / "media"
                media_dir.mkdir(exist_ok=True)
                
                # Create subdirectories for different types
                (media_dir / "images").mkdir(exist_ok=True)
                (media_dir / "documents").mkdir(exist_ok=True)
                (media_dir / "attachments").mkdir(exist_ok=True)
                
                # Process all attachments (including images)
                attachment_processor = AttachmentProcessor(
                    media_dir=media_dir,
                    error_tolerance=True  # Continue on non-critical errors
                )
                
                updated_content, processed_files = await attachment_processor.process_attachments(
                    consolidated.content,
                    base_path,
                    temp_path
                )
                
                logger.info(
                    "Processed attachments",
                    file_count=len(processed_files)
                )
                
                # Convert markdown to HTML
                html_content = await self._markdown_to_html(
                    updated_content,
                    temp_path
                )
                
                # Apply template
                final_html = await self._apply_template(html_content, consolidated)
                
                # Generate PDF
                await self._generate_pdf(
                    final_html,
                    output_path,
                    consolidated.metadata,
                    temp_path
                )
                
                return output_path
                
        except Exception as e:
            raise PDFGenerationError(
                message=f"Failed to generate PDF: {str(e)}",
                stage="pdf_generation"
            )

    async def _markdown_to_html(
        self,
        content: str,
        temp_dir: Path
    ) -> str:
        """Convert markdown content to HTML.
        
        Args:
            content: Markdown content string
            temp_dir: Temporary directory for processing
            
        Returns:
            HTML content
        """
        try:
            # Convert markdown to HTML
            import markdown
            html = markdown.markdown(
                content,
                extensions=[
                    'extra',
                    'codehilite',
                    'tables',
                    'toc',
                    'fenced_code',
                    'sane_lists'
                ]
            )
            
            return html
            
        except Exception as e:
            raise PDFGenerationError(
                f"Failed to convert markdown to HTML: {str(e)}"
            )

    async def _apply_template(
        self,
        content: str,
        consolidated: ConsolidatedDocument
    ) -> str:
        """Apply HTML template to content.
        
        Args:
            content: HTML content
            consolidated: Consolidated document
            
        Returns:
            Complete HTML document
        """
        try:
            # Load template
            template = self.jinja_env.get_template('pdf_template.html')
            
            # Render template
            return template.render(
                content=content,
                metadata=consolidated.metadata,
                title=consolidated.metadata.get('title', 'Document'),
                date=datetime.now().strftime("%Y-%m-%d"),
                toc=True
            )
            
        except Exception as e:
            raise PDFGenerationError(
                f"Failed to apply template: {str(e)}"
            )

    async def _generate_pdf(
        self,
        html_content: str,
        output_path: Path,
        metadata: Dict[str, Any],
        base_url: Path
    ) -> None:
        """Generate PDF from HTML.
        
        Args:
            html_content: HTML content
            output_path: Output PDF path
            metadata: Document metadata
            base_url: Base URL for resolving relative paths
        """
        try:
            css_file = self.template_dir / "pdf_styles.css"
            css = CSS(filename=str(css_file.resolve()))
            
            # Use file:// URL for base_url
            base_url_str = f"file://{base_url.resolve()}"
            
            html = HTML(
                string=html_content,
                base_url=base_url_str
            )
            
            html.write_pdf(
                target=str(output_path),
                stylesheets=[css],
                presentational_hints=True
            )
            
        except Exception as e:
            raise PDFGenerationError(
                f"Failed to generate PDF: {str(e)}"
            )

    async def _copy_file(self, source: Path, target: Path) -> None:
        """Copy file asynchronously.
        
        Args:
            source: Source file path
            target: Target file path
        """
        target.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiofiles.open(source, 'rb') as src, \
                   aiofiles.open(target, 'wb') as dst:
            while chunk := await src.read(8192):  # 8KB chunks
                await dst.write(chunk) 