"""
MarkdownWriter class for generating consistent Markdown output across all handlers.
"""
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class MarkdownWriter:
    """Central class for generating consistent Markdown output."""

    def __init__(self, base_level: int = 1, template_dir: Optional[Path] = None):
        """Initialize the MarkdownWriter.

        Args:
            base_level: The base heading level to start from (default: 1)
            template_dir: Directory containing templates (default: module's template dir)
        """
        self.base_level = base_level
        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"
        self.template_dir = template_dir
        self._template_cache: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)

    def write_section(self, title: str, content: str, level: int = 1) -> str:
        """Write a Markdown section with title and content.

        Args:
            title: The section title
            content: The section content
            level: The heading level (relative to base_level)

        Returns:
            Formatted Markdown section
        """
        actual_level = self.base_level + level - 1
        heading = "#" * actual_level
        return f"{heading} {title}\n\n{content}\n"

    def write_metadata(self, metadata: Dict[str, Any]) -> str:
        """Write metadata in YAML front matter format.

        Args:
            metadata: Dictionary of metadata key-value pairs

        Returns:
            Formatted YAML front matter
        """
        if not metadata:
            return ""

        lines = ["---"]
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")
        lines.append("---\n")

        return "\n".join(lines)

    def write_reference(self, ref_type: str, target: str, label: str) -> str:
        """Write a reference link in standardized format.

        Args:
            ref_type: Type of reference (e.g., 'ATTACH', 'LINK')
            target: Reference target (e.g., file path, URL)
            label: Display text for the reference

        Returns:
            Formatted reference link
        """
        return f"[{label}][{ref_type}:{target}]"

    def write_image_reference(
        self, image_path: str, alt_text: str, title: Optional[str] = None
    ) -> str:
        """Write an image reference in standardized format.

        Args:
            image_path: Path to the image
            alt_text: Alternative text for the image
            title: Optional title for the image

        Returns:
            Formatted image reference
        """
        title_text = f' "{title}"' if title else ""
        return f"![{alt_text}]({image_path}{title_text})"

    def _load_template(self, template_name: str) -> str:
        """Load a template from the template directory.

        Args:
            template_name: Name of the template file (without .md extension)

        Returns:
            Template content

        Raises:
            FileNotFoundError: If template doesn't exist
        """
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        template_path = self.template_dir / f"{template_name}.md"
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
            self._template_cache[template_name] = template
            return template

    def write_from_template(self, template_name: str, **kwargs: Any) -> str:
        """Generate Markdown content using a template.

        Args:
            template_name: Name of the template to use (without .md extension)
            **kwargs: Values to substitute in the template

        Returns:
            Formatted Markdown content

        Raises:
            FileNotFoundError: If template doesn't exist
            KeyError: If required template variables are missing
        """
        self.logger.debug(f"Loading template: {template_name}")
        template = self._load_template(template_name)
        try:
            self.logger.debug(f"Template variables: {kwargs}")
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"Missing required template variable: {e}")
            raise KeyError(f"Missing required template variable: {e}")

    def write_document(
        self,
        title: str,
        content: str,
        metadata: Dict[str, Any],
        file_path: Path,
        output_path: Path,
    ) -> str:
        """Write a markdown document with metadata.

        Args:
            title: Document title
            content: Document content
            metadata: Document metadata
            file_path: Original file path
            output_path: Output file path

        Returns:
            Markdown content
        """
        # Create metadata block
        metadata_block = self.write_metadata(
            {"file_name": file_path.name, "file_path": str(file_path), **metadata}
        )

        # Process image paths in content
        def replace_image_path(match):
            alt_text = match.group(1)
            img_path = match.group(2)
            # Convert to Path object
            img_path = Path(img_path)
            try:
                # Get relative path from output file to image
                rel_path = os.path.relpath(img_path, output_path.parent)
                return f"![{alt_text}]({rel_path})"
            except ValueError:
                # If paths are on different drives, use original path
                return match.group(0)

        # Replace image paths with relative paths
        content = re.sub(r"!\[(.*?)\]\((.*?)\)", replace_image_path, content)

        # Combine all parts
        parts = [metadata_block, f"# {title}", content]

        return "\n\n".join(parts)

    def write_image(
        self,
        title: str,
        image_path: Path,
        alt_text: str,
        description: str,
        analysis: str,
        metadata: Dict[str, Any],
        file_path: Path,
        output_path: Path,
    ) -> str:
        """Write an image document using the image template.

        Args:
            title: Image title
            image_path: Path to the image file
            alt_text: Alternative text for the image
            description: Image description
            analysis: Image analysis text
            metadata: Image metadata
            file_path: Original file path
            output_path: Output file path

        Returns:
            Formatted Markdown content
        """
        # Create reference marker for the image
        image_marker = f"![ATTACH:IMAGE:{image_path.stem}]"

        return self.write_from_template(
            "image",
            title=title,
            image_marker=image_marker,
            alt_text=alt_text,
            description=description,
            analysis=analysis,
            metadata=self.write_metadata(metadata),
        )
