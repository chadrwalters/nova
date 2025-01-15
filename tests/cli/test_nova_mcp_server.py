"""Tests for Nova FastMCP server implementation."""

import pytest
from pathlib import Path
from typing import Any, Dict, Generator
from fastapi.testclient import TestClient

from nova.cli.commands.nova_mcp_server import app, vector_store

@pytest.fixture
def test_client() -> TestClient:
    """Create test client fixture."""
    return TestClient(app.create_app())

@pytest.fixture
def test_vector_store(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temporary vector store."""
    store_dir = tmp_path / ".nova/vectors"
    store_dir.mkdir(parents=True)

    # Add test document
    test_doc = {
        "id": "test1",
        "title": "Test Document",
        "content": "This is a test document for searching.",
        "source": "test.md",
        "tags": ["test"]
    }
    vector_store.add(test_doc["id"], test_doc["content"], test_doc)

    yield store_dir

    # Cleanup
    vector_store.cleanup()

def test_search_tool(test_client: TestClient, test_vector_store: Path) -> None:
    """Test search tool functionality."""
    response = test_client.post("/tools/search", json={
        "query": "test document"
    })
    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) > 0

    result = data[0]
    assert "id" in result
    assert "metadata" in result
    assert "distance" in result
    assert result["metadata"]["title"] == "Test Document"

def test_monitor_health(test_client: TestClient, test_vector_store: Path) -> None:
    """Test monitor tool health check."""
    response = test_client.post("/tools/monitor", json={
        "command": "health"
    })
    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert data["status"] == "healthy"
    assert "vector_store" in data
    assert data["vector_store"]["exists"] is True
    assert data["vector_store"]["is_dir"] is True

def test_monitor_stats(test_client: TestClient, test_vector_store: Path) -> None:
    """Test monitor tool stats."""
    response = test_client.post("/tools/monitor", json={
        "command": "stats"
    })
    assert response.status_code == 200
    data = response.json()

    assert "vector_store" in data
    assert "documents" in data["vector_store"]
    assert data["vector_store"]["documents"] > 0
    assert "model" in data["vector_store"]
    assert "batch_size" in data["vector_store"]

def test_search_error_handling(test_client: TestClient) -> None:
    """Test search tool error handling."""
    # Test with invalid query
    response = test_client.post("/tools/search", json={
        "query": None  # type: ignore
    })
    assert response.status_code == 422  # Validation error

def test_monitor_error_handling(test_client: TestClient) -> None:
    """Test monitor tool error handling."""
    # Test with invalid command
    response = test_client.post("/tools/monitor", json={
        "command": "invalid"
    })
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "error"
    assert "error" in data
