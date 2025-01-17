"""Chunking functionality for the vector store."""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of text with essential metadata."""

    text: str
    source: Path | None = None
    heading_text: str = ""
    heading_level: int = 0
    tags: list[str] = field(default_factory=list)
    attachments: list[dict[str, str]] = field(
        default_factory=list
    )  # Simple dict with type and path only
    chunk_id: str = ""  # Will be set by the store

    def add_tag(self, tag: str) -> None:
        """Add a tag if it doesn't exist."""
        if tag not in self.tags:
            self.tags.append(tag)
            logger.debug(f"Added tag: {tag}")

    def add_attachment(self, type_: str, path: str) -> None:
        """Add a simple attachment with type and path."""
        self.attachments.append({"type": type_, "path": path})
        logger.debug(f"Added attachment: type={type_}, path={path}")


class ChunkingEngine:
    """Handles text chunking with simplified logic."""

    def __init__(self, min_chunk_size: int = 100, max_chunk_size: int = 512):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk_document(self, text: str, source: Path | None = None) -> list[Chunk]:
        """Chunk a document into smaller pieces."""
        if not text.strip():
            return []

        chunks = []
        lines = text.split("\n")
        current_chunk = []
        current_size = 0
        current_heading = ""
        current_level = 0

        def create_chunk_from_text(text_lines: list[str], heading: str, level: int) -> None:
            """Helper to create a chunk from text lines."""
            if text_lines:
                chunk_text = "\n".join(text_lines).strip()
                if chunk_text:
                    # Split if still too large
                    if len(chunk_text) > self.max_chunk_size:
                        words = chunk_text.split()
                        temp_chunk = []
                        temp_size = 0

                        for word in words:
                            if temp_size + len(word) + 1 > self.max_chunk_size and temp_chunk:
                                chunk = self._create_chunk(" ".join(temp_chunk), heading, level)
                                chunk.source = source
                                chunks.append(chunk)
                                temp_chunk = []
                                temp_size = 0
                            temp_chunk.append(word)
                            temp_size += len(word) + 1

                        if temp_chunk:
                            chunk = self._create_chunk(" ".join(temp_chunk), heading, level)
                            chunk.source = source
                            chunks.append(chunk)
                    else:
                        chunk = self._create_chunk(chunk_text, heading, level)
                        chunk.source = source
                        chunks.append(chunk)

        for line in lines:
            line = line.rstrip()

            # Handle headings
            if line.startswith("#"):
                # Save current chunk if it exists
                create_chunk_from_text(current_chunk, current_heading, current_level)
                current_chunk = []
                current_size = 0

                # Update heading
                current_heading, current_level = self._parse_heading(line)
                continue

            # Handle normal lines
            new_size = current_size + len(line) + 1  # +1 for newline
            if new_size > self.max_chunk_size and current_chunk:
                create_chunk_from_text(current_chunk, current_heading, current_level)
                current_chunk = []
                current_size = 0

            current_chunk.append(line)
            current_size = current_size + len(line) + 1

        # Add final chunk if it exists
        create_chunk_from_text(current_chunk, current_heading, current_level)

        return chunks

    def _parse_tags(self, text: str) -> list[str]:
        """Parse tags from text."""
        tags = []
        # Match hashtags followed by word characters and optional hierarchy
        pattern = (
            r"#([a-zA-Z][\w/]*)"  # Match hashtags starting with a letter, allowing forward slashes
        )
        matches = re.finditer(pattern, text)

        for match in matches:
            tag = match.group(1)
            # Remove trailing punctuation
            tag = tag.rstrip(".,!?")
            if tag and "@" not in tag:  # Exclude email-like tags
                tags.append(tag)

        return list(set(tags))

    def _parse_heading(self, text: str) -> tuple[str, int]:
        """Parse heading text and level."""
        level = len(text) - len(text.lstrip("#"))
        heading = text.lstrip("# ").strip()
        return heading, level

    def _create_chunk(
        self,
        text: str,
        heading_text: str = "",
        heading_level: int = 0,
    ) -> Chunk:
        """Create a chunk with metadata."""
        tags = self._parse_tags(text)
        attachments = self._parse_attachments(text)
        return Chunk(
            text=text.strip(),
            heading_text=heading_text,
            heading_level=heading_level,
            tags=tags,
            attachments=attachments,
        )

    def _parse_attachments(self, text: str) -> list[dict[str, str]]:
        """Parse attachments from text."""
        attachments = []
        # Match Markdown image syntax: ![alt](path)
        pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        matches = re.findall(pattern, text)
        for _, path in matches:
            attachments.append({"type": "image", "path": path})
        return attachments
