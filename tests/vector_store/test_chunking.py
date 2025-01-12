"""Tests for the chunking engine."""

from pathlib import Path


from nova.vector_store.chunking import ChunkingEngine


def test_chunk_document_basic() -> None:
    """Test basic document chunking."""
    engine = ChunkingEngine()
    text = "This is a test document.\n\nIt has multiple paragraphs."
    chunks = engine.chunk_document(text)

    assert len(chunks) == 2
    assert chunks[0].text == "This is a test document."
    assert chunks[1].text == "It has multiple paragraphs."


def test_chunk_document_with_headings() -> None:
    """Test document chunking with headings."""
    engine = ChunkingEngine()
    text = "# Heading 1\nParagraph 1\n\n# Heading 2\nParagraph 2"
    chunks = engine.chunk_document(text)

    assert len(chunks) == 2
    assert chunks[0].text == "Paragraph 1"
    assert chunks[0].heading_context == "Heading 1"
    assert chunks[1].text == "Paragraph 2"
    assert chunks[1].heading_context == "Heading 2"


def test_chunk_document_with_source() -> None:
    """Test document chunking with source path."""
    engine = ChunkingEngine()
    text = "This is a test document."
    source = Path("test.md")
    chunks = engine.chunk_document(text, source)

    assert len(chunks) == 1
    assert chunks[0].text == "This is a test document."
    assert chunks[0].source == source


def test_chunk_document_empty() -> None:
    """Test chunking empty document."""
    engine = ChunkingEngine()
    text = ""
    chunks = engine.chunk_document(text)

    assert len(chunks) == 0
