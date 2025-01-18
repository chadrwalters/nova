"""Tests for enhanced vector store features."""

import json
import os
import shutil
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from nova.vector_store.chunking import Chunk, ChunkingEngine
from nova.vector_store.store import VectorStore


@pytest.fixture
def vector_store(tmp_path: Path) -> Generator[VectorStore, None, None]:
    """Create a test vector store."""
    vector_dir = tmp_path / ".nova" / "vectors"
    vector_dir.mkdir(parents=True)

    # Create chroma directory with write permissions
    chroma_dir = vector_dir / "chroma"
    chroma_dir.mkdir(parents=True)
    os.chmod(chroma_dir, 0o700)

    # Create required subdirectories with write permissions
    for subdir in ["db", "index", "system", "data"]:
        dir_path = chroma_dir / subdir
        dir_path.mkdir(parents=True)
        os.chmod(dir_path, 0o700)

    store = VectorStore(str(vector_dir))
    yield store
    try:
        shutil.rmtree(str(store.base_path))
    except Exception:  # nosec
        pass  # Ignore cleanup errors in tests


@pytest.fixture
def chunking_engine() -> ChunkingEngine:
    """Create a test chunking engine."""
    return ChunkingEngine()


@pytest.mark.skip(reason="ChromaDB filter format needs to be updated for tag hierarchy search")
def test_tag_hierarchy_search(vector_store: VectorStore, chunking_engine: ChunkingEngine) -> None:
    """Test searching with hierarchical tags."""
    # Create test document with hierarchical tags
    chunk = Chunk(
        text="This is the main content with category/subcategory tag",
        source=Path("test.md"),
        heading_text="Main Heading",
        heading_level=1,
    )
    chunk._tags = ["category/subcategory"]
    chunk._attachments = []

    # Add chunk to store
    vector_store.add_chunk(
        chunk,
        {
            "source": str(chunk.source) if chunk.source else "",
            "heading_text": chunk.heading_text,
            "heading_level": chunk.heading_level,
            "tags": json.dumps(chunk._tags),
            "attachments": json.dumps([f"{att['type']}:{att['path']}" for att in chunk._attachments]),
            "chunk_id": chunk.chunk_id,
        },
    )

    # Wait for ChromaDB to persist the data
    time.sleep(0.1)

    # Search for chunks with the full hierarchical tag
    results = vector_store.search("content", tag_filter="category/subcategory")
    assert len(results) > 0  # nosec
    assert any(  # nosec
        "category/subcategory" in json.loads(result["metadata"]["tags"]) for result in results
    )


@pytest.mark.skip(reason="ChromaDB filter format needs to be updated for attachment filtering")
def test_attachment_filtering(vector_store: VectorStore, chunking_engine: ChunkingEngine) -> None:
    """Test filtering by attachment type."""
    # Create test document with attachments
    chunk = Chunk(
        text="Content with image attachment",
        source=Path("test.md"),
        heading_text="Main Heading",
        heading_level=1
    )
    chunk._attachments = [{"type": "image", "path": "test.jpg"}]

    # Add chunk to store
    vector_store.add_chunk(
        chunk,
        {
            "source": str(chunk.source) if chunk.source else "",
            "heading_text": chunk.heading_text,
            "heading_level": chunk.heading_level,
            "tags": json.dumps(chunk._tags),
            "attachments": json.dumps([f"{att['type']}:{att['path']}" for att in chunk._attachments]),
            "chunk_id": chunk.chunk_id,
        },
    )

    # Wait for ChromaDB to persist the data
    time.sleep(0.1)

    # Search for chunks with image attachments
    results = vector_store.search("content", attachment_type="image")
    assert len(results) > 0  # nosec
    assert all(  # nosec
        any("image:" in att for att in json.loads(result["metadata"]["attachments"]))
        for result in results
    )


def test_combined_filtering(vector_store: VectorStore, chunking_engine: ChunkingEngine) -> None:
    """Test combining tag and attachment filters."""
    # Create chunks with different tags and attachments
    chunk = Chunk(
        text="Test document with multiple tags",
        source=Path("test.md"),
        heading_text="Main Heading",
        heading_level=1
    )
    chunk._tags = ["documentation", "test"]
    chunk._attachments = [{"type": "image", "path": "test.jpg"}]

    # Add chunk to store
    vector_store.add_chunk(chunk)

    # Wait for ChromaDB to persist the data
    time.sleep(0.1)

    # Search with both filters
    results = vector_store.search("test document", tag_filter="documentation", attachment_type="image")
    assert len(results) > 0  # nosec
    for result in results:
        metadata = result["metadata"]
        # Check if the tag flag is present
        assert metadata.get("tag_documentation") is True  # nosec
        # Check if the attachment type flag is present
        assert metadata.get("attachment_type_image") is True  # nosec
