"""Module for converting markdown files to PDF format with customizable styling."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Literal, Optional, TypeVar, cast

import markdown
import structlog
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from rich.progress import Progress
from weasyprint import CSS, HTML

from src.core.exceptions import ProcessingError
from src.utils.colors import NovaConsole
from src.utils.path_utils import format_path, normalize_path

logger = structlog.get_logger(__name__)
console = NovaConsole()

T = TypeVar("T")


class MarkdownToPDFConverter:
    """Handles the conversion of markdown files to PDF format."""

    def __init__(self, template_dir: Optional[Path] = None):
        """Initialize the converter with optional template directory."""
        self.template_dir = template_dir
        self.console = NovaConsole()

    def convert(
        self,
        input_file: Path,
        output_file: Path,
        media_dir: Optional[Path] = None,
        debug_dir: Optional[Path] = None,
    ) -> None:
        """
        Convert a markdown file to PDF.

        Args:
            input_file: Path to the input markdown file
            output_file: Path to save the output PDF
            media_dir: Optional directory containing media files
            debug_dir: Optional directory for debug output
        """
        try:
            # Ensure output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Read markdown content
            markdown_content = input_file.read_text(encoding="utf-8")

            # Convert markdown to HTML
            html_content = self._convert_markdown_to_html(markdown_content, media_dir)

            # Apply template if available
            if self.template_dir:
                html_content = self._apply_template(
                    html_content,
                    title=input_file.stem,
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )

            # Save debug HTML if requested
            if debug_dir:
                debug_dir.mkdir(parents=True, exist_ok=True)
                debug_file = debug_dir / f"{output_file.stem}_debug.html"
                debug_file.write_text(html_content, encoding="utf-8")

            # Convert HTML to PDF
            self._convert_html_to_pdf(html_content, output_file)

            self.console.success(f"Successfully converted {input_file.name} to PDF")

        except Exception as e:
            logger.error(f"Failed to convert {input_file} to PDF: {str(e)}")
            raise

    def _normalize_content(self, content: str) -> str:
        """Normalize content by handling special characters and line endings."""
        # Replace Unicode paragraph separators with newlines
        content = content.replace("\u2029", "\n")

        # Normalize other special characters
        content = content.replace("\u2028", "\n")  # line separator
        content = content.replace("\r\n", "\n")  # Windows line endings
        content = content.replace("\r", "\n")  # Mac line endings

        # Normalize multiple newlines to maximum of two
        while "\n\n\n" in content:
            content = content.replace("\n\n\n", "\n\n")

        return content.strip()

    def _convert_markdown_to_html(
        self, content: str, media_dir: Optional[Path] = None
    ) -> str:
        """Convert markdown content to HTML with proper media path handling."""
        # Normalize content before conversion
        content = self._normalize_content(content)

        html = markdown.markdown(
            content,
            extensions=[
                "extra",
                "codehilite",
                "tables",
                "toc",
                "fenced_code",
                "sane_lists",
            ],
        )

        if media_dir:
            soup = BeautifulSoup(html, "html.parser")
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if src and not src.startswith(("http://", "https://")):
                    img["src"] = str(media_dir / src)
            html = str(soup)

        return html

    def _apply_template(self, content: str, **kwargs) -> str:
        """Apply HTML template to the content with variables."""
        if not self.template_dir:
            return content

        template_file = self.template_dir / "default_template.html"
        if not template_file.exists():
            raise FileNotFoundError(f"Template file not found: {template_file}")

        # Set up Jinja2 environment
        env = Environment(loader=FileSystemLoader(self.template_dir), autoescape=True)
        template = env.get_template("default_template.html")

        # Render template with content and variables
        return template.render(content=content, **kwargs)

    def _convert_html_to_pdf(self, html_content: str, output_file: Path) -> None:
        """Convert HTML content to PDF using weasyprint."""
        try:
            # Create HTML object with content
            html = HTML(string=html_content)

            # Apply CSS if template directory is available
            stylesheets = []
            if self.template_dir:
                style_file = self.template_dir.parent / "styles" / "default_style.css"
                if style_file.exists():
                    stylesheets.append(CSS(filename=str(style_file)))

            # Write PDF with styles
            document = html.render(stylesheets=stylesheets)
            document.write_pdf(str(output_file))

        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise


def convert_markdown_to_pdf(
    input_file: Path,
    output_file: Path,
    *,
    media_dir: Optional[Path] = None,
    template_dir: Optional[Path] = None,
    debug_dir: Optional[Path] = None,
) -> None:
    """Convert markdown file to PDF.

    Args:
        input_file: Input markdown file path
        output_file: Output PDF file path
        media_dir: Optional media directory path
        template_dir: Optional template directory path
        debug_dir: Optional debug output directory path

    Raises:
        FileNotFoundError: If input file doesn't exist
        ProcessingError: If conversion fails
    """
    try:
        # Convert markdown to HTML
        html_content = _convert_to_html(input_file, media_dir)

        # Convert HTML to PDF
        HTML(string=html_content).write_pdf(str(output_file))

        # Save debug output if requested
        if debug_dir:
            debug_file = debug_dir / f"{input_file.stem}.html"
            debug_file.write_text(html_content)

    except Exception as e:
        logger.error(
            "Failed to convert markdown to PDF",
            input_file=str(input_file),
            error=str(e),
        )
        raise ProcessingError(f"Failed to convert markdown to PDF: {e}") from e


def _convert_to_html(input_file: Path, media_dir: Optional[Path] = None) -> str:
    """Convert markdown file to HTML.

    Args:
        input_file: Input markdown file path
        media_dir: Optional media directory path

    Returns:
        The HTML content as a string

    Raises:
        FileNotFoundError: If input file doesn't exist
        ProcessingError: If conversion fails
    """
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Read markdown content
    content = input_file.read_text()

    # Convert to HTML using type-safe approach
    try:
        result = markdown.markdown(content)
        if not isinstance(result, str):
            raise ProcessingError("Markdown conversion failed: output is not a string")
        return result
    except Exception as e:
        raise ProcessingError(f"Failed to convert markdown to HTML: {e}") from e
