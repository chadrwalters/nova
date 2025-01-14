"""Performance tests for tool operations."""

import json
import time
import uuid
from pathlib import Path
from typing import Any
from collections.abc import Callable

import pytest

from nova.server.server import NovaServer
from nova.server.tools import SearchTool, ListTool, ExtractTool, RemoveTool
from nova.server.types import ServerConfig
from nova.stubs.docling import Document
from nova.vector_store.store import VectorStore


@pytest.fixture
def schema_dir(tmp_path: Path) -> Path:
    """Create schema directory with tool schemas."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir(parents=True)

    # Create search schema
    search_schema = {
        "id": "search",
        "type": "object",
        "properties": {
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "n_results": {"type": "integer"},
                    "min_score": {"type": "number"},
                },
                "required": ["query"],
            }
        },
        "required": ["parameters"],
    }
    with open(schema_dir / "search.json", "w") as f:
        json.dump(search_schema, f)

    # Create list schema
    list_schema = {
        "id": "list",
        "type": "object",
        "properties": {
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {"type": "string"},
                    "filter": {"type": "string"},
                    "path": {"type": "string"},
                },
                "required": ["path"],
            }
        },
        "required": ["parameters"],
    }
    with open(schema_dir / "list.json", "w") as f:
        json.dump(list_schema, f)

    # Create extract schema
    extract_schema = {
        "id": "extract",
        "type": "object",
        "properties": {
            "parameters": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "format": {"type": "string"},
                    "target_path": {"type": "string"},
                },
                "required": ["source_id", "target_path"],
            }
        },
        "required": ["parameters"],
    }
    with open(schema_dir / "extract.json", "w") as f:
        json.dump(extract_schema, f)

    # Create remove schema
    remove_schema = {
        "id": "remove",
        "type": "object",
        "properties": {
            "parameters": {
                "type": "object",
                "properties": {
                    "target_id": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "required": ["target_id"],
            }
        },
        "required": ["parameters"],
    }
    with open(schema_dir / "remove.json", "w") as f:
        json.dump(remove_schema, f)

    return schema_dir


@pytest.fixture
def vector_store(tmp_path: Path) -> VectorStore:
    """Create vector store for testing."""
    store_dir = tmp_path / "vector_store"
    store_dir.mkdir(parents=True)
    return VectorStore(store_dir)


@pytest.fixture
def server(tmp_path: Path) -> NovaServer:
    """Create server instance for testing."""
    config = ServerConfig(
        host="localhost",
        port=8000,
        debug=True,
        max_connections=5,
        store_dir=str(tmp_path),
    )
    server = NovaServer(config)
    return server


@pytest.fixture
def sample_documents() -> list[dict[str, Any]]:
    """Create sample documents for testing."""
    docs = []
    for i in range(10):
        doc = Document(name=f"Test Document {i}")
        doc.text = f"Test document {i} with some content for testing vector operations"
        doc.metadata = {
            "tags": ",".join(["test", "performance"]),
            "source": "test.md",
            "index": i,
            "format": "text",
            "modified": str(time.time()),
        }
        docs.append({"content": doc.text, "metadata": doc.metadata})
    return docs


def test_search_tool_execution(
    benchmark: Callable[[Callable[[], None]], None],
    vector_store: VectorStore,
    schema_dir: Path,
    sample_documents: list[dict],
) -> None:
    """Test search tool execution."""
    # Add a document first
    doc = sample_documents[0]
    doc_id = str(uuid.uuid4())
    vector_store.add(doc_id, doc["content"], doc["metadata"])
    vector_store._process_batch()  # Ensure document is committed

    search_tool = SearchTool(schema_dir / "search.json", vector_store)
    request = {
        "parameters": {
            "query": doc["content"],
            "n_results": 5,
            "min_score": 0.7,
        }
    }
    search_tool.validate_request(request)

    def run_search() -> None:
        response = search_tool.search(request)
        assert isinstance(response, dict)
        assert "results" in response
        assert isinstance(response["results"], list)

    benchmark(run_search)


def test_list_tool_execution(
    benchmark: Callable[[Callable[[], None]], None], schema_dir: Path
) -> None:
    """Test list tool execution."""
    list_tool = ListTool(schema_dir / "list.json")
    request = {
        "parameters": {
            "path": str(schema_dir),
            "type": "text",
            "filter": "*.txt",
        }
    }
    list_tool.validate_request(request)

    def run_list() -> None:
        response = list_tool.list(request)
        assert isinstance(response, dict)
        assert "entries" in response
        assert isinstance(response["entries"], list)

    benchmark(run_list)


def test_extract_tool_execution(
    benchmark: Callable[[Callable[[], None]], None],
    vector_store: VectorStore,
    schema_dir: Path,
    sample_documents: list[dict],
) -> None:
    """Test extract tool execution."""
    # Add a document first
    doc = sample_documents[0]
    doc_id = str(uuid.uuid4())
    vector_store.add(doc_id, doc["content"], doc["metadata"])
    vector_store._process_batch()  # Ensure document is committed

    # Create a test file
    test_file = Path("test.txt")
    test_file.write_text("Test content for extraction")

    extract_tool = ExtractTool(schema_dir / "extract.json")
    request = {
        "parameters": {
            "source_id": doc_id,
            "format": "text",
            "target_path": str(test_file),
        }
    }
    extract_tool.validate_request(request)

    def run_extract() -> None:
        response = extract_tool.extract(request)
        assert isinstance(response, dict)
        assert "id" in response
        assert "success" in response
        assert "metadata" in response
        assert isinstance(response["id"], str)
        assert isinstance(response["success"], bool)
        assert isinstance(response["metadata"], dict)

    benchmark(run_extract)

    # Clean up
    test_file.unlink()


def test_remove_tool_execution(
    benchmark: Callable[[Callable[[], None]], None],
    vector_store: VectorStore,
    schema_dir: Path,
    sample_documents: list[dict],
) -> None:
    """Test remove tool execution."""
    # Add a document first
    doc = sample_documents[0]
    doc_id = str(uuid.uuid4())
    vector_store.add(doc_id, doc["content"], doc["metadata"])
    vector_store._process_batch()  # Ensure document is committed

    remove_tool = RemoveTool(schema_dir / "remove.json")
    request = {
        "parameters": {
            "target_id": doc_id,
            "force": True,
        }
    }
    remove_tool.validate_request(request)

    def run_remove() -> None:
        response = remove_tool.remove(request)
        assert isinstance(response, dict)
        assert "id" in response
        assert "success" in response
        assert "metadata" in response
        assert isinstance(response["id"], str)
        assert isinstance(response["success"], bool)
        assert isinstance(response["metadata"], dict)

    benchmark(run_remove)
