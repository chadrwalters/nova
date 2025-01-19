"""Chunking functionality for the vector store."""

import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A chunk of text with metadata."""

    text: str
    source: Path | None = None
    heading_text: str = ""
    heading_level: int = 0
    _tags: list[str] = field(default_factory=list)  # Internal list of tags
    _attachments: list[dict[str, str]] = field(
        default_factory=list
    )  # Internal list of attachment dicts
    chunk_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Initialize chunk ID if not provided."""
        if not self.chunk_id:
            self.chunk_id = str(uuid.uuid4())

    @property
    def tags(self) -> list[str]:
        """Get tags as a list."""
        return self._tags

    @tags.setter
    def tags(self, value: str | list[str]) -> None:
        """Set tags from either a comma-separated string or list."""
        if isinstance(value, str):
            self._tags = [t.strip() for t in value.split(",")] if value else []
        else:
            self._tags = list(value)

    @property
    def attachments(self) -> list[dict[str, str]]:
        """Get attachments as a list of dicts."""
        return self._attachments

    @attachments.setter
    def attachments(self, value: str | list[Any]) -> None:
        """Set attachments from either a comma-separated string or list.

        Args:
            value: Either a comma-separated string of 'type:path' pairs,
                  or a list of strings/dicts with type and path information.
        """
        self._attachments = []
        if isinstance(value, str) and value:
            # Parse string format "type:path,type:path"
            for att in value.split(","):
                type_, path = att.strip().split(":", 1)
                self._attachments.append({"type": type_, "path": path})
        elif isinstance(value, list):
            # Convert list items to dicts if needed
            for item in value:
                if isinstance(item, str):
                    type_, path = item.strip().split(":", 1)
                    self._attachments.append({"type": type_, "path": path})
                elif isinstance(item, dict):
                    self._attachments.append(
                        {
                            "type": str(item.get("type", "unknown")),
                            "path": str(item.get("path", "")),
                        }
                    )

    def add_tag(self, tag: str) -> None:
        """Add a tag to the chunk."""
        if tag not in self._tags:
            self._tags.append(tag)

    def add_attachment(self, attachment_type: str, path: str) -> None:
        """Add an attachment to the chunk."""
        attachment = {"type": attachment_type, "path": path}
        if attachment not in self._attachments:
            self._attachments.append(attachment)

    def to_metadata(self) -> dict:
        """Convert chunk metadata to a format suitable for ChromaDB."""
        # Generate a document ID from the source path if available
        doc_id = str(self.source) if self.source else self.chunk_id

        # Get document type from source extension or default to unknown
        doc_type = self.source.suffix[1:] if self.source else "unknown"

        # Get document size from source file if available
        doc_size = (
            self.source.stat().st_size if self.source and self.source.exists() else len(self.text)
        )

        return {
            "document_id": doc_id,
            "document_type": doc_type,
            "document_size": doc_size,
            "text": self.text,
            "date": None,  # Date will be set by the caller if available
            "tags": self._tags,
            "attachments": self._attachments,
            "heading_text": self.heading_text,
            "heading_level": self.heading_level,
            "chunk_id": self.chunk_id,
        }


