"""Markdown to PDF conversion processor."""

import asyncio
from pathlib import Path
from typing import Optional

import fitz
from bs4 import BeautifulSoup

from src.core.exceptions import PipelineError
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.core.resource_manager import ResourceManager


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
        # Initialize processors
        markdown_processor = MarkdownProcessor()
        html_processor = HTMLProcessor()
        
        # Create resource manager if not provided
        if not resource_manager:
            resource_manager = ResourceManager()
        
        # Convert markdown to HTML
        html_content = await markdown_processor.process_file(input_path)
        
        # Apply template and CSS
        html_content = await html_processor.process_content(
            html_content,
            template_path=template_path,
            css_path=css_path
        )
        
        # Create temporary HTML file
        markdown_processor = MarkdownProcessor(
            temp_dir=config.temp_dir,
            media_dir=config.media_dir,
            error_tolerance=True
        )
        html_processor = HTMLProcessor(
            temp_dir=config.temp_dir,
            template_dir=config.template_dir,
            error_tolerance=True
        )

        # Process markdown
        markdown_content = markdown_processor.process_file(input_path)
        log_file_operation(logger, "read", input_path, "markdown")

        # Save HTML
        html_path = config.html_dir / input_path.with_suffix('.html').name
        html_processor.convert_to_html(markdown_content, html_path)
        log_file_operation(logger, "create", html_path, "html")

        # Generate PDF using PyMuPDF
        html_processor.generate_pdf(
            html_path.read_text(encoding="utf-8"),
            output_path
        )
        log_file_operation(logger, "create", output_path, "pdf")

    except Exception as e:
        logger.error("PDF conversion failed", exc_info=e)
        raise PipelineError(f"Failed to convert {input_path} to PDF: {str(e)}") from e
