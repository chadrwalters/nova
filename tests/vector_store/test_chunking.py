"""Tests for the chunking engine."""
import pytest
from pytest import FixtureRequest
from nova.vector_store.chunking import ChunkingEngine


@pytest.fixture(scope="function")
def sample_markdown(_request: FixtureRequest) -> str:
    """Sample markdown document for testing."""
    return """# Main Heading

This is the first paragraph with some content that should be chunked
appropriately based on semantic meaning and size constraints.

## Sub Heading 1

More content here that continues for a while and should be split into
multiple chunks if it exceeds the maximum chunk size. We want to make
sure the chunking preserves the heading context.

### Sub-Sub Heading

Even more content that should maintain its heading hierarchy when chunked.
This helps ensure proper context is maintained throughout the document.

## Sub Heading 2

Final section with content that should be properly chunked while maintaining
all the appropriate metadata and context information."""


@pytest.fixture(scope="function")
def engine(_request: FixtureRequest) -> ChunkingEngine:
    """Create a ChunkingEngine instance for testing."""
    return ChunkingEngine()


def test_chunking_engine_initialization() -> None:
    """Test initialization of ChunkingEngine."""
    engine = ChunkingEngine(min_chunk_size=100, max_chunk_size=512, overlap_size=50)
    assert engine.min_chunk_size == 100
    assert engine.max_chunk_size == 512
    assert engine.overlap_size == 50


def test_heading_splitting(engine: ChunkingEngine, sample_markdown: str) -> None:
    """Test splitting content by headings."""
    splits = engine._split_by_headings(sample_markdown)
    assert len(splits) == 4  # Main + 2 Sub + 1 Sub-sub sections

    # Check first split
    first_split = splits[0]
    assert first_split[0] == ["Main Heading"]
    assert "first paragraph" in first_split[1]


def test_semantic_content_splitting(engine: ChunkingEngine) -> None:
    """Test splitting content semantically."""
    content = "A " * 1000  # Content that exceeds max_chunk_size
    heading_context = ["Test Heading"]

    chunks = engine._split_semantic_content(content, heading_context)

    # Verify chunk sizes
    for chunk in chunks:
        assert len(chunk.content) >= engine.min_chunk_size
        assert len(chunk.content) <= engine.max_chunk_size
        assert chunk.heading_context == heading_context


def test_document_chunking(engine: ChunkingEngine, sample_markdown: str) -> None:
    """Test complete document chunking process."""
    chunks = engine.chunk_document(
        content=sample_markdown, source_location="test.md", tags=["test", "markdown"]
    )

    # Verify basic chunk properties
    assert len(chunks) > 0
    for chunk in chunks:
        # Size constraints
        assert len(chunk.content) >= engine.min_chunk_size
        assert len(chunk.content) <= engine.max_chunk_size

        # Metadata preservation
        assert chunk.source_location == "test.md"
        assert chunk.tags == ["test", "markdown"]
        assert len(chunk.heading_context) > 0

        # Line numbers
        assert chunk.start_line > 0
        assert chunk.end_line > chunk.start_line