class ChunkingEngine:
    """Handles text chunking with simplified logic."""

    def __init__(self, min_chunk_size: int = 50, max_chunk_size: int = 512):
        """Initialize the chunking engine.

        Args:
            min_chunk_size: Minimum size of a chunk in characters (default: 50)
            max_chunk_size: Maximum size of a chunk in characters (default: 512)
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.tag_pattern = re.compile(r"#([a-zA-Z][a-zA-Z0-9_/]*)")  # Must start with letter
        self.attachment_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def chunk_document(self, text: str, source: Path | None = None) -> list[Chunk]:
        """Chunk a document into smaller pieces."""
        if not text.strip():
            return []

        chunks = []
        lines = text.split("\n")
        current_chunk: list[str] = []
        current_size = 0
        current_heading = ""
        current_level = 0
        consecutive_headings: list[tuple[str, int]] = []  # Store both heading text and level

        def create_chunk_from_text(text_lines: list[str], heading: str, level: int) -> None:
            """Helper to create a chunk from text lines."""
            if not text_lines:
                return

            # Join text lines and split into smaller chunks if needed
            text_content = "\n".join(text_lines)
            if len(text_content) > self.max_chunk_size:
                # Split at sentence boundaries or line breaks
                sub_chunks = self._split_text(text_content)
                for sub_text in sub_chunks:
                    if len(sub_text) >= self.min_chunk_size or len(sub_text.strip()) > 0:
                        chunk = self._create_chunk(sub_text, heading, level)
                        chunk.source = source
                        self._parse_tags(sub_text, chunk)
                        self._parse_attachments(sub_text, chunk)
                        chunks.append(chunk)
            else:
                chunk = self._create_chunk(text_content, heading, level)
                chunk.source = source
                self._parse_tags(text_content, chunk)
                self._parse_attachments(text_content, chunk)
                chunks.append(chunk)

        for line in lines:
            line = line.rstrip()

            # Handle headings
            if line.startswith("#"):
                # Get heading info
                heading, level = self._parse_heading(line)

                # If we have consecutive headings, store them
                if not current_chunk:
                    consecutive_headings.append((heading, level))
                    continue

                # Save current chunk if it exists
                if current_chunk:
                    create_chunk_from_text(current_chunk, current_heading, current_level)
                    current_chunk = []
                    current_size = 0
                    consecutive_headings = [(heading, level)]

                # Start new chunk with heading
                current_heading = heading
                current_level = level
                current_chunk = [line]
                current_size = len(line) + 1  # +1 for newline
                continue

            # If we have consecutive headings and now got content, create a single chunk
            if consecutive_headings and line:
                # Use the last heading as the main heading
                current_heading, current_level = consecutive_headings[-1]
                # Include all headings in the chunk
                current_chunk = [f"{'#' * h[1]} {h[0]}" for h in consecutive_headings]
                current_chunk.append(line)
                current_size = sum(len(l) + 1 for l in current_chunk)
                consecutive_headings = []
                continue

            # Handle normal lines
            if line:
                # Check if adding this line would exceed max size
                if current_size + len(line) + 1 > self.max_chunk_size and current_chunk:
                    create_chunk_from_text(current_chunk, current_heading, current_level)
                    current_chunk = [line]
                    current_size = len(line) + 1
                else:
                    current_chunk.append(line)
                    current_size += len(line) + 1  # +1 for newline

        # Handle remaining text
        if current_chunk:
            create_chunk_from_text(current_chunk, current_heading, current_level)
        elif consecutive_headings:  # Handle remaining consecutive headings
            # Use the last heading as the main heading
            current_heading, current_level = consecutive_headings[-1]
            # Include all headings in the chunk
            create_chunk_from_text(
                [f"{'#' * h[1]} {h[0]}" for h in consecutive_headings],
                current_heading,
                current_level,
            )

        # If no chunks were created, create one from the entire text
        if not chunks and text.strip():
            chunk = self._create_chunk(text.strip(), "", 0)
            chunk.source = source
            self._parse_tags(text.strip(), chunk)
            self._parse_attachments(text.strip(), chunk)
            chunks.append(chunk)

        return chunks

    def _create_chunk(self, text: str, heading: str, level: int) -> Chunk:
        """Create a chunk with metadata."""
        chunk = Chunk(text=text, heading_text=heading, heading_level=level)
        return chunk

    def _parse_heading(self, line: str) -> tuple[str, int]:
        """Parse heading text and level from a line."""
        match = re.match(r"^(#+)\s*(.*)$", line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            return text, level
        return "", 0

    def _parse_tags(self, text: str, chunk: Chunk) -> None:
        """Parse tags from text and add them to the chunk."""
        # Find all tags in the text
        matches = self.tag_pattern.finditer(text)
        tags = set()  # Use a set to avoid duplicates

        for match in matches:
            tag = match.group(1)
            # Only add valid tags (no special characters or numbers at start)
            if tag and not re.match(r"^[0-9#@/]", tag):
                # Handle hierarchical tags
                if "/" in tag:
                    # Only add the full hierarchical tag
                    tags.add(tag)
                else:
                    tags.add(tag)

        # Add tags to chunk
        chunk._tags = sorted(tags)  # Sort for consistent ordering

    def _parse_attachments(self, text: str, chunk: Chunk) -> None:
        """Parse attachments from text and add them to the chunk."""
        # Find all attachments in the text
        matches = self.attachment_pattern.finditer(text)
        attachments = []

        for match in self.attachment_pattern.finditer(text):
            title = match.group(1)
            path = match.group(2)

            # Determine type based on extension
            ext = Path(path).suffix.lower()
            type_ = "image"  # Default to image

            # Map common extensions to types
            if ext in {".mp4", ".mov", ".avi", ".webm"}:
                type_ = "video"
            elif ext in {".mp3", ".wav", ".m4a", ".ogg"}:
                type_ = "audio"
            elif ext in {".pdf", ".doc", ".docx", ".txt"}:
                type_ = "document"

            # Add to attachments list
            attachments.append({"type": type_, "path": path})

        # Add attachments to chunk
        chunk._attachments = attachments

    def _split_text(self, text: str) -> list[str]:
        """Split text into smaller chunks at sentence boundaries or line
        breaks.
        """
        # First try to split at sentence boundaries
        sentences = re.split(r"([.!?]+\s+)", text)
        chunks = []
        current_chunk: list[str] = []
        current_size = 0

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # Add the delimiter back
            sentence_size = len(sentence)

            # If sentence is too large, split at line breaks
            if sentence_size > self.max_chunk_size:
                # First add current chunk if it exists
                if current_chunk:
                    chunk_text = "".join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)
                    current_chunk = []
                    current_size = 0

                # Split sentence at line breaks
                for line in sentence.split("\n"):
                    line_size = len(line) + 1  # +1 for newline
                    if line_size > self.max_chunk_size:
                        # If line is too large, split at word boundaries
                        words = line.split()
                        line_chunk: list[str] = []
                        line_size = 0
                        for word in words:
                            word_size = len(word) + 1  # +1 for space
                            if line_size + word_size > self.max_chunk_size and line_chunk:
                                chunk_text = " ".join(line_chunk)
                                if len(chunk_text) >= self.min_chunk_size:
                                    chunks.append(chunk_text)
                                line_chunk = [word]
                                line_size = word_size
                            else:
                                line_chunk.append(word)
                                line_size += word_size
                        if line_chunk:
                            chunk_text = " ".join(line_chunk)
                            if len(chunk_text) >= self.min_chunk_size:
                                chunks.append(chunk_text)
                    else:
                        if len(line) >= self.min_chunk_size:
                            chunks.append(line)
            else:
                # If adding this sentence would exceed max size, create new chunk
                if current_size + sentence_size > self.max_chunk_size and current_chunk:
                    chunk_text = "".join(current_chunk)
                    if len(chunk_text) >= self.min_chunk_size:
                        chunks.append(chunk_text)
                    current_chunk = [sentence]
                    current_size = sentence_size
                else:
                    current_chunk.append(sentence)
                    current_size += sentence_size

        # Add remaining chunk
        if current_chunk:
            chunk_text = "".join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)

        return chunks
