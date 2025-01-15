"""Tests for Nova FastMCP integration."""

import asyncio
from pathlib import Path
from typing import AsyncGenerator

import pytest
from mcp.server.fastmcp import FastMCP

from nova.server.mcp import (
    app,
    process_notes_tool,
    search_tool,
    monitor_tool,
    clean_processing_tool,
    clean_vectors_tool,
)
from nova.vector_store.store import VectorStore


@pytest.fixture(autouse=True)
def setup_vector_store(temp_dir: Path, monkeypatch) -> None:
    """Set up vector store with temp directory."""
    # Create a new vector store instance with temp directory
    store = VectorStore(temp_dir / ".nova/vectors")

    # Patch the vector store in the MCP module
    monkeypatch.setattr("nova.server.mcp.vector_store", store)


def test_app_initialization() -> None:
    """Test that the FastMCP app is initialized correctly."""
    assert isinstance(app, FastMCP)
    assert app.name == "nova"

    # Check that tool functions exist
    assert callable(process_notes_tool)
    assert callable(search_tool)
    assert callable(monitor_tool)
    assert callable(clean_processing_tool)
    assert callable(clean_vectors_tool)


@pytest.mark.asyncio
async def test_search_tool() -> None:
    """Test search tool functionality."""
    result = await search_tool(query="test query", limit=5)
    assert isinstance(result, dict)
    assert "status" in result
    assert "results" in result
    assert "count" in result
    assert "query" in result
    assert result["query"] == "test query"


@pytest.mark.asyncio
async def test_monitor_tool_health() -> None:
    """Test monitor tool health check."""
    result = await monitor_tool(subcommand="health")
    assert isinstance(result, dict)
    assert "status" in result
    assert "message" in result
    assert "vector_store" in result


@pytest.mark.asyncio
async def test_monitor_tool_stats() -> None:
    """Test monitor tool stats."""
    result = await monitor_tool(subcommand="stats")
    assert isinstance(result, dict)
    assert "status" in result
    assert "message" in result
    assert "vector_store" in result


@pytest.mark.asyncio
async def test_clean_processing_tool() -> None:
    """Test clean processing tool."""
    result = await clean_processing_tool(force=True)
    assert isinstance(result, dict)
    assert "status" in result
    assert "message" in result
    assert result["message"] == "Processing directory cleaned"


@pytest.mark.asyncio
async def test_clean_vectors_tool() -> None:
    """Test clean vectors tool."""
    result = await clean_vectors_tool(force=True)
    assert isinstance(result, dict)
    assert "status" in result
    assert "message" in result
    assert result["message"] == "Vector store cleaned"


@pytest.mark.asyncio
async def test_process_notes_tool(tmp_path: Path) -> None:
    """Test process notes tool."""
    # Create test input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    result = await process_notes_tool(
        input_dir=str(input_dir),
        output_dir=str(output_dir)
    )
    assert isinstance(result, dict)
    assert "status" in result
    assert "message" in result
    assert result["message"] == "Notes processed successfully"


@pytest.mark.asyncio
async def test_error_handling() -> None:
    """Test error handling for invalid requests."""
    # Test invalid monitor subcommand
    with pytest.raises(Exception):
        await monitor_tool(subcommand="invalid")

    # Test missing required parameter
    with pytest.raises(TypeError):
        await search_tool()  # type: ignore

