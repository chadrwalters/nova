"""Unit tests for tool handlers."""

import json
from pathlib import Path
from typing import Any

import pytest

from nova.server.tools.base import ToolHandler
from nova.server.tools.extract import ExtractTool
from nova.server.tools.list import ListTool
from nova.server.tools.remove import RemoveTool
from nova.server.tools.search import SearchTool
from nova.server.types import ResourceError
from nova.vector_store.store import VectorStore


class MockVectorStore(VectorStore):
    """Mock vector store for testing."""

    def __init__(self) -> None:
        """Initialize mock vector store."""
        self.vectors: list[dict] = []

    def add_embeddings(
        self, embedding_vectors: list[Any], metadata_dicts: list[dict[str, Any]]
    ) -> None:
        """Add embeddings to store."""
        pass

    def query(
        self, query_vector: Any, n_results: int = 5, where: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Query vectors."""
        return []

    def delete_vectors(self, vector_ids: list[str]) -> None:
        """Delete vectors from store."""
        pass


@pytest.fixture
def schema_path(tmp_path: Path) -> Path:
    """Create schema path fixture."""
    schema_path = tmp_path / "tool.json"
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
                    "query": {"type": "string"},
                    "n_results": {"type": "integer"},
                    "min_score": {"type": "number"},
                    "filters": {"type": "object"},
                },
                "required": ["query"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    return schema_path


def test_search_tool_validation(schema_path: Path) -> None:
    """Test search tool validation."""
    vector_store = MockVectorStore()
    tool = SearchTool(schema_path, vector_store)

    # Valid request
    tool.validate_request(
        {
            "id": "search-1",
            "type": "search",
            "name": "Search Vectors",
            "version": "1.0.0",
            "parameters": {
                "query": "test",
                "n_results": 10,
                "min_score": 0.5,
                "filters": {"source": "test"},
            },
            "capabilities": ["search", "filter"],
        }
    )

    # Missing query
    with pytest.raises(
        ResourceError, match="Invalid search request: 'query' is a required property"
    ):
        tool.validate_request(
            {
                "id": "search-2",
                "type": "search",
                "name": "Search Vectors",
                "version": "1.0.0",
                "parameters": {},
                "capabilities": ["search"],
            }
        )

    # Invalid n_results
    with pytest.raises(
        ResourceError, match="Invalid search request: Invalid n_results"
    ):
        tool.validate_request(
            {
                "id": "search-3",
                "type": "search",
                "name": "Search Vectors",
                "version": "1.0.0",
                "parameters": {"query": "test", "n_results": 0},
                "capabilities": ["search"],
            }
        )

    # Invalid min_score
    with pytest.raises(
        ResourceError, match="Invalid search request: Invalid min_score"
    ):
        tool.validate_request(
            {
                "id": "search-4",
                "type": "search",
                "name": "Search Vectors",
                "version": "1.0.0",
                "parameters": {"query": "test", "min_score": 2.0},
                "capabilities": ["search"],
            }
        )

    # Invalid filters
    with pytest.raises(ResourceError, match="Invalid search request: Invalid filters"):
        tool.validate_request(
            {
                "id": "search-5",
                "type": "search",
                "name": "Search Vectors",
                "version": "1.0.0",
                "parameters": {"query": "test", "filters": "invalid"},
                "capabilities": ["search"],
            }
        )


def test_list_tool_validation(schema_path: Path) -> None:
    """Test list tool validation."""
    tool = ListTool(schema_path)

    # Valid request
    tool.validate_request(
        {
            "id": "list-1",
            "type": "list",
            "name": "List Files",
            "version": "1.0.0",
            "parameters": {
                "query": "*.txt",
                "path": "/test",
                "recursive": True,
                "include_pattern": "*.txt",
                "exclude_pattern": "*.tmp",
            },
            "capabilities": ["list", "filter"],
        }
    )


def test_extract_tool_validation(schema_path: Path) -> None:
    """Test extract tool validation."""
    tool = ExtractTool(schema_path)

    # Valid request
    tool.validate_request(
        {
            "id": "extract-1",
            "type": "extract",
            "name": "Extract Files",
            "version": "1.0.0",
            "parameters": {
                "source_id": "test-source",
                "target_path": "/test/output",
                "query": "*.txt",
                "path": "/test",
                "pattern": "*.txt",
                "recursive": True,
                "max_files": 100,
            },
            "capabilities": ["extract", "filter"],
        }
    )


def test_remove_tool_validation(schema_path: Path) -> None:
    """Test remove tool validation."""
    tool = RemoveTool(schema_path)

    # Valid request
    tool.validate_request(
        {
            "id": "remove-1",
            "type": "remove",
            "name": "Remove Files",
            "version": "1.0.0",
            "parameters": {
                "target_id": "test-target",
                "query": "*.txt",
                "path": "/test",
                "pattern": "*.txt",
                "recursive": True,
                "dry_run": True,
            },
            "capabilities": ["remove", "filter"],
        }
    )


def test_tool_registry(tmp_path: Path) -> None:
    """Test tool registry."""
    schema_path = tmp_path / "tool.json"
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
                    "query": {"type": "string"},
                    "n_results": {"type": "integer"},
                    "min_score": {"type": "number"},
                    "filters": {"type": "object"},
                },
                "required": ["query"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    vector_store = MockVectorStore()

    tools = [
        SearchTool(schema_path, vector_store),
        ListTool(schema_path),
        ExtractTool(schema_path),
        RemoveTool(schema_path),
    ]

    for tool in tools:
        assert isinstance(tool, ToolHandler)
        assert tool.get_metadata() is not None
        assert tool.validate_request is not None
        assert tool.validate_response is not None
        assert tool.cleanup is not None
