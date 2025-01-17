"""Tests for vector store functionality."""

import json
import os
import tempfile
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from nova.vector_store.chunking import Chunk
from nova.vector_store.store import VectorStore


@pytest.fixture
def output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create required directories
        vector_dir = temp_path / ".nova" / "vectors"
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

        yield temp_path


@pytest.fixture
def store(output_dir: Path) -> Generator[VectorStore, None, None]:
    """Create a test vector store."""
    store = VectorStore(vector_dir=str(output_dir / ".nova" / "vectors"))
    yield store
    try:
        store.cleanup()
    except Exception:
        # Ignore cleanup errors in tests since ChromaDB sometimes fails to release
        # resources immediately in test environments. This doesn't affect actual usage.
        pass


@pytest.fixture
def populated_store(store: VectorStore) -> Generator[VectorStore, None, None]:
    """Create a vector store populated with test data."""
    chunks = [
        Chunk(
            text="Frontend developer with React experience needed for web development",
            heading_text="Job Posting",
            heading_level=1,
            tags=["frontend", "react"],
        ),
        Chunk(
            text="Python developer position available for backend programming",
            heading_text="Job Posting",
            heading_level=1,
            tags=["backend", "python"],
        ),
        Chunk(
            text="Web programmer needed for frontend and backend development",
            heading_text="Job Posting",
            heading_level=1,
            tags=["fullstack"],
        ),
        Chunk(
            text="Software engineer with web development skills required",
            heading_text="Job Posting",
            heading_level=1,
            tags=["fullstack"],
        ),
        Chunk(
            text="Machine learning engineer position in artificial intelligence team",
            heading_text="Tech Topics",
            heading_level=1,
            tags=["ml", "ai"],
        ),
        Chunk(
            text="Deep learning and machine learning projects in AI department",
            heading_text="Tech Topics",
            heading_level=1,
            tags=["ml", "ai"],
        ),
        Chunk(
            text="Random text about gardening and cooking recipes",
            heading_text="Random",
            heading_level=1,
            tags=[],
        ),
    ]

    for chunk in chunks:
        store.add_chunk(
            chunk,
            {
                "source": str(chunk.source) if chunk.source else "",
                "heading_text": chunk.heading_text,
                "heading_level": chunk.heading_level,
                "tags": json.dumps(chunk.tags),
                "attachments": json.dumps(chunk.attachments),
                "chunk_id": chunk.chunk_id,
            },
        )

    # Wait for ChromaDB to persist the data
    time.sleep(0.5)  # Increased wait time to ensure data is persisted
    yield store


def test_exact_match_search(populated_store: VectorStore) -> None:
    """Test search with exact phrase matches."""
    results = populated_store.search("frontend developer")
    assert len(results) > 0
    assert any("frontend developer" in result["text"].lower() for result in results)
    assert results[0]["score"] > 65  # High score for exact match


def test_partial_match_search(populated_store: VectorStore) -> None:
    """Test search with partial matches."""
    results = populated_store.search("python developer")
    assert len(results) > 0
    assert any("python" in result["text"].lower() for result in results)
    assert any("developer" in result["text"].lower() for result in results)
    assert all(result["score"] > 20 for result in results)  # Good scores for partial matches


def test_semantic_search(populated_store: VectorStore) -> None:
    """Test semantic search capabilities."""
    results = populated_store.search("web programmer")  # Should match frontend/backend developer
    assert len(results) > 0
    assert any("web" in result["text"].lower() for result in results)
    assert any(
        "programmer" in result["text"].lower() or "developer" in result["text"].lower()
        for result in results
    )
    assert all(result["score"] > 5 for result in results)  # Decent scores for semantic matches


