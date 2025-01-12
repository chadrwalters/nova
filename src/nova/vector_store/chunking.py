"""Chunking engine for text processing."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Text chunk with metadata."""

    text: str
    source: Path | None = None
    heading_context: str = ""
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class ChunkingEngine:
    """Engine for splitting text into semantic chunks."""

    def chunk_document(self, text: str, source: Path | None = None) -> list[Chunk]:
        """Split document into semantic chunks.

        Args:
            text: Document text
            source: Optional source path

        Returns:
            List of chunks
        """
        # Split by headings first
        heading_chunks = self._split_by_headings(text)

        # Then split each heading chunk into semantic chunks
        chunks: list[Chunk] = []
        for heading, content in heading_chunks:
            semantic_chunks = self._split_semantic_content(content)
            for chunk_text in semantic_chunks:
                chunks.append(
                    Chunk(text=chunk_text, source=source, heading_context=heading)
                )

        return chunks

    def _split_by_headings(self, text: str) -> list[tuple[str, str]]:
        """Split text by markdown headings.

        Args:
            text: Text to split

        Returns:
            List of (heading, content) tuples
        """
        chunks: list[tuple[str, str]] = []
        current_heading = ""
        current_content: list[str] = []

        for line in text.split("\n"):
            if line.startswith("#"):
                # Save previous chunk if it exists
                if current_content:
                    chunks.append((current_heading, "\n".join(current_content)))
                    current_content = []

                # Extract new heading
                current_heading = line.lstrip("#").strip()
            else:
                current_content.append(line)

        # Add final chunk
        if current_content:
            chunks.append((current_heading, "\n".join(current_content)))

        return chunks

    def _split_semantic_content(self, text: str) -> list[str]:
        """Split content into semantic chunks.

        Args:
            text: Text to split

        Returns:
            List of chunk texts
        """
        # For now, just split by paragraphs
        chunks: list[str] = []
        current_chunk: list[str] = []

        for line in text.split("\n"):
            if not line.strip():
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
            else:
                current_chunk.append(line)

        # Add final chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks
