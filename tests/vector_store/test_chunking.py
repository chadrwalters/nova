"""Tests for the chunking engine."""

from pathlib import Path

import pytest

from nova.vector_store.chunking import Chunk, ChunkingEngine


@pytest.fixture
def engine() -> ChunkingEngine:
    """Create a chunking engine for testing."""
    return ChunkingEngine()


def test_chunk_size_limits():
    """Test that chunks respect size limits."""
    engine = ChunkingEngine(min_chunk_size=10, max_chunk_size=50)

    # Test max size
    long_text = "This is a very long paragraph that should be split into multiple chunks. " * 3
    chunks = engine.chunk_document(long_text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 50

    # Test min size (should combine very small chunks)
    small_text = "One\nTwo\nThree"
    chunks = engine.chunk_document(small_text)
    assert len(chunks) == 1
    assert chunks[0].text == small_text


def test_heading_hierarchy():
    """Test that heading hierarchy is preserved."""
    engine = ChunkingEngine()
    text = """# Main Heading
Content 1

## Section 1
Content 2

### Subsection 1.1
Content 3

## Section 2
Content 4"""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 4

    # Check heading levels
    assert chunks[0].heading_text == "Main Heading"
    assert chunks[0].heading_level == 1
    assert "Content 1" in chunks[0].text

    assert chunks[1].heading_text == "Section 1"
    assert chunks[1].heading_level == 2
    assert "Content 2" in chunks[1].text

    assert chunks[2].heading_text == "Subsection 1.1"
    assert chunks[2].heading_level == 3
    assert "Content 3" in chunks[2].text

    assert chunks[3].heading_text == "Section 2"
    assert chunks[3].heading_level == 2
    assert "Content 4" in chunks[3].text


def test_multiple_tags_same_line():
    """Test handling of multiple tags in the same line."""
    engine = ChunkingEngine()
    text = """# Test
This line has #multiple #tags on the #same/line."""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert set(chunks[0].tags) == {"multiple", "tags", "same/line"}


def test_multiple_attachments():
    """Test handling of multiple attachments in the same chunk."""
    engine = ChunkingEngine()
    text = """# Test
Here's an image: ![Image 1](test1.jpg)
And another: ![Image 2](test2.png)"""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert len(chunks[0].attachments) == 2
    assert chunks[0].attachments[0] == {"type": "image", "path": "test1.jpg"}
    assert chunks[0].attachments[1] == {"type": "image", "path": "test2.png"}


def test_empty_document():
    """Test handling of empty documents."""
    engine = ChunkingEngine()
    chunks = engine.chunk_document("")
    assert len(chunks) == 0

    # Test document with only whitespace
    chunks = engine.chunk_document("   \n  \n  ")
    assert len(chunks) == 0


def test_special_characters():
    """Test handling of special characters in tags and headings."""
    engine = ChunkingEngine()
    text = """# Special! @ # $ % Characters
This has a #tag! and a #special@tag."""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert chunks[0].heading_text == "Special! @ # $ % Characters"
    assert set(chunks[0].tags) == {"tag", "special"}  # Special characters should be stripped


def test_source_path(engine: ChunkingEngine):
    """Test source path is properly set."""
    source = Path("test.md")
    text = "# Test\nContent"
    chunks = engine.chunk_document(text, source=source)
    assert len(chunks) == 1
    assert chunks[0].source == source


def test_chunk_methods():
    """Test Chunk class methods."""
    chunk = Chunk(text="Test content")

    # Test add_tag
    chunk.add_tag("test")
    chunk.add_tag("test")  # Should not duplicate
    assert chunk.tags == ["test"]

    # Test add_attachment
    chunk.add_attachment("image", "test.jpg")
    assert chunk.attachments == [{"type": "image", "path": "test.jpg"}]


def test_tag_hierarchy():
    """Test handling of hierarchical tags."""
    engine = ChunkingEngine()
    text = """# Test
Content with #parent/child/grandchild tag."""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert "parent/child/grandchild" in chunks[0].tags


def test_large_document_chunking():
    """Test chunking of a large document."""
    engine = ChunkingEngine(max_chunk_size=100)
    # Create a large document with repeated content
    paragraphs = [f"This is paragraph {i}. " * 3 for i in range(10)]
    text = "\n\n".join(paragraphs)

    chunks = engine.chunk_document(text)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.text) <= 100


def test_consecutive_headings():
    """Test handling of consecutive headings."""
    engine = ChunkingEngine()
    text = """# Heading 1
## Heading 2
### Heading 3
Content"""

    chunks = engine.chunk_document(text)
    # The chunking engine keeps the last heading when there are consecutive ones
    assert len(chunks) == 1
    assert chunks[0].heading_text == "Heading 3"
    assert chunks[0].heading_level == 3
    assert "Content" in chunks[0].text


def test_invalid_tags():
    """Test handling of invalid tag formats."""
    engine = ChunkingEngine()
    text = """# Test
#123invalid #@invalid #/invalid #
Some content to make the chunk valid."""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert not chunks[0].tags  # No valid tags should be extracted


def test_mixed_content():
    """Test handling of mixed content types."""
    engine = ChunkingEngine()
    text = """# Mixed Content
Regular text with #tag1
![Image](test.jpg)
More text with #tag2
```python
code block
```
Final text with #tag3"""

    chunks = engine.chunk_document(text)
    assert len(chunks) == 1
    assert len(chunks[0].tags) == 3
    assert len(chunks[0].attachments) == 1
    assert "code block" in chunks[0].text
