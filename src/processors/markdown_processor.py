import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown

from src.core.exceptions import ProcessingError
from src.core.logging import get_logger
from src.processors.attachment_processor import AttachmentProcessor


class MarkdownProcessor:
    """Processor for handling markdown files and their content."""

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
        self.logger = get_logger()
        self.attachment_processor = AttachmentProcessor(
            media_dir=media_dir, error_tolerance=error_tolerance
        )

        # Create directories
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: Path) -> str:
        """Process a markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Processed markdown content
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            processed_content = self.process_content(content, file_path)
            if processed_content is None:
                raise ProcessingError(f"Failed to process content from {file_path}")
            return processed_content
        except Exception as err:
            self.logger.error(f"Error processing file {file_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(f"Failed to process {file_path}") from err
            return ""

    def process_content(self, content: str, source_path: Path) -> Optional[str]:
        """Process markdown content.

        Args:
            content: Markdown content to process
            source_path: Source file path for resolving relative paths

        Returns:
            Processed markdown content, or None if processing failed
        """
        try:
            # Process attachments
            content = self._process_attachments(content, source_path)

            # Process images
            content = self._process_images(content, source_path)

            # Process links
            content = self._process_links(content, source_path)

            # Fix list formatting
            content = self._fix_list_formatting(content)

            return content

        except Exception as err:
            self.logger.error(
                f"Error processing content from {source_path}", exc_info=err
            )
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to process content from {source_path}"
                ) from err
            return None

    def _process_attachments(self, content: str, source_path: Path) -> str:
        """Process attachments in markdown content.

        Args:
            content: Markdown content to process
            source_path: Source file path for resolving relative paths

        Returns:
            Processed markdown content
        """
        try:
            # Process each attachment
            for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
                link_text, file_path_str = match.groups()
                file_path = source_path.parent / file_path_str

                if file_path.exists() and file_path.is_file():
                    processed = self.attachment_processor.process_attachment(file_path)
                    if processed:
                        relative_path = processed.target_path.relative_to(
                            self.media_dir
                        )
                        content = content.replace(
                            match.group(0), f"[{link_text}]({relative_path})"
                        )

            return content

        except Exception as err:
            self.logger.error(
                f"Error processing attachments in {source_path}", exc_info=err
            )
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to process attachments in {source_path}"
                ) from err
            return content

    def _process_images(self, content: str, source_path: Path) -> str:
        """Process images in markdown content.

        Args:
            content: Markdown content to process
            source_path: Source file path for resolving relative paths

        Returns:
            Processed markdown content
        """
        try:
            # Process each image
            for match in re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", content):
                alt_text, image_path_str = match.groups()
                image_path = source_path.parent / image_path_str

                if image_path.exists() and image_path.is_file():
                    processed = self.attachment_processor.process_attachment(image_path)
                    if processed:
                        relative_path = processed.target_path.relative_to(
                            self.media_dir
                        )
                        content = content.replace(
                            match.group(0), f"![{alt_text}]({relative_path})"
                        )

            return content

        except Exception as err:
            self.logger.error(f"Error processing images in {source_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to process images in {source_path}"
                ) from err
            return content

    def _process_links(self, content: str, source_path: Path) -> str:
        """Process links in markdown content.

        Args:
            content: Markdown content to process
            source_path: Source file path for resolving relative paths

        Returns:
            Processed markdown content
        """
        try:
            # Process each link
            for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", content):
                link_text, link_path_str = match.groups()

                # Skip URLs and anchors
                if link_path_str.startswith(("http://", "https://", "#", "mailto:")):
                    continue

                link_path = source_path.parent / link_path_str
                if link_path.exists() and link_path.is_file():
                    processed = self.attachment_processor.process_attachment(link_path)
                    if processed:
                        relative_path = processed.target_path.relative_to(
                            self.media_dir
                        )
                        content = content.replace(
                            match.group(0), f"[{link_text}]({relative_path})"
                        )

            return content

        except Exception as err:
            self.logger.error(f"Error processing links in {source_path}", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError(
                    f"Failed to process links in {source_path}"
                ) from err
            return content

    def _is_list_item(self, line: str) -> tuple[bool, int]:
        """Check if a line is a list item and get its indentation.

        Args:
            line: Line to check

        Returns:
            Tuple of (is_list_item, indentation)
        """
        list_match = re.match(r"^(\s*)([-*+]|\d+\.)\s", line)
        if list_match:
            return True, len(list_match.group(1))
        return False, 0

    def _should_end_list(
        self,
        line: str,
        in_list: bool,
        list_indent: int,
        is_list_item: bool,
        item_indent: int,
    ) -> bool:
        """Check if the current list should end.

        Args:
            line: Current line
            in_list: Whether we're currently in a list
            list_indent: Current list indentation
            is_list_item: Whether the current line is a list item
            item_indent: Current line's indentation

        Returns:
            Whether the list should end
        """
        if not in_list:
            return False

        # Empty line ends the list
        if not line.strip():
            return True

        # List item with less indentation ends the list
        if is_list_item and item_indent < list_indent:
            return True

        # Non-list item without proper indentation ends the list
        if not is_list_item and line.strip():
            if not line.startswith(" " * (list_indent + 2)):
                return True

        return False

    def _fix_list_formatting(self, content: str) -> str:
        """Fix list formatting in markdown content.

        Args:
            content: Markdown content to fix

        Returns:
            Fixed markdown content
        """
        try:
            lines = content.splitlines()
            fixed_lines: List[str] = []
            in_list = False
            list_indent = 0

            for line in lines:
                # Check if line is a list item
                is_list_item, item_indent = self._is_list_item(line)

                # Check if we should start a new list
                if is_list_item and not in_list:
                    in_list = True
                    list_indent = item_indent
                    if fixed_lines and fixed_lines[-1].strip():
                        fixed_lines.append("")

                # Check if we should end the current list
                elif self._should_end_list(
                    line, in_list, list_indent, is_list_item, item_indent
                ):
                    in_list = False
                    list_indent = 0
                    if line.strip():
                        fixed_lines.append("")

                # Add the line
                fixed_lines.append(line)

            return "\n".join(fixed_lines)

        except Exception as err:
            self.logger.error("Error fixing list formatting", exc_info=err)
            if not self.error_tolerance:
                raise ProcessingError("Failed to fix list formatting") from err
            return content
