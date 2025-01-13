"""Tests for vector store."""

import pytest
import numpy as np
from pathlib import Path
from collections.abc import Generator

from nova.vector_store.store import VectorStore


@pytest.fixture
def store_dir(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary directory for the vector store.

    Args:
        tmp_path: Pytest temporary path fixture

    Yields:
        Path to temporary directory
    """
    store_dir = tmp_path / "store"
    store_dir.mkdir()
    yield store_dir


def test_add_embeddings_basic(store_dir: Path) -> None:
    """Test basic embedding addition."""
    store = VectorStore(store_dir)

    # Create test embeddings
    embeddings = [np.array([1.0, 2.0, 3.0], dtype=np.float32)]
    metadata: list[dict[str, str | int | float | bool]] = [
        {
            "id": "test1",
            "text": "test text",
            "source": "test.txt",
            "heading_context": "Test",
            "tags": "test",
        }
    ]

    # Add embeddings
    store.add_embeddings(embeddings, metadata)


def test_add_embeddings_multiple(store_dir: Path) -> None:
    """Test adding multiple embeddings."""
    store = VectorStore(store_dir)

    # Create test embeddings
    embeddings = [
        np.array([1.0, 2.0, 3.0], dtype=np.float32),
        np.array([4.0, 5.0, 6.0], dtype=np.float32),
    ]
    metadata: list[dict[str, str | int | float | bool]] = [
        {
            "id": "test1",
            "text": "test text 1",
            "source": "test1.txt",
            "heading_context": "Test 1",
            "tags": "test1",
        },
        {
            "id": "test2",
            "text": "test text 2",
            "source": "test2.txt",
            "heading_context": "Test 2",
            "tags": "test2",
        },
    ]

    # Add embeddings
    store.add_embeddings(embeddings, metadata)


def test_query_with_filter(store_dir: Path) -> None:
    """Test querying with filters."""
    store = VectorStore(store_dir)

    # Create test embeddings with 384 dimensions
    embeddings = [
        np.zeros(384, dtype=np.float32),  # First vector
        np.ones(384, dtype=np.float32),  # Second vector
    ]
    metadata: list[dict[str, str | int | float | bool]] = [
        {
            "id": "test1",
            "text": "test text 1",
            "source": "test1.txt",
            "heading_context": "Test 1",
            "tags": "test1",
        },
        {
            "id": "test2",
            "text": "test text 2",
            "source": "test2.txt",
            "heading_context": "Test 2",
            "tags": "test2",
        },
    ]

    # Add embeddings
    store.add_embeddings(embeddings, metadata)

    # Query with filter
    query = np.zeros(384, dtype=np.float32)  # Query vector matching first embedding
    results = store.query(query, where={"source": "test1.txt"})
    assert len(results) == 1
    assert results[0]["metadata"]["source"] == "test1.txt"
