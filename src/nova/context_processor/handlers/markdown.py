"""Markdown file handler."""

# Standard library
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Match, Optional, Union, Tuple, Any, Set

# Internal imports
from nova.context_processor.config.manager import ConfigManager
from nova.context_processor.core.metadata.models.types import DocumentMetadata
from nova.context_processor.core.markdown.writer import MarkdownWriter
from nova.context_processor.handlers.base import BaseHandler
from nova.context_processor.utils.file_utils import calculate_file_hash
from nova.context_processor.core.metadata import BaseMetadata
from nova.context_processor.core.metadata.models.types import MarkdownMetadata

# Configure logger
logger = logging.getLogger(__name__)


class MarkdownHandler(BaseHandler):
    """Handler for markdown files."""

    def __init__(self, config: ConfigManager) -> None:
        """Initialize markdown handler.

        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
        self.supported_extensions = {".md", ".markdown"}
        self.markdown_writer = MarkdownWriter()

    def _update_links(self, content: str, file_path: Path) -> str:
        """Update links in markdown content.

        Args:
            content: Markdown content to update
            file_path: Path to file being processed

        Returns:
            Updated markdown content
        """
        # Get parent directory of file
        parent_dir = file_path.parent

        # Find all links in content
        link_pattern = r'\[([^\]]*)\]\(([^)]*)\)'
        matches = re.finditer(link_pattern, content)

        # Process each link
        for match in matches:
            link_text = match.group(1)
            link_url = match.group(2)

            # Skip if it's an external link
            if link_url.startswith(('http://', 'https://', 'ftp://', 'mailto:')):
                continue

            # Convert to Path object
            link_path = Path(link_url)

            # If link is relative, make it absolute using parent directory
            if not link_path.is_absolute():
                link_path = (parent_dir / link_path).resolve()

            # Get relative path from input directory
            input_dir = Path(self.config.input_dir).resolve()
            try:
                rel_path = link_path.relative_to(input_dir)
            except ValueError:
                # If file is not under input directory, try to find a parent directory
                # that matches the input directory pattern
                for parent in link_path.parents:
                    if re.search(r"\d{8}", str(parent)):
                        # Use the path relative to this parent
                        remaining_path = link_path.relative_to(parent)
                        # Include the parent directory name in the relative path
                        rel_path = Path(parent.name) / remaining_path
                        break
                else:
                    # If no parent with date found, use just the filename
                    logger.warning(f"File {link_path} is not under input directory {input_dir}")
                    rel_path = Path(link_path.name)

            # Replace link with reference marker
            content = content.replace(
                match.group(0),
                f'[{link_text}]({rel_path})'
            )

        return content

    async def _extract_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Extract information from a markdown file.

        Args:
            file_path: Path to file

        Returns:
            Optional[Dict[str, Any]]: Markdown information if successful, None if failed
        """
        try:
            # Read markdown file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract basic information
            info = {
                "content": content,
                "line_count": len(content.splitlines()),
                "word_count": len(content.split()),
                "char_count": len(content),
                "has_frontmatter": content.startswith("---"),
                "has_links": bool(re.search(r'\[([^\]]*)\]\(([^)]*)\)', content)),
                "has_images": bool(re.search(r'!\[([^\]]*)\]\(([^)]*)\)', content)),
                "has_code_blocks": bool(re.search(r'```[^\n]*\n[\s\S]*?```', content)),
                "has_tables": bool(re.search(r'\|[^|]+\|[^|]+\|', content)),
                "has_math": bool(re.search(r'\$[^$]+\$', content)),
                "has_html": bool(re.search(r'<[^>]+>', content)),
            }

            return info

        except Exception as e:
            logger.error(f"Failed to extract markdown information: {str(e)}")
            return None

    async def _process_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Process a markdown file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether processing was successful
        """
        try:
            # Extract markdown information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.content = info["content"]
            metadata.line_count = info["line_count"]
            metadata.word_count = info["word_count"]
            metadata.char_count = info["char_count"]
            metadata.has_frontmatter = info["has_frontmatter"]
            metadata.has_links = info["has_links"]
            metadata.has_images = info["has_images"]
            metadata.has_code_blocks = info["has_code_blocks"]
            metadata.has_tables = info["has_tables"]
            metadata.has_math = info["has_math"]
            metadata.has_html = info["has_html"]

            return True

        except Exception as e:
            logger.error(f"Failed to process markdown {file_path}: {e}")
            return False

    async def _parse_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Parse a markdown file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether parsing was successful
        """
        try:
            # Extract markdown information
            info = await self._extract_info(file_path)
            if not info:
                return False

            # Update metadata
            metadata.content = info["content"]
            metadata.line_count = info["line_count"]
            metadata.word_count = info["word_count"]
            metadata.char_count = info["char_count"]
            metadata.has_frontmatter = info["has_frontmatter"]
            metadata.has_links = info["has_links"]
            metadata.has_images = info["has_images"]
            metadata.has_code_blocks = info["has_code_blocks"]
            metadata.has_tables = info["has_tables"]
            metadata.has_math = info["has_math"]
            metadata.has_html = info["has_html"]

            return True

        except Exception as e:
            logger.error(f"Failed to parse markdown {file_path}: {e}")
            return False

    async def _disassemble_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Disassemble a markdown file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether disassembly was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to disassemble markdown {file_path}: {e}")
            return False

    async def _split_file(self, file_path: Path, metadata: DocumentMetadata) -> bool:
        """Split a markdown file.

        Args:
            file_path: Path to file
            metadata: Metadata to update

        Returns:
            bool: Whether splitting was successful
        """
        try:
            # For now, just copy the file
            metadata.file_size = file_path.stat().st_size
            metadata.file_hash = calculate_file_hash(file_path)

            return True

        except Exception as e:
            logger.error(f"Failed to split markdown {file_path}: {e}")
            return False

    async def parse_file(self, file_path: Path) -> Optional[BaseMetadata]:
        """Parse a markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            Optional[BaseMetadata]: Metadata if successful, None if failed
        """
        try:
            # Create metadata
            metadata = MarkdownMetadata(
                file_path=str(file_path),
                file_name=file_path.name,
                file_type=file_path.suffix.lstrip('.'),
                file_size=file_path.stat().st_size,
                file_hash=calculate_file_hash(file_path),
                created_at=file_path.stat().st_ctime,
                modified_at=file_path.stat().st_mtime,
            )

            # Parse file
            if await self._parse_file(file_path, metadata):
                return metadata

            return None

        except Exception as e:
            logger.error(f"Failed to parse markdown {file_path}: {str(e)}")
            return None
