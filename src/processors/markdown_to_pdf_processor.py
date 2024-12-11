"""Markdown to PDF conversion processor."""

import asyncio
from pathlib import Path
from typing import Optional
import structlog

from src.core.exceptions import PipelineError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.core.resource_manager import ResourceManager

logger = structlog.get_logger(__name__)

async def convert_markdown_to_pdf(
    input_path: Path,
    output_path: Path,
    resource_manager: Optional[ResourceManager] = None,
    template_path: Optional[Path] = None,
    css_path: Optional[Path] = None
) -> Path:
    """Convert markdown file to PDF.
    
    Args:
        input_path: Path to input markdown file
        output_path: Path to output PDF file
        resource_manager: Optional resource manager for file operations
        template_path: Optional path to HTML template
        css_path: Optional path to CSS file
        
    Returns:
        Path to generated PDF file
        
    Raises:
        PipelineError: If conversion fails at any stage
    """
    try:
        # Create resource manager if not provided
        if not resource_manager:
            resource_manager = ResourceManager()

        # Set up processors with proper directories
        markdown_processor = MarkdownProcessor(
            temp_dir=resource_manager.temp_dir,
            media_dir=resource_manager.media_dir,
            error_tolerance=True
        )
        
        html_processor = HTMLProcessor(
            temp_dir=resource_manager.temp_dir,
            template_dir=resource_manager.template_dir
        )

        # Process markdown
        logger.info("Processing markdown", file=str(input_path))
        html_content = await markdown_processor.convert_to_html(input_path)

        # Ensure CSS path exists
        if not css_path:
            css_path = resource_manager.template_dir / 'styles' / 'pdf.css'
        
        if not css_path.exists():
            raise PipelineError(f"CSS file not found: {css_path}")

        # Generate PDF
        logger.info("Generating PDF", output=str(output_path))
        await html_processor.generate_pdf(
            html_content,
            output_path,
            css_path
        )

        logger.info("PDF generation complete", output=str(output_path))
        return output_path

    except Exception as e:
        logger.error(
            "PDF conversion failed",
            input=str(input_path),
            output=str(output_path),
            error=str(e)
        )
        raise PipelineError(f"Failed to convert {input_path} to PDF: {str(e)}") from e
