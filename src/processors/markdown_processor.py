"""Markdown processing functionality."""

import re
from pathlib import Path
from typing import Optional

import structlog

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)


class MarkdownProcessor:
    """Processor for markdown files and content."""

    def __init__(
        self, temp_dir: Path, media_dir: Path, error_tolerance: bool = False
    ) -> None:
        """Initialize the markdown processor.

        Args:
            temp_dir: Directory for temporary files
            media_dir: Directory for media files
            error_tolerance: Whether to continue on errors
        """
        self.temp_dir = temp_dir
        self.media_dir = media_dir
        self.error_tolerance = error_tolerance
        self.logger = logger

        # Create required directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def process_content(self, content: str) -> str:
        """Process markdown content.

        Args:
            content: Raw markdown content

        Returns:
            Processed markdown content
        """
        try:
            # Clean up line endings
            content = content.replace('\r\n', '\n')
            
            # Remove multiple blank lines
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            # Fix list formatting
            lines = []
            for line in content.split('\n'):
                # Convert bullet points to standard markdown
                if re.match(r'^[\s]*[·•-]', line):
                    line = re.sub(r'^[\s]*[·•-]\s*', '* ', line)
                lines.append(line)
            
            content = '\n'.join(lines)
            
            return content

        except Exception as err:
            self.logger.error("Error processing markdown content", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError("Failed to process markdown content") from err
            return content

    def _extract_metadata(self, content: str) -> tuple[str, str]:
        """Extract metadata from content.

        Args:
            content: Raw markdown content

        Returns:
            Tuple of (metadata, remaining_content)
        """
        lines = content.split("\n")
        metadata_lines = []
        content_lines = []
        in_metadata = True

        for line in lines:
            if not line.strip() and in_metadata:
                in_metadata = False
                continue
            if in_metadata and (line.startswith("·") or line.startswith("*") or line.startswith("#")):
                metadata_lines.append(line)
            else:
                in_metadata = False
                content_lines.append(line)

        metadata = "\n".join(metadata_lines)
        content = "\n".join(content_lines)
        return metadata, content

    def _clean_whitespace(self, content: str) -> str:
        """Clean up whitespace in content.

        Args:
            content: Markdown content

        Returns:
            Cleaned content
        """
        # Remove multiple blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)
        # Remove trailing whitespace
        content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
        return content

    def _process_lists(self, content: str) -> str:
        """Process lists and indentation.

        Args:
            content: Markdown content

        Returns:
            Processed content
        """
        lines = content.split("\n")
        processed_lines = []
        list_level = 0

        for line in lines:
            # Handle list items
            if re.match(r"^[\s]*[-*·]\s", line):
                # Calculate indentation level
                indent = len(re.match(r"^[\s]*", line).group())
                level = indent // 2
                # Ensure proper indentation
                line = "  " * level + "* " + line.lstrip("[-*·] ").strip()
                list_level = level
            elif list_level > 0 and line.strip():
                # Maintain indentation for wrapped lines
                line = "  " * (list_level + 1) + line.strip()
            else:
                list_level = 0

            processed_lines.append(line)

        return "\n".join(processed_lines)

    def _process_urls(self, content: str) -> str:
        """Process URLs in content.

        Args:
            content: Markdown content

        Returns:
            Processed content
        """
        # Wrap long URLs in <span class="url">
        content = re.sub(
            r"(https?://\S{40,})",
            r"<span class='url'>\1</span>",
            content
        )
        return content


class MarkdownChunkProcessor:
    def process_chunk(self, content: str) -> str:
        # Don't break in the middle of:
        # - Code blocks (``` or ~~~)
        # - Tables
        # - Lists (numbered or bulleted)
        # - Image/attachment references and their captions
        # Look for complete logical sections
        return content  # For now, return unmodified content until we implement specific processing


class SectionProcessor:
    def identify_section_boundaries(self, content: str) -> list[tuple[int, int]]:
        """
        Identifies logical section boundaries in markdown content.
        
        Returns:
            List of (start, end) positions for complete sections
        """
        # Look for complete logical units:
        # - Header + content until next header
        # - Complete lists
        # - Image + caption
        # - Complete tables
