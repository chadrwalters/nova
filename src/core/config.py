from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    template_dir: Path
    media_dir: Path
    relative_media_path: str
    debug_dir: Optional[Path] = None
    error_tolerance: Literal["strict", "lenient"] = "lenient"

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure paths exist
        if not self.template_dir.exists():
            raise ValueError(f"Template directory does not exist: {self.template_dir}")
        if not self.media_dir.parent.exists():
            self.media_dir.parent.mkdir(parents=True, exist_ok=True)

        # Create media directory if it doesn't exist
        self.media_dir.mkdir(exist_ok=True)

        # Create debug directories if enabled
        if self.debug_dir:
            self.debug_dir = self.debug_dir.resolve()
            self.debug_dir.mkdir(parents=True, exist_ok=True)
            (self.debug_dir / "markdown").mkdir(parents=True, exist_ok=True)
            (self.debug_dir / "html").mkdir(parents=True, exist_ok=True)
            (self.debug_dir / "html" / "individual").mkdir(parents=True, exist_ok=True)
            (self.debug_dir / "attachments").mkdir(parents=True, exist_ok=True)
            (self.debug_dir / "media").mkdir(parents=True, exist_ok=True)

        # Validate error_tolerance
        if self.error_tolerance not in ("strict", "lenient"):
            raise ValueError("error_tolerance must be either 'strict' or 'lenient'")

    def get_media_path(self, is_consolidated: bool) -> str:
        """Get the correct media path based on context."""
        if is_consolidated:
            return "_media"  # Relative to consolidated HTML location
        return "../_media"  # Relative to individual HTML files in html/ subdirectory

    def get_debug_html_dir(self) -> Path:
        """Get the debug HTML directory."""
        if not self.debug_dir:
            raise ValueError("Debug directory not configured")
        return self.debug_dir / "html"

    def get_debug_individual_html_dir(self) -> Path:
        """Get the debug individual HTML directory."""
        if not self.debug_dir:
            raise ValueError("Debug directory not configured")
        return self.debug_dir / "html" / "individual"

    def get_debug_media_dir(self) -> Path:
        """Get the debug media directory."""
        if not self.debug_dir:
            raise ValueError("Debug directory not configured")
        return self.debug_dir / "media"

    def get_debug_attachments_dir(self) -> Path:
        """Get the debug attachments directory."""
        if not self.debug_dir:
            raise ValueError("Debug directory not configured")
        return self.debug_dir / "attachments"
