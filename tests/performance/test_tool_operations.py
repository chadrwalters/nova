"""Performance tests for tool operations."""

import json
import random
from pathlib import Path

import pytest

from nova.server.server import NovaServer
from nova.server.tools import ExtractTool, ListTool, RemoveTool, SearchTool
from nova.server.types import ServerConfig
from tests.performance.conftest import benchmark


@pytest.fixture
def list_schema_path(tmp_path: Path) -> Path:
    """Create list tool schema file."""
    schema_path = tmp_path / "list_tool.json"
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
                    "path": {"type": "string"},
                    "recursive": {"type": "boolean"},
                    "include_pattern": {"type": "string"},
                    "exclude_pattern": {"type": "string"},
                },
                "required": ["path"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    return schema_path


@pytest.fixture
def remove_schema_path(tmp_path: Path) -> Path:
    """Create remove tool schema file."""
    schema_path = tmp_path / "remove_tool.json"
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
                    "target_id": {"type": "string"},
                    "force": {"type": "boolean"},
                },
                "required": ["target_id"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    return schema_path


@pytest.fixture
def search_schema_path(tmp_path: Path) -> Path:
    """Create search tool schema file."""
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


@pytest.fixture
def extract_schema_path(tmp_path: Path) -> Path:
    """Create extract tool schema file."""
    schema_path = tmp_path / "extract_tool.json"
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
                    "source_id": {"type": "string"},
                    "target_path": {"type": "string"},
                    "query": {"type": "string"},
                },
                "required": ["source_id", "target_path"],
            },
            "capabilities": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["id", "type", "name", "version", "parameters", "capabilities"],
    }
    schema_path.write_text(json.dumps(schema))
    return schema_path


@pytest.fixture
def server(temp_dir: Path) -> NovaServer:
    """Create server instance for benchmarking.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        NovaServer instance
    """
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)
    server = NovaServer(config)
    server.start()
    return server


@benchmark(iterations=100, warmup=10)
def test_search_tool_execution(
    server: NovaServer, search_schema_path: Path, sample_documents: list[dict]
) -> None:
    """Benchmark search tool execution."""
    search_tool = SearchTool(search_schema_path, server._get_vector_store())

    search_tool.validate_request(
        {
            "id": "search-1",
            "type": "search",
            "name": "Search Test",
            "version": "1.0.0",
            "parameters": {
                "query": "test query",
                "n_results": 10,
                "min_score": 0.5,
                "filters": {"source": "test"},
            },
            "capabilities": ["search"],
        }
    )


@benchmark(iterations=100, warmup=10)
def test_list_tool_execution(server: NovaServer, list_schema_path: Path) -> None:
    """Benchmark list tool execution."""
    list_tool = ListTool(list_schema_path)
    list_tool.validate_request(
        {
            "id": "list-1",
            "type": "list",
            "name": "List Test",
            "version": "1.0.0",
            "parameters": {
                "path": "/test",
                "recursive": True,
                "include_pattern": "*.txt",
                "exclude_pattern": "*.tmp",
            },
            "capabilities": ["list"],
        }
    )


@benchmark(iterations=100, warmup=10)
def test_extract_tool_execution(
    server: NovaServer, extract_schema_path: Path, sample_documents: list[dict]
) -> None:
    """Benchmark extract tool execution."""
    extract_tool = ExtractTool(extract_schema_path)
    doc = random.choice(sample_documents)

    # Create a test file
    test_file = Path("test.txt")
    test_file.write_text("This is a test file for extraction")

    try:
        extract_tool.execute(
            {
                "id": "extract-1",
                "type": "extract",
                "name": "Extract Test",
                "version": "1.0.0",
                "parameters": {"source_id": doc["id"], "target_path": str(test_file)},
                "capabilities": ["extract"],
            }
        )
    finally:
        # Clean up test file
        if test_file.exists():
            test_file.unlink()


@benchmark(iterations=100, warmup=10)
def test_remove_tool_execution(
    server: NovaServer, remove_schema_path: Path, sample_documents: list[dict]
) -> None:
    """Benchmark remove tool execution."""
    remove_tool = RemoveTool(remove_schema_path)
    doc = random.choice(sample_documents)
    remove_tool.validate_request(
        {
            "id": "remove-1",
            "type": "remove",
            "name": "Remove Test",
            "version": "1.0.0",
            "parameters": {"target_id": doc["id"], "force": True},
            "capabilities": ["remove"],
        }
    )
