"""Module for converting markdown files to PDF format with customizable styling."""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import markdown
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from rich.progress import Progress
from weasyprint import CSS, HTML

from src.utils.colors import NovaConsole
from src.utils.path_utils import format_path, normalize_path

logger = logging.getLogger(__name__)
console = NovaConsole()


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

    def _convert_markdown_to_html(
        self, content: str, media_dir: Optional[Path] = None
    ) -> str:
        """Convert markdown content to HTML with proper media path handling."""
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
            html.write_pdf(
                str(output_file), stylesheets=stylesheets, presentational_hints=True
            )
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise


def convert_markdown_to_pdf(
    input_file: Path,
    output_file: Path,
    media_dir: Optional[Path] = None,
    template_dir: Optional[Path] = None,
    debug_dir: Optional[Path] = None,
) -> None:
    """
    Convert a markdown file to PDF with optional media and template support.

    Args:
        input_file: Path to the input markdown file
        output_file: Path to save the output PDF
        media_dir: Optional directory containing media files
        template_dir: Optional directory containing HTML templates
        debug_dir: Optional directory for debug output
    """
    converter = MarkdownToPDFConverter(template_dir)
    converter.convert(input_file, output_file, media_dir, debug_dir)
