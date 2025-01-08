"""Markdown file handler."""

# Standard library
import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Match, Optional, Union, Tuple

# Internal imports
from ..config.manager import ConfigManager
from ..core.markdown import MarkdownWriter
from ..core.metadata import DocumentMetadata
from .base import BaseHandler, ProcessingResult, ProcessingStatus

# Configure logger
logger = logging.getLogger(__name__)


class MarkdownHandler(BaseHandler):
    """Handler for markdown files."""

    name = "markdown"
    version = "0.1.0"
    file_types = ["md", "markdown"]

    def __init__(self, config: ConfigManager) -> None:
        """Initialize markdown handler.

        Args:
            config: Nova configuration manager.
        """
        super().__init__(config)
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

    async def process_file_impl(
        self, file_path: Union[str, Path], output_path: Union[str, Path], metadata: DocumentMetadata
    ) -> Optional[DocumentMetadata]:
        """Process a markdown file.

        Args:
            file_path: Path to file to process
            output_path: Path to write output to
            metadata: Metadata for file

        Returns:
            DocumentMetadata if successful, None if failed
        """
        # Convert to Path objects and resolve
        file_path = Path(file_path).resolve()
        output_path = Path(output_path).resolve()

        try:
            # Read markdown file
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Process embedded documents
            content, embedded_files = await self._process_embedded_documents(content, file_path)
            
            # Store embedded files in metadata but don't process them separately
            metadata.embedded_files = embedded_files
            metadata.metadata["embedded_files"] = [str(f) for f in embedded_files]

            # Update links in content
            content = self._update_links(content, file_path)

            # Ensure parent directories exist
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            # Update metadata
            metadata.processed = True
            metadata.output_path = output_path
            metadata.content_type = "text/markdown"

            return metadata

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            return None

    async def _process_embedded_documents(
        self, content: str, file_path: Path
    ) -> Tuple[str, List[Path]]:
        """Process embedded documents in markdown content.

        Args:
            content: Markdown content to process
            file_path: Path to file being processed

        Returns:
            Tuple of (updated content, list of embedded file paths)
        """
        # Get parent directory of file
        parent_dir = file_path.parent

        # Find all embedded documents and attachments
        embed_pattern = r'\[([^\]]*)\]\(([^)]*)\)\s*(?:<!--\s*{"embed":\s*"true"[^}]*}\s*-->)?'
        matches = list(re.finditer(embed_pattern, content))
        embedded_files = []

        # Process each embedded document or attachment
        for match in matches:
            link_text = match.group(1)
            link_url = match.group(2)
            is_embed = '{"embed": "true"}' in (match.group(0) if len(match.groups()) > 2 else '')

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

            # Add to list of embedded files
            embedded_files.append(rel_path)

            # If this is an embedded document, try to embed its content
            if is_embed:
                try:
                    with open(link_path, "r", encoding="utf-8") as f:
                        embedded_content = f.read()
                        
                    # Create a section for the embedded content
                    section = f"\n\n## Embedded Document: {link_text}\n\n{embedded_content}\n\n"
                    
                    # Replace the embed marker with the actual content
                    content = content.replace(match.group(0), section)
                except Exception as e:
                    logger.error(f"Failed to embed document {link_path}: {str(e)}")
                    # Keep the original link if we can't embed
                    content = content.replace(
                        match.group(0),
                        f'[{link_text}]({rel_path}) (Failed to embed: {str(e)})'
                    )
            else:
                # This is a regular attachment, just update the link path
                content = content.replace(
                    match.group(0),
                    f'[{link_text}]({rel_path})'
                )

        return content, embedded_files
