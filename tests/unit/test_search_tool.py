"""Unit tests for search tool."""

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from numpy.typing import NDArray

from nova.server.tools.search import SearchTool
from nova.server.types import ResourceError
from nova.vector_store.store import VectorStore


class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self) -> None:
        """Initialize mock vector store."""
        self.vectors: list[dict] = []

    def add_embeddings(
        self,
        embedding_vectors: list[NDArray[np.float32]],
        metadata_dicts: list[dict[str, str | int | float | bool]],
    ) -> None:
        """Add embeddings to store.

        Args:
            embedding_vectors: List of embedding vectors
            metadata_dicts: List of metadata dictionaries
        """
        pass

    def query(
        self,
        query_vector: NDArray[np.float32],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Query vectors.

        Args:
            query_vector: Query vector
            n_results: Maximum number of results to return
            where: Optional filter conditions

        Returns:
            List of results
        """
        return [
            {
                "id": "test1",
                "distance": 0.1,
                "metadata": {
                    "content": "test content",
                    "source": "test",
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                    "tags": ["test"],
                },
            }
        ]


@pytest.fixture
def search_tool(tmp_path: Path) -> SearchTool:
    """Create search tool fixture.

    Args:
        tmp_path: Temporary directory path

    Returns:
        SearchTool instance
    """
    schema_path = tmp_path / "search_tool.json"
    schema = {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "type": {"type": "string"},
            "name": {"type": "string"},
            "version": {"type": "string"},
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "n_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "minimum": 1,
                        "default": 10,
                    },
                    "min_score": {
                        "type": "number",
                        "description": "Minimum similarity score threshold",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.0,
                    },
                    "filters": {
                        "type": "object",
                        "description": "Optional filters to apply",
                    },
                },
                "required": ["query"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    return SearchTool(schema_path, MockVectorStore())


def test_validate_request(search_tool: SearchTool) -> None:
    """Test request validation."""
    # Valid request
    search_tool.validate_request(
        {
            "id": "search-1",
            "type": "search",
            "name": "Search Test",
            "version": "1.0.0",
            "parameters": {
                "query": "test",
                "n_results": 10,
                "min_score": 0.5,
                "filters": {"source": "test"},
            },
            "capabilities": ["search"],
        }
    )

    # Invalid n_results
    with pytest.raises(
        ResourceError, match="Invalid search request: Invalid n_results"
    ):
        search_tool.validate_request(
            {
                "id": "search-2",
                "type": "search",
                "name": "Search Test",
                "version": "1.0.0",
                "parameters": {
                    "query": "test",
                    "n_results": 0,
                    "min_score": 0.5,
                    "filters": {"source": "test"},
                },
                "capabilities": ["search"],
            }
        )

    # Invalid min_score
    with pytest.raises(
        ResourceError, match="Invalid search request: Invalid min_score"
    ):
        search_tool.validate_request(
            {
                "id": "search-3",
                "type": "search",
                "name": "Search Test",
                "version": "1.0.0",
                "parameters": {
                    "query": "test",
                    "n_results": 10,
                    "min_score": 2.0,
                    "filters": {"source": "test"},
                },
                "capabilities": ["search"],
            }
        )

    # Invalid filters
    with pytest.raises(ResourceError, match="Invalid search request: Invalid filters"):
        search_tool.validate_request(
            {
                "id": "search-4",
                "type": "search",
                "name": "Search Test",
                "version": "1.0.0",
                "parameters": {
                    "query": "test",
                    "n_results": 10,
                    "min_score": 0.5,
                    "filters": "invalid",
                },
                "capabilities": ["search"],
            }
        )


def test_validate_response(search_tool: SearchTool) -> None:
    """Test response validation."""
    # Valid response
    response = {
        "results": [
            {
                "id": "test1",
                "score": 0.9,
                "content": "test content",
                "metadata": {
                    "source": "test",
                    "created": "2024-01-01T00:00:00Z",
                    "modified": "2024-01-01T00:00:00Z",
                    "tags": ["test"],
                },
            }
        ],
        "total": 1,
        "query": "test",
    }
    search_tool.validate_response(response)

    # Invalid score
    with pytest.raises(
        ResourceError,
        match="Invalid search response: 2.0 is greater than the maximum of 1.0",
    ):
        search_tool.validate_response(
            {
                "results": [
                    {
                        "id": "test1",
                        "score": 2.0,
                        "content": "test content",
                        "metadata": {
                            "source": "test",
                            "created": "2024-01-01T00:00:00Z",
                            "modified": "2024-01-01T00:00:00Z",
                        },
                    }
                ],
                "total": 1,
                "query": "test",
            }
        )

    # Missing required field
    with pytest.raises(ResourceError, match="Invalid search response: Missing content"):
        search_tool.validate_response(
            {
                "results": [
                    {
                        "id": "test1",
                        "score": 0.9,
                        "metadata": {
                            "source": "test",
                            "created": "2024-01-01T00:00:00Z",
                            "modified": "2024-01-01T00:00:00Z",
                        },
                    }
                ],
                "total": 1,
                "query": "test",
            }
        )


def test_search(search_tool: SearchTool) -> None:
    """Test search functionality."""
    # Basic search
    request = {
        "id": "search-1",
        "type": "search",
        "name": "Search Test",
        "version": "1.0.0",
        "parameters": {
            "query": "test query",
            "n_results": 3,
            "min_score": 0.5,
            "filters": {"source": "test"},
        },
        "capabilities": ["search"],
    }
    response = search_tool.search(request)
    assert isinstance(response, dict)
    assert "results" in response
    assert "total" in response
    assert "query" in response
    assert len(response["results"]) > 0
    result = response["results"][0]
    assert isinstance(result["id"], str)
    assert isinstance(result["score"], float)
    assert isinstance(result["content"], str)
    assert isinstance(result["metadata"], dict)

    # No results
    request = {
        "id": "search-2",
        "type": "search",
        "name": "Search Test",
        "version": "1.0.0",
        "parameters": {"query": "no results", "min_score": 1.0},
        "capabilities": ["search"],
    }
    response = search_tool.search(request)
    assert len(response["results"]) == 0