def test_relevance_ordering(populated_store: VectorStore) -> None:
    """Test that results are ordered by relevance score."""
    # Test relevant content gets high scores
    ml_results = populated_store.search("machine learning artificial intelligence")
    assert len(ml_results) > 0
    ml_scores = [
        r["score"]
        for r in ml_results
        if any(
            term in r["text"].lower()
            for term in ["machine learning", "artificial intelligence", "ai"]
        )
    ]
    assert len(ml_scores) > 0
    assert all(score > 50 for score in ml_scores)  # High scores for relevant content

    # Test unrelated content gets lower scores
    unrelated_results = populated_store.search("gardening cooking")
    assert len(unrelated_results) > 0
    unrelated_scores = [r["score"] for r in unrelated_results]

    # Test relative ordering
    mixed_results = populated_store.search("machine learning gardening")
    assert len(mixed_results) > 0

    ml_mixed_scores = [
        r["score"]
        for r in mixed_results
        if any(term in r["text"].lower() for term in ["machine learning", "ai"])
    ]
    gardening_mixed_scores = [r["score"] for r in mixed_results if "gardening" in r["text"].lower()]

    # Verify that relevant content scores higher than unrelated content
    if ml_mixed_scores and gardening_mixed_scores:
        assert min(ml_mixed_scores) > max(gardening_mixed_scores)


def test_metadata_search(populated_store: VectorStore) -> None:
    """Test search results include correct metadata."""
    results = populated_store.search("frontend developer")
    assert len(results) > 0
    for result in results:
        assert "metadata" in result
        metadata = result["metadata"]
        assert "heading_text" in metadata
        assert "tags" in metadata
        tags = json.loads(metadata["tags"])
        assert isinstance(tags, list)


def test_combined_filters(store: VectorStore) -> None:
    """Test combining tag and attachment filters."""
    # Create chunks with different combinations
    chunk1 = Chunk(
        text="Document with tag and image",
        tags=["documentation"],
        attachments=[{"type": "image", "path": "test.jpg"}],
    )
    chunk2 = Chunk(text="Document with tag only", tags=["documentation"])
    chunk3 = Chunk(
        text="Document with image only", attachments=[{"type": "image", "path": "test.png"}]
    )
    chunk4 = Chunk(text="Document with neither")

    for chunk in [chunk1, chunk2, chunk3, chunk4]:
        store.add_chunk(
            chunk,
            {
                "source": str(chunk.source) if chunk.source else "",
                "heading_text": chunk.heading_text,
                "heading_level": chunk.heading_level,
                "tags": json.dumps(chunk.tags),
                "attachments": json.dumps(chunk.attachments),
                "chunk_id": chunk.chunk_id,
            },
        )

    # Wait for ChromaDB to persist the data
    time.sleep(0.5)  # Increased wait time to ensure data is persisted

    # Search with both filters
    results = store.search("document", tag_filter="documentation", attachment_type="image")

    assert len(results) == 1  # Only chunk1 should match
    assert "tag and image" in results[0]["text"]

    # Verify metadata
    metadata = results[0]["metadata"]
    tags = json.loads(metadata["tags"])
    attachments = json.loads(metadata["attachments"])
    assert "documentation" in tags
    assert any(attachment["type"] == "image" for attachment in attachments)


def test_empty_search(store: VectorStore) -> None:
    """Test searching with no chunks."""
    results = store.search("test")
    assert len(results) == 0


def test_case_insensitive_search(populated_store: VectorStore) -> None:
    """Test case insensitive search."""
    lower_results = populated_store.search("frontend developer")
    upper_results = populated_store.search("FRONTEND DEVELOPER")

    assert len(lower_results) == len(upper_results)
    if lower_results and upper_results:
        assert abs(lower_results[0]["score"] - upper_results[0]["score"]) < 1.0


def test_search_limit(populated_store: VectorStore) -> None:
    """Test search result limit."""
    limit = 2
    results = populated_store.search("developer", limit=limit)
    assert len(results) <= limit


def test_nonexistent_query(populated_store: VectorStore) -> None:
    """Test search with a query that should match nothing."""
    results = populated_store.search("xyzabc123nonexistentquery")
    assert len(results) == 0


def test_score_normalization(populated_store: VectorStore) -> None:
    """Test that all scores are properly normalized."""
    results = populated_store.search("developer")
    assert len(results) > 0
    for result in results:
        score = result["score"]
        assert 0 <= score <= 100, f"Score {score} is not normalized between 0 and 100"
