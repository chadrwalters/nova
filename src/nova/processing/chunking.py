"""Engine for chunking documents into smaller pieces."""

import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple, Union, Dict, Any
from dataclasses import dataclass, field

from nova.processing.types import Chunk, Document

@dataclass
class Document:
    """Document to be chunked."""
    content: str
    metadata: Optional[Dict[str, Any]] = None
    source_path: Optional[Path] = None

    def __str__(self) -> str:
        return self.content

    def __len__(self) -> int:
        return len(self.content)

    def split(self, sep: str) -> List[str]:
        return self.content.split(sep)

class ChunkingEngine:
    """Engine for chunking documents into smaller pieces."""

    def __init__(self, chunk_size: int = 1000, heading_weight: float = 1.5):
        """Initialize the chunking engine.

        Args:
            chunk_size: Maximum size of each chunk in characters.
            heading_weight: Weight to apply to headings when calculating chunk size.
        """
        self.chunk_size = chunk_size
        self.heading_weight = heading_weight

    def chunk_document(self, document: Document, chunk_size: Optional[int] = None) -> List[Chunk]:
        """Chunk a document into smaller pieces.

        Args:
            document: Document to chunk.
            chunk_size: Optional override for the maximum chunk size.

        Returns:
            List of Chunk objects.
        """
        max_size = chunk_size or self.chunk_size
        segments = self._split_into_segments(document.content)
        chunks = []
        current_chunk = []
        current_size = 0

        for segment in segments:
            segment_size = len(segment)
            if current_size + segment_size > max_size and current_chunk:
                # Create a new chunk from accumulated segments
                content = "\n".join(current_chunk)
                chunk = Chunk(
                    content=content,
                    source=document.source,
                    metadata=document.metadata,
                    chunk_id=str(uuid.uuid4()),
                    is_ephemeral=False
                )
                chunks.append(chunk)
                current_chunk = []
                current_size = 0

            current_chunk.append(segment)
            current_size += segment_size

        # Handle any remaining content
        if current_chunk:
            content = "\n".join(current_chunk)
            chunk = Chunk(
                content=content,
                source=document.source,
                metadata=document.metadata,
                chunk_id=str(uuid.uuid4()),
                is_ephemeral=False
            )
            chunks.append(chunk)

        return chunks

    def _split_into_segments(self, text: str) -> List[str]:
        """Split text into segments based on newlines and punctuation.

        Args:
            text: Text to split into segments.

        Returns:
            List of text segments.
        """
        segments = []
        current_segment = []

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                if current_segment:
                    segments.append(" ".join(current_segment))
                    current_segment = []
                continue

            current_segment.append(line)

        if current_segment:
            segments.append(" ".join(current_segment))

        return segments
