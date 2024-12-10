"""Template management for document processing."""

import datetime
from pathlib import Path

import structlog

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)


class TemplateManager:
    """Manages HTML templates for document processing."""

    def __init__(self, template_dir: Path) -> None:
        """Initialize the template manager.

        Args:
            template_dir: Directory containing HTML templates

        Raises:
            ProcessingError: If no template files are found
        """
        self.template_dir = template_dir
        self.template_path = Path(__file__).parent / "template.html"

        if not self.template_path.exists():
            self.template_path = Path(__file__).parent / "default.html"
            if not self.template_path.exists():
                logger.error("No template files found in resources")
                raise ProcessingError("No template files found in resources")

        logger.info(
            "Initialized template manager", template_path=str(self.template_path)
        )

    def apply_template(self, content: str) -> str:
        """Apply HTML template to content.

        Args:
            content: HTML content to wrap in template

        Returns:
            str: Content wrapped in HTML template

        Raises:
            ProcessingError: If template application fails
        """
        try:
            template = self.template_path.read_text(encoding="utf-8")
            current_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            return (
                template.replace("{{content}}", content)
                .replace("{{title}}", "Consolidated Document")
                .replace("{{date}}", current_date)
            )
        except Exception as err:
            logger.error("Failed to apply template", error=str(err))
            raise ProcessingError("Failed to apply template") from err
