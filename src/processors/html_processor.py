import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import unquote
from xml.etree import ElementTree as etree

import markdown
import pdfkit
import structlog
from bs4 import BeautifulSoup, Tag
from markdown.blockprocessors import ListIndentProcessor
from markdown.core import Markdown
from markdown.extensions import Extension

from src.core.config import ProcessingConfig
from src.core.exceptions import ConsolidationError, ConversionError, ProcessingError
from src.core.logging import get_logger
from src.resources.templates.template_manager import TemplateManager

logger = get_logger(__name__)


class CustomListExtension(Extension):
    """Custom extension for better list handling."""

    def extendMarkdown(self, md: Markdown) -> None:
        """Extend markdown with custom list processor.

        Args:
            md: Markdown instance to extend
        """
        # Replace the default list processor with our custom one
        md.parser.blockprocessors.register(
            CustomListProcessor(md.parser),
            "list",
            175,  # Priority (higher than default list processor)
        )


class CustomListProcessor(ListIndentProcessor):
    """Custom list processor that handles nested lists better."""

    def __init__(self, parser: Any) -> None:
        """Initialize the list processor.

        Args:
            parser: Markdown parser instance
        """
        super().__init__(parser)
        self.INDENT_RE = re.compile(r"^[ ]*[\*\-\+]\s+")

    def get_level(self, parent: etree.Element, block: str) -> Tuple[int, etree.Element]:
        """Get the list level and parent element.

        Args:
            parent: Parent element
            block: Block of text to process

        Returns:
            Tuple of (level, parent element)
        """
        # Simply use indentation to determine level
        m = self.INDENT_RE.match(block)
        level = 0
        if m:
            indent = len(m.group(0))
            level = max(0, (indent - 2) // 2)
        return level, parent


class HTMLProcessor:
    """Processor for converting markdown to HTML and handling HTML files."""

    def __init__(
        self, temp_dir: Path, template_dir: Path, error_tolerance: bool = False
    ) -> None:
        """Initialize the HTML processor.

        Args:
            temp_dir: Directory for temporary files
            template_dir: Directory containing HTML templates
            error_tolerance: Whether to continue on errors
        """
        self.temp_dir = temp_dir
        self.template_dir = template_dir
        self.error_tolerance = error_tolerance
        self.logger = get_logger()
        self.template_manager = TemplateManager(template_dir)

        # Configure PDF options
        self.pdf_options: Dict[str, Any] = {
            "enable-local-file-access": None,
            "quiet": "",
            "print-media-type": None,
            "margin-top": "20mm",
            "margin-right": "20mm",
            "margin-bottom": "20mm",
            "margin-left": "20mm",
            "encoding": "UTF-8",
            "custom-header": [("Accept-Encoding", "gzip")],
            "no-outline": None,
            "enable-smart-shrinking": "",
        }

    def process_content(self, content: str) -> str:
        """Process markdown content to HTML.

        Args:
            content: Markdown content to process

        Returns:
            Processed HTML content
        """
        try:
            html = markdown.markdown(
                content, extensions=["extra", "meta", "toc", "tables", "fenced_code"]
            )
            return self.template_manager.apply_template(html)
        except Exception as err:
            self.logger.error("Error processing content to HTML", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError("Failed to process content to HTML") from err
            return ""

    def convert_to_html(self, markdown_content: str, output_path: Path) -> None:
        """Convert markdown content to HTML and save to file.

        Args:
            markdown_content: The markdown content to convert
            output_path: Path to save the HTML file
        """
        try:
            html_content = self.process_content(markdown_content)
            output_path.write_text(html_content, encoding="utf-8")
            self.logger.info(f"Created HTML file: {output_path}")
        except Exception as err:
            self.logger.error(f"Error converting to HTML: {output_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to convert to HTML: {output_path}"
                ) from err

    def consolidate_html_files(self, html_files: List[Path], output_file: Path) -> None:
        """Consolidate multiple HTML files into a single file.

        Args:
            html_files: List of HTML files to consolidate
            output_file: Path to save the consolidated HTML file
        """
        try:
            # Read and combine HTML contents
            contents: List[str] = []
            for file in html_files:
                content = file.read_text(encoding="utf-8")
                contents.append(content)

            # Join contents with separators
            consolidated = "\n\n<hr>\n\n".join(contents)

            # Apply template
            final_html = self.template_manager.apply_template(consolidated)

            # Save consolidated file
            output_file.write_text(final_html, encoding="utf-8")
            self.logger.info(f"Created consolidated HTML: {output_file}")

        except Exception as err:
            self.logger.error(
                f"Error consolidating HTML files: {output_file}", exc_info=err
            )
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to consolidate HTML files: {output_file}"
                ) from err

    def generate_pdf(self, html_content: str, output_path: Path) -> None:
        """Generate PDF from HTML content.

        Args:
            html_content: HTML content to convert
            output_path: Path to save the PDF file
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Create temporary HTML file with absolute paths
            temp_html = self.temp_dir / "temp.html"
            temp_html.write_text(html_content, encoding="utf-8")

            # Generate PDF
            pdfkit.from_file(str(temp_html), str(output_path), options=self.pdf_options)

            # Clean up
            temp_html.unlink()
            self.logger.info(f"Generated PDF: {output_path}")

        except Exception as err:
            self.logger.error(f"Error generating PDF: {output_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(f"Failed to generate PDF: {output_path}") from err

    def process_file(self, file_path: Path) -> Optional[str]:
        """Process a markdown file and convert to HTML.

        Args:
            file_path: Path to the markdown file

        Returns:
            HTML content if successful, None otherwise
        """
        try:
            if not file_path.exists():
                self.logger.error(f"File not found: {file_path}")
                return None

            content = file_path.read_text()
            return self.process_content(content)

        except Exception as e:
            self.logger.error(f"Failed to process HTML file {file_path}: {str(e)}")
            return None
