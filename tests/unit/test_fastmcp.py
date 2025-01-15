"""Tests for FastMCP implementation."""

import pytest
from typing import Any, Dict
from pathlib import Path
from fastapi.testclient import TestClient
from starlette.testclient import TestClient as StarletteTestClient

from nova.server.fastmcp import FastMCP, Tool, TextContent

@pytest.fixture
def mcp_server() -> FastMCP:
    """Create FastMCP server fixture."""
    server = FastMCP("test-server")

    @server.tool(name="test_tool")
    async def test_tool(query: str = "") -> Dict[str, Any]:
        """Test tool implementation."""
        return {"result": f"Processed: {query}"}

    @server.prompt(name="test_prompt")
    async def test_prompt(query: str = "") -> Dict[str, Any]:
        """Test prompt implementation."""
        return {
            "messages": [
                {
                    "role": "user",
                    "content": {"type": "text", "text": f"Query: {query}"}
                }
            ]
        }

    return server

@pytest.fixture
def test_client(mcp_server: FastMCP) -> StarletteTestClient:
    """Create test client fixture."""
    app = mcp_server.create_app()
    return StarletteTestClient(app)

def test_tool_registration(mcp_server: FastMCP) -> None:
    """Test tool registration."""
    assert "test_tool" in mcp_server.tools
    tool = mcp_server.tools["test_tool"]
    assert isinstance(tool, Tool)
    assert tool.name == "test_tool"

def test_prompt_registration(mcp_server: FastMCP) -> None:
    """Test prompt registration."""
    assert "test_prompt" in mcp_server.prompts
    prompt = mcp_server.prompts["test_prompt"]
    assert prompt.name == "test_prompt"

@pytest.mark.asyncio
async def test_sse_endpoint(test_client: StarletteTestClient) -> None:
    """Test SSE endpoint."""
    response = test_client.get("/sse")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_search_tool(mcp_server: FastMCP) -> None:
    """Test search tool functionality."""
    # Add test document to vector store
    test_doc = {
        "id": "test1",
        "title": "Test Document",
        "content": "This is a test document for searching.",
        "source": "test.md",
        "tags": ["test"]
    }
    mcp_server.vector_store.add(
        test_doc["id"],
        test_doc["content"],
        test_doc
    )

    # Register search tool
    @mcp_server.tool(name="search_notes")
    async def search_notes(query: str, limit: int = 5) -> Dict[str, Any]:
        """Search through notes."""
        results = mcp_server.vector_store.search(query, limit=limit)
        return {"results": results}

    # Test search
    handler = mcp_server._tool_handlers["search_notes"]
    result = await handler(query="test document", limit=1)

    assert "results" in result
    assert len(result["results"]) == 1

    # Verify result format
    item = result["results"][0]
    assert "id" in item
    assert "metadata" in item
    assert "distance" in item
    assert item["metadata"]["title"] == "Test Document"

    # Clean up
    mcp_server.vector_store.cleanup()
