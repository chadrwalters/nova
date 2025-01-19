"""Tests for vector store health checks."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest

from nova.vector_store.store import HealthData, VectorStore


@pytest.fixture
def temp_vector_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for vector store."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_vector_store_health(temp_vector_dir: Path) -> None:
    """Test vector store health check."""
    store = VectorStore(str(temp_vector_dir))

    # Test initial health check
    health = store.check_health()
    assert health["status"] == "healthy"
    assert health["directory"]["exists"] is True
    assert health["directory"]["is_directory"] is True
    assert health["collection"]["exists"] is True
    assert health["collection"]["count"] == 0
    assert health["repository"]["total_chunks"] == 0
    assert health["repository"]["unique_sources"] == 0
    assert health["repository"]["file_types"] == {}
    assert health["repository"]["total_attachments"] == 0
    assert health["repository"]["attachment_types"] == {}
    assert health["repository"]["tags"]["total"] == 0
    assert health["repository"]["tags"]["unique"] == 0
    assert health["repository"]["tags"]["list"] == []

    # Add some test data
    store.add_chunk(
        chunk=Mock(
            chunk_id="chunk1",
            text="Sample text 1",
            to_metadata=lambda: {
                "document_id": "doc1",
                "document_type": "markdown",
                "document_size": 5000,
                "tags": json.dumps(["python", "code"]),
                "date": "2024-01-01",
            },
        )
    )
    store.add_chunk(
        chunk=Mock(
            chunk_id="chunk2",
            text="Sample text 2",
            to_metadata=lambda: {
                "document_id": "doc1",
                "document_type": "markdown",
                "document_size": 5000,
                "tags": json.dumps(["python", "tutorial"]),
                "date": "2024-01-01",
            },
        )
    )
    store.add_chunk(
        chunk=Mock(
            chunk_id="chunk3",
            text="Sample text 3",
            to_metadata=lambda: {
                "document_id": "doc2",
                "document_type": "pdf",
                "document_size": 150000,
                "tags": "[]",
                "date": "2024-03-15",
            },
        )
    )

    # Test health check with data
    health = cast(HealthData, store.check_health())
    assert health["status"] == "healthy"
    assert health["collection"]["count"] == 3
    assert health["repository"]["total_chunks"] == 3
    assert health["repository"]["unique_sources"] == 2
    assert health["repository"]["file_types"] == {"markdown": 2, "pdf": 1}
    assert health["repository"]["tags"]["total"] == 4
    assert health["repository"]["tags"]["unique"] == 3
    assert set(health["repository"]["tags"]["list"]) == {"python", "code", "tutorial"}
    if "size_stats" in health["repository"]:
        assert health["repository"]["size_stats"]["min_size"] > 0
        assert health["repository"]["size_stats"]["max_size"] > 0
        assert health["repository"]["size_stats"]["avg_size"] > 0
        assert health["repository"]["size_stats"]["total_size"] > 0
