"""Chunking engine for Nova vector store.

This module implements a hybrid chunking strategy that combines heading-
based segmentation with semantic content splitting for optimal RAG
retrieval.
"""
from dataclasses import dataclass
import re


@dataclass
class Chunk:
    """A chunk of text with associated metadata."""

    content: str
    heading_context: list[str]
    source_location: str
    tags: list[str]
    start_line: int
    end_line: int


class ChunkingEngine:
    """Engine for splitting documents into semantic chunks.

    The chunking engine uses a hybrid approach:
    1. Heading-based segmentation to maintain document structure
    2. Semantic content splitting for optimal chunk sizes
    3. Metadata preservation throughout the chunking process
    """

    def __init__(
        self,
        min_chunk_size: int = 100,
        max_chunk_size: int = 512,
        overlap_size: int = 50,
    ):
        """Initialize the chunking engine.

        Args:
            min_chunk_size: Minimum chunk size in characters
            max_chunk_size: Maximum chunk size in characters
            overlap_size: Number of characters to overlap between chunks
        """
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

    def chunk_document(
        self, content: str, source_location: str, tags: list[str] | None = None
    ) -> list[Chunk]:
        """Split a document into chunks while preserving context.

        Args:
            content: The document content to chunk
            source_location: Location/identifier of the source document
            tags: Optional list of tags associated with the document

        Returns:
            List of Chunk objects with content and metadata
        """
        # Use empty list if no tags provided
        tags = tags or []

        # First split by headings
        heading_splits = self._split_by_headings(content)

        # Initialize result list
        chunks: list[Chunk] = []

        # Process each heading section
        for heading_context, section_content in heading_splits:
            # Split section content semantically
            section_chunks = self._split_semantic_content(
                section_content, heading_context
            )

            # Set source location and tags for each chunk
            for chunk in section_chunks:
                chunk.source_location = source_location
                chunk.tags = tags.copy()

            chunks.extend(section_chunks)

        return chunks

    def _split_by_headings(self, content: str) -> list[tuple[list[str], str]]:
        """Split content by markdown headings.

        Args:
            content: Markdown content to split

        Returns:
            List of (heading_context, content) tuples
        """
        # Split content into lines while preserving line numbers
        lines = content.split("\n")

        # Initialize variables
        current_heading_stack: list[str] = []
        current_content_lines: list[str] = []
        result: list[tuple[list[str], str]] = []

        # Regex for markdown headings (e.g., # Heading, ## Subheading)
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")

        for line in lines:
            # Check if line is a heading
            heading_match = heading_pattern.match(line)

            if heading_match:
                # If we have accumulated content, save it with current heading context
                if current_content_lines:
                    result.append(
                        (current_heading_stack.copy(), "\n".join(current_content_lines))
                    )
                    current_content_lines = []

                # Get heading level and text
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                # Update heading stack based on level
                current_heading_stack = current_heading_stack[: level - 1]
                current_heading_stack.append(heading_text)

                # Add heading line to current content
                current_content_lines.append(line)
            else:
                current_content_lines.append(line)

        # Add any remaining content
        if current_content_lines:
            result.append(
                (current_heading_stack.copy(), "\n".join(current_content_lines))
            )

        return result

    def _split_semantic_content(
        self, content: str, heading_context: list[str]
    ) -> list[Chunk]:
        """Split content semantically while respecting size constraints.

        Args:
            content: Content section to split
            heading_context: List of headings providing context

        Returns:
            List of chunks for this content section
        """
        chunks: list[Chunk] = []
        current_chunk_lines: list[str] = []
        current_size = 0
        start_line = 1

        for line_num, line in enumerate(content.split("\n"), start=1):
            line_size = len(line.split())

            if current_size + line_size > self.max_chunk_size and current_chunk_lines:
                # Create chunk if it meets minimum size
                chunk_content = "\n".join(current_chunk_lines)
                if len(chunk_content) >= self.min_chunk_size:
                    chunks.append(
                        Chunk(
                            content=chunk_content,
                            heading_context=heading_context.copy(),
                            source_location="",  # Will be set by chunk_document
                            tags=[],  # Will be set by chunk_document
                            start_line=start_line,
                            end_line=line_num - 1,
                        )
                    )
                current_chunk_lines = []
                current_size = 0
                start_line = line_num

            current_chunk_lines.append(line)
            current_size += line_size

        # Add remaining content as final chunk if it meets minimum size
        if current_chunk_lines:
            chunk_content = "\n".join(current_chunk_lines)
            if len(chunk_content) >= self.min_chunk_size:
                chunks.append(
                    Chunk(
                        content=chunk_content,
                        heading_context=heading_context.copy(),
                        source_location="",  # Will be set by chunk_document
                        tags=[],  # Will be set by chunk_document
                        start_line=start_line,
                        end_line=len(content.split("\n")),
                    )
                )

        return chunks
