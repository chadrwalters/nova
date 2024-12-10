from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        consolidated_dir: Path,
        processing_dir: Optional[Path] = None,
        media_dir: Optional[Path] = None,
        template_dir: Optional[Path] = None,
        css_file: Optional[Path] = None,
        error_tolerance: str = "lenient",
    ):
        """Initialize configuration.

        Args:
            input_dir: Directory containing input markdown files
            output_dir: Directory for output files
            consolidated_dir: Directory for consolidated output
            processing_dir: Directory for intermediate processing files
            media_dir: Directory for media files
            template_dir: Directory containing HTML templates
            css_file: Optional CSS file for styling
            error_tolerance: How to handle errors ("strict" or "lenient")
        """
        self.input_dir = input_dir.resolve()
        self.output_dir = output_dir.resolve()
        self.consolidated_dir = consolidated_dir.resolve()
        self.processing_dir = processing_dir
        self.media_dir = media_dir
        self.template_dir = template_dir or Path("src/resources/templates")
        self.css_file = css_file
        self.error_tolerance = error_tolerance

        # Create necessary directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.consolidated_dir.mkdir(parents=True, exist_ok=True)

        if self.processing_dir:
            self.processing_dir = self.processing_dir.resolve()
            self.processing_dir.mkdir(parents=True, exist_ok=True)
            (self.processing_dir / "markdown").mkdir(parents=True, exist_ok=True)
            (self.processing_dir / "html").mkdir(parents=True, exist_ok=True)
            (self.processing_dir / "html" / "individual").mkdir(
                parents=True, exist_ok=True
            )
            (self.processing_dir / "attachments").mkdir(parents=True, exist_ok=True)
            (self.processing_dir / "media").mkdir(parents=True, exist_ok=True)

    @property
    def html_dir(self) -> Path:
        """Get the HTML output directory."""
        if not self.processing_dir:
            raise ValueError("Processing directory not configured")
        return self.processing_dir / "html"

    @property
    def individual_html_dir(self) -> Path:
        """Get the directory for individual HTML files."""
        if not self.processing_dir:
            raise ValueError("Processing directory not configured")
        return self.processing_dir / "html" / "individual"

    @property
    def media_output_dir(self) -> Path:
        """Get the media output directory."""
        if not self.processing_dir:
            raise ValueError("Processing directory not configured")
        return self.processing_dir / "media"

    @property
    def attachments_dir(self) -> Path:
        """Get the attachments directory."""
        if not self.processing_dir:
            raise ValueError("Processing directory not configured")
        return self.processing_dir / "attachments"
