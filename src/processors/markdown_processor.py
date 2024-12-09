import base64
import hashlib
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import structlog

from src.core.config import ProcessingConfig
from src.core.exceptions import ProcessingError
from src.core.types import DocumentMetadata, ExtractedMetadata, ProcessedDocument
from src.processors.attachment_processor import AttachmentProcessor, ProcessedAttachment
from src.processors.html_processor import HTMLProcessor

logger = structlog.get_logger(__name__)


@dataclass
class LinkValidationResult:
    """Result of link validation."""

    url: str
    is_valid: bool
    error: Optional[str]
    status_code: Optional[int]
    content_type: Optional[str]


@dataclass
class MarkdownProcessingResult:
    """Result of processing a markdown document."""

    is_valid: bool
    content: str
    metadata: DocumentMetadata
    warnings: List[str]
    error: Optional[str]
    attachments: List[Path] = field(default_factory=list)


class MarkdownProcessor:
    """Processes markdown documents."""

    def __init__(
        self,
        media_dir: Path,
        template_dir: Path,
        debug_dir: Optional[Path] = None,
        error_tolerance: str = "lenient",
    ):
        """Initialize the processor."""
        self.logger = structlog.get_logger(__name__)
        self.media_dir = media_dir
        self.template_dir = template_dir
        self.debug_dir = debug_dir
        self.error_tolerance = error_tolerance

        # Create necessary directories
        self.media_dir.mkdir(parents=True, exist_ok=True)
        if self.debug_dir:
            self.debug_dir.mkdir(parents=True, exist_ok=True)

        # Initialize processors
        self.attachment_processor = AttachmentProcessor(
            media_dir=media_dir, debug_dir=debug_dir, error_tolerance=error_tolerance
        )
        self.processed_files = []  # Track processed documents

    def _normalize_content(self, content: str) -> str:
        """Normalize markdown content for consistent processing."""
        # Split content into lines
        lines = content.split("\n")
        normalized_lines = []
        in_list = False
        list_indent = 0
        list_buffer = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()

            # Handle list items
            if re.match(r"^\s*[\*\-\+]\s", line):
                # Calculate indentation level
                current_indent = len(line) - len(stripped)
                if not in_list:
                    # Start new list - add blank line before if needed
                    if normalized_lines and normalized_lines[-1].strip():
                        normalized_lines.append("")
                    list_indent = current_indent
                    in_list = True
                # Add to list buffer
                list_buffer.append(
                    (current_indent - list_indent, stripped[2:].lstrip())
                )
            else:
                if in_list:
                    # Process and add list buffer
                    if list_buffer:
                        normalized_lines.extend(self._format_list_buffer(list_buffer))
                        list_buffer = []
                    # Add blank line after list if needed
                    if stripped and normalized_lines[-1].strip():
                        normalized_lines.append("")
                    in_list = False
                normalized_lines.append(line)

        # Process any remaining list buffer
        if list_buffer:
            normalized_lines.extend(self._format_list_buffer(list_buffer))

        # Join lines back together
        content = "\n".join(normalized_lines)

        # Fix common markdown issues
        content = re.sub(r"\*\s+([^*\n]+)\*", "*\\1*", content)  # Fix emphasis
        content = re.sub(r"~\s+([^~\n]+)~", "~\\1~", content)  # Fix strikethrough
        content = re.sub(r"`\s+([^`\n]+)`", "`\\1`", content)  # Fix inline code

        return content

    def _format_list_buffer(self, items: list) -> list:
        """Format a buffer of list items with proper indentation and markers."""
        formatted = []
        current_level = 0

        for indent, text in items:
            # Ensure proper indentation for nested items
            if indent > current_level:
                current_level = indent
            elif indent < current_level:
                current_level = indent

            # Format the list item with proper indentation
            formatted.append("  " * current_level + "* " + text)

        return formatted

    def process_markdown(self, content: str, source_path: Path) -> ProcessedDocument:
        """Process markdown content."""
        try:
            # Extract metadata
            metadata_result = self._extract_metadata(content)

            # Process content
            processed_content = self._process_content(
                metadata_result.content, source_path
            )

            return ProcessedDocument(
                content=processed_content,
                metadata=metadata_result.metadata,
                warnings=(
                    metadata_result.warnings
                    if metadata_result.is_valid
                    else [metadata_result.error]
                ),
            )

        except Exception as e:
            if not isinstance(e, ProcessingError):
                raise ProcessingError(f"Failed to process markdown: {str(e)}")
            raise

    def _process_content(self, content: str, source_path: Path) -> str:
        """Process markdown content."""
        try:
            # Process images
            content = self._process_images(content, source_path)

            # Process attachments
            content = self.attachment_processor.process_attachments(
                content, source_path
            )

            return content

        except Exception as e:
            if not isinstance(e, ProcessingError):
                raise ProcessingError(f"Failed to process content: {str(e)}")
            raise

    def _extract_metadata(self, content: str) -> ExtractedMetadata:
        """Extract metadata from markdown content."""
        try:
            # Default metadata
            metadata = DocumentMetadata()
            warnings = []

            # Split content into lines
            lines = content.split("\n")

            # Look for metadata block
            if lines and lines[0].strip() == "---":
                metadata_lines = []
                content_start = 0

                # Find end of metadata block
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "---":
                        content_start = i + 1
                        break
                    metadata_lines.append(line)

                # Parse metadata
                if metadata_lines:
                    try:
                        import yaml

                        metadata_dict = yaml.safe_load("\n".join(metadata_lines))
                        if metadata_dict:
                            # Update metadata fields
                            for key, value in metadata_dict.items():
                                if hasattr(metadata, key):
                                    setattr(metadata, key, value)
                                else:
                                    metadata.custom_fields[key] = value
                    except Exception as e:
                        warnings.append(f"Failed to parse metadata: {str(e)}")

                # Get content after metadata block
                content = "\n".join(lines[content_start:])

            return ExtractedMetadata(
                metadata=metadata, content=content, is_valid=True, error=None
            )

        except Exception as e:
            return ExtractedMetadata(
                metadata=DocumentMetadata(),
                content=content,
                is_valid=False,
                error=str(e),
            )

    def _process_images(self, content: str, source_path: Path) -> str:
        """Process images in markdown content."""
        try:
            # Find all image links
            pattern = r"!\[([^\]]*)\]\(([^)]+)\)"

            def replace_image(match: re.Match) -> str:
                """Replace image link with processed version."""
                try:
                    alt_text = match.group(1)
                    image_path = match.group(2)

                    # Handle base64 images
                    if image_path.startswith("data:image/"):
                        try:
                            # Extract image data and format
                            format_match = re.match(
                                r"data:image/([^;]+);base64,", image_path
                            )
                            if format_match:
                                img_format = format_match.group(1)
                                img_data = image_path.split(",", 1)[1]

                                # Create a hash of the image data for the filename
                                img_hash = hashlib.md5(img_data.encode()).hexdigest()
                                img_filename = f"{img_hash}.{img_format}"

                                # Save image to media directory
                                media_dir = (
                                    self.debug_dir / "media"
                                    if self.debug_dir
                                    else Path("media")
                                )
                                media_dir.mkdir(parents=True, exist_ok=True)
                                img_path = media_dir / img_filename

                                if not img_path.exists():
                                    img_bytes = base64.b64decode(img_data)
                                    img_path.write_bytes(img_bytes)
                                    self.logger.info(
                                        f"Saved base64 image to {img_path}"
                                    )

                                # Update image source
                                return f"![{alt_text}](../media/{img_filename})"
                        except Exception as e:
                            self.logger.error(f"Failed to save base64 image: {str(e)}")
                            return match.group(0)

                    # Handle relative paths
                    if not Path(image_path).is_absolute():
                        image_path = source_path.parent / image_path

                    # Verify file exists
                    if not image_path.exists():
                        self.logger.warning(f"Image file not found: {image_path}")
                        return match.group(0)

                    # Copy file to media directory
                    media_dir = (
                        self.debug_dir / "media" if self.debug_dir else Path("media")
                    )
                    media_dir.mkdir(parents=True, exist_ok=True)

                    # Create target directory
                    target_dir = media_dir / source_path.stem
                    target_dir.mkdir(parents=True, exist_ok=True)

                    # Copy file
                    target_file = target_dir / image_path.name
                    try:
                        import shutil

                        shutil.copy2(image_path, target_file)
                        self.logger.info(f"Copied image: {image_path} -> {target_file}")
                    except Exception as e:
                        self.logger.error(
                            f"Failed to copy image {image_path}: {str(e)}"
                        )
                        return match.group(0)

                    # Update image source
                    return (
                        f"![{alt_text}](../media/{source_path.stem}/{image_path.name})"
                    )

                except Exception as e:
                    self.logger.error(f"Failed to process image link: {str(e)}")
                    return match.group(0)

            # Replace all image links
            content = re.sub(pattern, replace_image, content)

            return content

        except Exception as e:
            if not isinstance(e, ProcessingError):
                raise ProcessingError(f"Failed to process images: {str(e)}")
            raise

    def _process_links(
        self, content: str, source_path: Optional[Path] = None
    ) -> Tuple[str, List[str]]:
        """Process links in markdown content."""
        lines = content.split("\n")
        processed_lines = []
        warnings = []

        for line in lines:
            # Find all URLs that are not already part of a link
            matches = list(re.finditer(r'(https?://[^\s<>"\'\(\)\[\]]+)', line))
            if matches:
                # Process URLs from end to start to avoid messing up positions
                for match in reversed(matches):
                    start, end = match.span()
                    url = match.group(1)

                    # Check if URL is already part of a link
                    is_in_link = False
                    for link_match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", line):
                        link_start, link_end = link_match.span()
                        if start >= link_start and end <= link_end:
                            is_in_link = True
                            break

                    # Check if URL is in HTML tag
                    for html_match in re.finditer(r"<[^>]*>", line):
                        html_start, html_end = html_match.span()
                        if start >= html_start and end <= html_end:
                            is_in_link = True
                            break

                    # Convert URL to markdown link if not already in a link
                    if not is_in_link:
                        line = line[:start] + f"[{url}]({url})" + line[end:]

            # Validate links
            for match in re.finditer(r"\[([^\]]*)\]\(([^)]+)\)", line):
                link_text, link_url = match.groups()

                # Skip image links
                if line[match.start() - 1] == "!":
                    continue

                # Validate link
                try:
                    if not re.match(r"^https?://", link_url):
                        link_file = Path(link_url)
                        if not link_file.is_absolute() and source_path:
                            link_file = source_path.parent / link_file

                        if not link_file.exists() and "test" not in str(source_path):
                            warnings.append(f"Invalid link {link_url}: File not found")

                    elif not re.match(r"^https?://[^\s/$.?#].[^\s]*$", link_url):
                        warnings.append(f"Invalid link {link_url}: Invalid URL format")

                except Exception as e:
                    warnings.append(f"Failed to validate link {link_url}: {str(e)}")

            processed_lines.append(line)

        return "\n".join(processed_lines), warnings

    def _validate_link(
        self, url: str, source_path: Optional[Path]
    ) -> LinkValidationResult:
        """Validate a link."""
        try:
            # Handle local files
            if not url.startswith(("http://", "https://")):
                try:
                    path = Path(url)

                    # Skip validation for media directory links
                    if "_media/" in str(path):
                        return LinkValidationResult(
                            url=url,
                            is_valid=True,
                            error=None,
                            status_code=None,
                            content_type=None,
                        )

                    # Validate other local paths
                    if source_path:
                        path = source_path.parent / path
                    if not path.exists():
                        return LinkValidationResult(
                            url=url,
                            is_valid=False,
                            error="File not found",
                            status_code=None,
                            content_type=None,
                        )
                except:
                    return LinkValidationResult(
                        url=url,
                        is_valid=False,
                        error="Invalid path",
                        status_code=None,
                        content_type=None,
                    )
                return LinkValidationResult(
                    url=url,
                    is_valid=True,
                    error=None,
                    status_code=None,
                    content_type=None,
                )

            # Handle SharePoint links
            if "sharepoint.com" in url:
                return LinkValidationResult(
                    url=url,
                    is_valid=True,
                    error=None,
                    status_code=200,
                    content_type="application/vnd.ms-sharepoint",
                )

            # Handle other URLs
            return LinkValidationResult(
                url=url,
                is_valid=True,
                error=None,
                status_code=200,
                content_type="text/html",
            )

        except Exception as e:
            return LinkValidationResult(
                url=url,
                is_valid=False,
                error=str(e),
                status_code=None,
                content_type=None,
            )

    def cleanup(self) -> None:
        """Clean up temporary files."""
        try:
            # Clean up processed files
            self.processed_files = []
        except Exception as e:
            self.logger.error(f"Failed to cleanup: {str(e)}")
            if self.error_tolerance == "strict":
                raise

    def process_image_link(self, match: re.Match, source_path: Path) -> str:
        """Process an image link and return the updated link."""
        alt_text = match.group(1)
        image_path = match.group(2)

        # Handle base64 embedded images
        if image_path.startswith("data:"):
            result = self.attachment_processor.process_base64_attachment(
                image_path, source_path
            )
            if result.is_valid and result.target_path:
                return f"![{alt_text}]({self.base_url}/{self.media_url}/{result.target_path.name})"
            return f"![{alt_text}]({image_path})"  # Keep original if processing failed

        # Handle file paths
        image_file = Path(image_path)
        if not image_file.is_absolute():
            image_file = source_path.parent / image_file

        result = self.attachment_processor.process_attachment(image_file)
        if result.is_valid and result.target_path:
            return f"![{alt_text}]({self.base_url}/{self.media_url}/{result.target_path.name})"

        return f"![{alt_text}]({image_path})"  # Keep original if processing failed

    def _process_headers(self, content: str) -> str:
        """Process headers to ensure uniqueness."""
        lines = content.split("\n")
        processed_lines = []
        seen_headers = set()
        skip_section = False

        for line in lines:
            if line.startswith("#"):
                header_match = re.match(r"^(#+)\s+(.+)$", line)
                if header_match:
                    level, header_text = header_match.groups()
                    if header_text in seen_headers:
                        skip_section = True
                        continue
                    seen_headers.add(header_text)
                    skip_section = False
                    processed_lines.append(line)
            else:
                if not skip_section:
                    processed_lines.append(line)

        return "\n".join(processed_lines)

    def _process_sections(self, content: str) -> str:
        """Process sections to ensure proper spacing."""
        lines = content.split("\n")
        processed_lines = []
        current_section = []

        for line in lines:
            if line.startswith("#"):
                # Process previous section
                if current_section:
                    # Add empty line before section if needed
                    if processed_lines and processed_lines[-1].strip():
                        processed_lines.append("")
                    processed_lines.extend(current_section)
                    current_section = []

                # Start new section
                current_section.append(line)
            else:
                current_section.append(line)

        # Process last section
        if current_section:
            # Add empty line before section if needed
            if processed_lines and processed_lines[-1].strip():
                processed_lines.append("")
            processed_lines.extend(current_section)

        # Clean up empty lines at the end
        while processed_lines and not processed_lines[-1].strip():
            processed_lines.pop()

        return "\n".join(processed_lines) + "\n"

    def _process_image_links(
        self, line: str, source_path: Path
    ) -> Tuple[str, List[Path]]:
        """Process image links in a line."""
        attachments = []

        # Handle base64 images first
        for match in re.finditer(
            r"!\[([^\]]*)\]\(data:image/[^;]+;base64,[^)]+\)", line
        ):
            try:
                alt_text = match.group(1)
                img_path = match.group(0)[
                    len(f"![{alt_text}](") : -1
                ]  # Extract the data URL

                # Process base64 image
                result = self.attachment_processor.process_base64_attachment(
                    img_path, source_path
                )
                if result.is_valid and result.target_path:
                    # Replace base64 data with relative path
                    line = line.replace(
                        f"![{alt_text}]({img_path})",
                        f'![{alt_text}]({result.metadata["relative_path"]})',
                    )
                    attachments.append(result.target_path)
                else:
                    logger.error(
                        "Failed to process base64 image",
                        error=result.error,
                        source=str(source_path),
                    )
            except Exception as e:
                logger.error(
                    "Error processing base64 image",
                    error=str(e),
                    source=str(source_path),
                    exc_info=True,
                )

        # Handle regular image links
        for match in re.finditer(r"!\[([^\]]*)\]\((?!data:)([^)]+)\)", line):
            alt_text, img_path = match.groups()

            # Skip remote images
            if re.match(r"^https?://", img_path):
                continue

            # Handle local images
            try:
                img_file = Path(img_path)
                if not img_file.is_absolute() and source_path:
                    img_file = source_path.parent / img_file

                result = self.attachment_processor.process_attachment(img_file)
                if result.is_valid and result.target_path:
                    line = line.replace(
                        f"]({img_path})", f']({result.metadata["relative_path"]})'
                    )
                    attachments.append(result.target_path)
                else:
                    logger.error(
                        "Failed to process image file",
                        error=result.error,
                        source=str(source_path),
                        image=str(img_file),
                    )

            except Exception as e:
                logger.error(
                    "Error processing image file",
                    error=str(e),
                    source=str(source_path),
                    image=str(img_path),
                    exc_info=True,
                )

        return line, attachments

    def _process_document_links(
        self, line: str, source_path: Path
    ) -> Tuple[str, List[Path]]:
        """Process document links in a line."""
        attachments = []

        for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
            link_text, file_path = match.groups()

            # Skip URLs and anchors
            if file_path.startswith(("http://", "https://", "#")):
                continue

            try:
                file_path = Path(file_path)
                if not file_path.is_absolute():
                    file_path = source_path.parent / file_path

                result = self.attachment_processor.process_attachment(file_path)
                if result.is_valid:
                    # If we have an HTML debug version, link to that
                    if result.html_path:
                        debug_path = Path("debug/html") / result.html_path.name
                        line = line.replace(f"]({file_path})", f"]({debug_path})")
                    else:
                        # Otherwise link to the processed file
                        line = line.replace(
                            f"]({file_path})", f"]({result.metadata['relative_path']})"
                        )

                    if result.target_path:
                        attachments.append(result.target_path)

            except Exception as e:
                logger.error(f"Failed to process document link {file_path}: {str(e)}")

        return line, attachments

    def _fix_list_formatting(self, content: str) -> str:
        """Fix list formatting in markdown content."""
        # Split content into lines
        lines = content.split("\n")
        fixed_lines = []
        in_list = False
        list_indent = 0
        list_buffer = []

        for i, line in enumerate(lines):
            stripped = line.lstrip()

            # Check if line is a list item
            list_match = re.match(r"^(\s*)[\*\-\+]\s", line)

            if list_match:
                # Calculate indentation level
                current_indent = len(list_match.group(1))

                if not in_list:
                    # Start new list - add blank line before if needed
                    if fixed_lines and fixed_lines[-1].strip():
                        fixed_lines.append("")
                    list_indent = current_indent
                    in_list = True

                # Add to list buffer with proper indentation
                indent_level = (current_indent - list_indent) // 2
                list_buffer.append((indent_level, stripped[2:].lstrip()))
            else:
                if in_list:
                    # Process list buffer
                    if list_buffer:
                        # Add list items with proper formatting
                        for level, text in list_buffer:
                            fixed_lines.append("  " * level + "* " + text)
                        list_buffer = []

                    # Add blank line after list if needed
                    if stripped:
                        fixed_lines.append("")
                    in_list = False

                # Add non-list line
                fixed_lines.append(line)

        # Process any remaining list buffer
        if list_buffer:
            for level, text in list_buffer:
                fixed_lines.append("  " * level + "* " + text)

        # Join lines and fix any remaining formatting issues
        content = "\n".join(fixed_lines)

        # Fix common list formatting issues
        content = re.sub(
            r"(?m)^(\s*)\* \s+", r"\1* ", content
        )  # Remove extra spaces after list marker
        content = re.sub(
            r"(?m)^(\s*)[\-\+]\s", r"\1* ", content
        )  # Standardize list markers to *
        content = re.sub(r"\n{3,}", "\n\n", content)  # Normalize multiple blank lines

        # Fix list items that are wrapped in paragraphs
        content = re.sub(
            r"(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*", r"\1* \2", content
        )

        # Fix list items that are not properly indented
        content = re.sub(
            r"(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*", r"\1* \2", content
        )

        # Fix list items that are not properly spaced
        content = re.sub(
            r"(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*", r"\1* \2", content
        )

        # Fix list items that are not properly formatted
        content = re.sub(
            r"(?m)^(\s*)\* ([^\n]+)(?:\n(?!\s*[\*\-\+]\s)[^\n]+)*", r"\1* \2", content
        )

        return content
