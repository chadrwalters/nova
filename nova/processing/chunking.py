import re
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from nova.processing.types import Chunk, Document

class ChunkingEngine:
    def __init__(self, chunk_size: int = 500, heading_weight: float = 1.5):
        """Initialize the chunking engine.
        
        Args:
            chunk_size: Target size for chunks in characters
            heading_weight: Weight multiplier for heading-based chunks
        """
        self.chunk_size = chunk_size
        self.heading_weight = heading_weight
    
    def process_directory(self, directory: Path) -> List[Chunk]:
        """Process all markdown files in a directory."""
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        chunks = []
        for md_file in directory.glob("**/*.md"):
            document = Document(
                content=md_file.read_text(),
                source=str(md_file),
                metadata={"source": "markdown"}
            )
            chunks.extend(self.chunk_document(document))
        
        return chunks
    
    def chunk_document(self, document: Document) -> List[Chunk]:
        """Process a document into chunks using hybrid chunking strategy."""
        # Split into sections by headings
        sections = self._split_by_headings(document.content)
        
        chunks = []
        for heading, content in sections:
            # Create chunks from each section
            section_chunks = self._create_section_chunks(
                content=content,
                heading=heading,
                metadata=document.metadata.copy()
            )
            chunks.extend(section_chunks)
        
        return chunks
    
    def _split_by_headings(self, content: str) -> List[Tuple[Optional[str], str]]:
        """Split content into sections based on markdown headings."""
        sections: List[Tuple[Optional[str], str]] = []
        current_heading: Optional[str] = None
        current_content: List[str] = []
        
        for line in content.split("\n"):
            # Check for heading
            if heading_match := re.match(r"^(#{1,6})\s+(.+)$", line):
                # Save previous section if exists
                if current_content:
                    sections.append((current_heading, "\n".join(current_content)))
                    current_content = []
                
                current_heading = heading_match.group(2)
            else:
                current_content.append(line)
        
        # Add final section
        if current_content:
            sections.append((current_heading, "\n".join(current_content)))
        
        return sections
    
    def _create_section_chunks(
        self,
        content: str,
        heading: Optional[str],
        metadata: dict
    ) -> List[Chunk]:
        """Create chunks from a section, preserving semantic boundaries."""
        chunks = []
        current_chunk: List[str] = []
        current_size = 0
        
        # Update metadata with heading if exists
        if heading:
            metadata = metadata.copy()
            metadata["heading"] = heading
        
        # Split into sentences/paragraphs
        segments = self._split_into_segments(content)
        
        for segment in segments:
            segment_size = len(segment)
            
            # If segment alone exceeds chunk size, split it
            if segment_size > self.chunk_size:
                # First, add current chunk if exists
                if current_chunk:
                    chunks.append(self._create_chunk(
                        "\n".join(current_chunk),
                        metadata,
                        heading
                    ))
                    current_chunk = []
                    current_size = 0
                
                # Split large segment
                segment_chunks = self._split_large_segment(
                    segment,
                    metadata,
                    heading
                )
                chunks.extend(segment_chunks)
                continue
            
            # If adding segment exceeds chunk size, create new chunk
            if current_size + segment_size > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(
                    "\n".join(current_chunk),
                    metadata,
                    heading
                ))
                current_chunk = []
                current_size = 0
            
            # Add segment to current chunk
            current_chunk.append(segment)
            current_size += segment_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                "\n".join(current_chunk),
                metadata,
                heading
            ))
        
        return chunks
    
    def _split_into_segments(self, content: str) -> List[str]:
        """Split content into semantic segments (sentences/paragraphs)."""
        # First split by paragraphs
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        
        segments = []
        for para in paragraphs:
            # For short paragraphs, keep them whole
            if len(para) <= self.chunk_size:
                segments.append(para)
                continue
            
            # For long paragraphs, split into sentences
            sentences = re.split(r"(?<=[.!?])\s+", para)
            segments.extend(sentences)
        
        return segments
    
    def _split_large_segment(
        self,
        segment: str,
        metadata: dict,
        heading: Optional[str]
    ) -> List[Chunk]:
        """Split a large segment into smaller chunks."""
        chunks = []
        words = segment.split()
        current_chunk: List[str] = []
        current_size = 0
        
        for word in words:
            word_size = len(word) + 1  # +1 for space
            
            if current_size + word_size > self.chunk_size and current_chunk:
                chunks.append(self._create_chunk(
                    " ".join(current_chunk),
                    metadata,
                    heading
                ))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(word)
            current_size += word_size
        
        # Add final chunk
        if current_chunk:
            chunks.append(self._create_chunk(
                " ".join(current_chunk),
                metadata,
                heading
            ))
        
        return chunks
    
    def _create_chunk(
        self,
        content: str,
        metadata: dict,
        heading: Optional[str] = None
    ) -> Chunk:
        """Create a chunk with appropriate metadata."""
        chunk_id = str(uuid.uuid4())
        
        # Copy metadata to avoid modifying original
        chunk_metadata = metadata.copy()
        chunk_metadata["chunk_id"] = chunk_id
        
        # Add heading weight if exists
        if heading:
            chunk_metadata["heading"] = heading
            chunk_metadata["heading_weight"] = str(self.heading_weight)
        
        return Chunk(
            content=content.strip(),
            metadata=chunk_metadata,
            chunk_id=chunk_id
        ) 