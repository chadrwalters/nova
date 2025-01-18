"""Tests for vector store functionality."""

import json
import os
import tempfile
import time
from collections.abc import Generator
from pathlib import Path
from typing import cast, Dict, Any, List, Union
import uuid

import pytest
from chromadb.api.types import Where

from nova.vector_store.chunking import Chunk
from nova.vector_store.store import VectorStore


@pytest.fixture
def output_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary output directory for tests."""
    yield tmp_path


@pytest.fixture
def store(output_dir: Path) -> Generator[VectorStore, None, None]:
    """Initialize a test vector store."""
    test_collection = f"test_{uuid.uuid4()}"
    store = VectorStore(
        base_path=str(output_dir / ".nova" / "vectors"),
        use_memory=True
    )
    store.clear()  # Clear any existing data
    yield store


@pytest.fixture
def populated_store(store: VectorStore) -> Generator[VectorStore, None, None]:
    """Populate the vector store with test data."""
    # Add job posting chunks with metadata
    job_chunks = [
        (
            Chunk(
                text="Frontend developer position available for web development",
                source=Path("jobs.md"),
                heading_text="Job Postings",
                heading_level=1
            ),
            {"source": "jobs.md", "tags": "frontend,developer", "heading_text": "Job Postings", "heading_level": 1}
        ),
        (
            Chunk(
                text="Backend developer needed for Python project",
                source=Path("jobs.md"),
                heading_text="Job Postings",
                heading_level=1
            ),
            {"source": "jobs.md", "tags": "backend,developer", "heading_text": "Job Postings", "heading_level": 1}
        ),
    ]
    for chunk, metadata in job_chunks:
        chunk.tags = metadata["tags"]
        store.add_chunk(chunk, metadata)

    # Add tech topic chunks with metadata
    tech_chunks = [
        (
            Chunk(
                text="Machine learning algorithms use neural networks and deep learning for pattern recognition and data analysis",
                source=Path("tech.md"),
                heading_text="Tech Topics",
                heading_level=1
            ),
            {"source": "tech.md", "tags": "ml,ai", "heading_text": "Tech Topics", "heading_level": 1}
        ),
        (
            Chunk(
                text="Artificial intelligence and machine learning models process large datasets to make predictions",
                source=Path("tech.md"),
                heading_text="Tech Topics",
                heading_level=1
            ),
            {"source": "tech.md", "tags": "ml,ai", "heading_text": "Tech Topics", "heading_level": 1}
        ),
        (
            Chunk(
                text="Growing tomatoes and herbs in your garden, plus delicious recipes for homemade pasta sauce",
                source=Path("random.md"),
                heading_text="Random",
                heading_level=1
            ),
            {"source": "random.md", "tags": "", "heading_text": "Random", "heading_level": 1}
        ),
    ]
    for chunk, metadata in tech_chunks:
        chunk.tags = metadata["tags"]
        store.add_chunk(chunk, metadata)

    yield store


def test_exact_match_search(populated_store: VectorStore) -> None:
    """Test search with exact phrase matches."""
    results = populated_store.search("frontend developer")
    assert len(results) > 0
    assert any("frontend developer" in result["text"].lower() for result in results)
    assert results[0]["score"] > 0.85  # High score for exact match


def test_partial_match_search(populated_store: VectorStore) -> None:
    """Test search with partial matches."""
    results = populated_store.search("python developer", min_score=30.0)
    assert len(results) > 0
    assert any("python" in result["text"].lower() for result in results)
    assert all(result["score"] > 30.0 for result in results)


def test_semantic_search(populated_store: VectorStore) -> None:
    """Test semantic search capabilities."""
    results = populated_store.search("web programmer")  # Should match frontend/backend developer
    assert len(results) > 0
    assert any("web" in result["text"].lower() for result in results)
    assert any(
        "programmer" in result["text"].lower() or "developer" in result["text"].lower()
        for result in results
    )
    assert all(result["score"] > 0.5 for result in results)  # Reasonable scores for semantic matches


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
    assert all(score > 0.6 for score in ml_scores)  # High scores for relevant content

    # Test unrelated content gets lower scores
    unrelated_results = populated_store.search("gardening cooking")
    assert len(unrelated_results) > 0
    unrelated_scores = [r["score"] for r in unrelated_results]

    # Test relative ordering with lower threshold for mixed query
    mixed_results = populated_store.search("machine learning gardening", min_score=0.5)
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
        tags = metadata["tags"].split(",")
        assert isinstance(tags, list)


def test_combined_filters(populated_store: VectorStore) -> None:
    """Test combining multiple filter conditions."""
    # Create test chunks with different tags
    chunk1 = Chunk(
        text="Test document with multiple tags",
        source=Path("test.md"),
        heading_text="Main Heading",
        heading_level=1
    )
    # Set tags and attachments using property setters
    chunk1._tags = cast(List[str], ["documentation", "frontend"])  # type: ignore
    chunk1._attachments = cast(List[Dict[str, str]], [{"type": "image", "path": "test.jpg"}])  # type: ignore

    chunk2 = Chunk(
        text="Another test document",
        source=Path("test.md"),
        heading_text="Main Heading",
        heading_level=1
    )
    # Set tags and attachments using property setters
    chunk2._tags = cast(List[str], ["documentation", "backend"])  # type: ignore
    chunk2._attachments = cast(List[Dict[str, str]], [{"type": "code", "path": "test.py"}])  # type: ignore

    # Add chunks to store
    populated_store.add_chunk(chunk1)
    populated_store.add_chunk(chunk2)

    # Search with combined filters
    results = populated_store.search(
        query="test",
        tag_filter="documentation",
        attachment_type="image"
    )

    assert len(results) == 1
    assert results[0]["text"] == "Test document with multiple tags"


def test_empty_search(store: VectorStore) -> None:
    """Test searching with no chunks."""
    results = store.search("test", min_score=30.0)
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
    results = populated_store.search("xyzabc123nonexistentquery", min_score=30.0)
    assert len(results) == 0


def test_score_normalization(populated_store: VectorStore) -> None:
    """Test that all scores are properly normalized."""
    results = populated_store.search("developer")
    assert len(results) > 0
    for result in results:
        score = result["score"]
        assert 0 <= score <= 100, f"Score {score} is not normalized between 0 and 100"
