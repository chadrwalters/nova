"""Module for converting markdown to PDF."""

import tempfile
from pathlib import Path
from typing import Optional

from weasyprint import CSS, HTML

from src.core.exceptions import ConversionError
from src.core.logging import get_logger, get_file_logger, log_file_operation
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor
from src.resources.templates.template_manager import TemplateManager
from src.core.config import ProcessingConfig

logger = get_logger(__name__)


def convert_markdown_to_pdf(
    input_path: Path,
    output_path: Path,
    config: ProcessingConfig,
    css_path: Optional[Path] = None,
) -> None:
    """Convert markdown to PDF using consistent directory structure."""
    logger = get_file_logger(__name__)
    
    try:
        # Initialize processors
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

        # Generate PDF
        html_processor.generate_pdf(
            html_path.read_text(encoding="utf-8"),
            output_path,
            css_path=css_path
        )
        log_file_operation(logger, "create", output_path, "pdf")

    except Exception as e:
        logger.error("PDF conversion failed", exc_info=e)
        raise ConversionError(f"Failed to convert {input_path} to PDF: {str(e)}") from e
