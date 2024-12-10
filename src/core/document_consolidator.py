import hashlib
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from src.core.config import ProcessingConfig
from src.core.exceptions import (
    ConsolidationError,
    ConversionError,
    MediaError,
    NovaError,
    ProcessingError,
)
from src.core.logging import get_logger
from src.processors.attachment_processor import AttachmentProcessor
from src.processors.html_processor import HTMLProcessor
from src.processors.markdown_processor import MarkdownProcessor

logger = get_logger(__name__)


@dataclass
class ProcessedImage:
    """Result of image processing."""

    path: Path
    target_path: Path
    html_path: Path
    metadata: Dict[str, Any]
    is_valid: bool = True
    error: Optional[str] = None


@dataclass
class ConsolidationResult:
    """Result of document consolidation."""

    content: str
    html_files: List[Path]
    consolidated_html: Path
    warnings: List[str]
    metadata: List[dict]


class DocumentConsolidator:
    """Handles the consolidation of multiple markdown documents."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        consolidated_dir: Path,
        temp_dir: Path,
        template_dir: Path,
        error_tolerance: bool = False,
    ) -> None:
        """Initialize the document consolidator.

        Args:
            input_dir: Directory containing input markdown files
            output_dir: Directory for final output files
            consolidated_dir: Directory for consolidated files
            temp_dir: Directory for temporary files
            template_dir: Directory containing templates
            error_tolerance: Whether to continue on errors
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.consolidated_dir = consolidated_dir
        self.temp_dir = temp_dir
        self.template_dir = template_dir
        self.error_tolerance = error_tolerance
        self.logger = get_logger()

        # Initialize processors
        self.markdown_processor = MarkdownProcessor(
            temp_dir=temp_dir,
            media_dir=output_dir / "_media",
            error_tolerance=error_tolerance,
        )
        self.html_processor = HTMLProcessor(
            temp_dir=temp_dir,
            template_dir=template_dir,
            error_tolerance=error_tolerance,
        )

    def consolidate_files(self, files: List[Path]) -> None:
        """Consolidate multiple markdown files into a single document.

        Args:
            files: List of markdown files to consolidate
        """
        try:
            # Process each file
            processed_contents = self._process_markdown_files(files)

            # Generate consolidated markdown
            consolidated_md = self._generate_consolidated_markdown(processed_contents)
            consolidated_md_path = self.consolidated_dir / "consolidated.md"
            consolidated_md_path.write_text(consolidated_md, encoding="utf-8")
            self.logger.info(f"Created consolidated markdown: {consolidated_md_path}")

            # Convert to HTML
            consolidated_html = self.html_processor.process_content(consolidated_md)
            consolidated_html_path = self.consolidated_dir / "consolidated.html"
            consolidated_html_path.write_text(consolidated_html, encoding="utf-8")
            self.logger.info(f"Created consolidated HTML: {consolidated_html_path}")

            # Generate PDF
            output_pdf = self.output_dir / "consolidated.pdf"
            self.html_processor.generate_pdf(consolidated_html, output_pdf)
            self.logger.info(f"Generated PDF: {output_pdf}")

        except Exception as err:
            self.logger.error("Error during consolidation", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError("Failed to consolidate files") from err

    def _process_markdown_files(self, files: List[Path]) -> List[str]:
        """Process individual markdown files.

        Args:
            files: List of markdown files to process

        Returns:
            List of processed markdown contents
        """
        processed_contents = []
        for file in files:
            try:
                content = self.markdown_processor.process_file(file)
                processed_contents.append(content)
                self.logger.info(f"Processed markdown file: {file}")
            except Exception as err:
                self.logger.error(f"Error processing {file}", exc_info=err)
                if not self.error_tolerance:
                    raise ProcessingError(f"Failed to process {file}") from err
        return processed_contents

    def _generate_consolidated_markdown(self, processed_contents: List[str]) -> str:
        """Generate consolidated markdown from processed markdown contents.

        Args:
            processed_contents: List of processed markdown contents

        Returns:
            Consolidated markdown content
        """
        return "\n\n---\n\n".join(processed_contents)
