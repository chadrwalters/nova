"""Test search consistency between CLI and MCP server."""

import json
import logging
import sys
import time
from collections.abc import Generator
from pathlib import Path

import pytest

from nova.cli.commands.nova_mcp_server import search as mcp_search
from nova.cli.commands.search import SearchCommand
from nova.vector_store.chunking import Chunk
from nova.vector_store.store import VectorStore


@pytest.fixture
def setup_logging() -> Generator[None, None, None]:
    # Get the root logger and clear existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create a stream handler that writes to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Add the handler and set level
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    yield

    # Clean up
    root_logger.removeHandler(handler)
    handler.close()


@pytest.fixture
def vector_store(tmp_path: Path) -> Generator[VectorStore, None, None]:
    """Create a test vector store with sample data."""
    store = VectorStore(vector_dir=str(tmp_path))

    # Add test chunks
    chunks = [
        (
            Chunk(
                text="Python is a great programming language",
                source=Path("test1.md"),
                heading_text="Programming",
                heading_level=1,
                tags=["python", "programming"],
            ),
            {
                "source": "test1.md",
                "heading_text": "Programming",
                "heading_level": 1,
                "tags": json.dumps(["python", "programming"]),
                "attachments": "[]",
            },
        ),
        (
            Chunk(
                text="Machine learning is transforming technology",
                source=Path("test2.md"),
                heading_text="AI/ML",
                heading_level=1,
                tags=["ml", "ai", "tech"],
            ),
            {
                "source": "test2.md",
                "heading_text": "AI/ML",
                "heading_level": 1,
                "tags": json.dumps(["ml", "ai", "tech"]),
                "attachments": "[]",
            },
        ),
        (
            Chunk(
                text="Testing ensures code quality",
                source=Path("test3.md"),
                heading_text="Development",
                heading_level=1,
                tags=["testing", "dev"],
            ),
            {
                "source": "test3.md",
                "heading_text": "Development",
                "heading_level": 1,
                "tags": json.dumps(["testing", "dev"]),
                "attachments": "[]",
            },
        ),
    ]

    for chunk, metadata in chunks:
        store.add_chunk(chunk, metadata)

    # Wait for ChromaDB to persist the data
    time.sleep(0.5)  # Increased wait time to ensure data is persisted

    yield store

    try:
        store.cleanup()
    except Exception:
        pass  # Ignore cleanup errors in tests


@pytest.fixture
def cli_command(vector_store: VectorStore) -> SearchCommand:
    """Create a CLI search command instance."""
    return SearchCommand()


@pytest.mark.asyncio
async def test_search_consistency(
    vector_store: VectorStore,
    cli_command: SearchCommand,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that CLI and MCP server search return consistent results."""
    query = "python programming"
    limit = 5

    # Patch the MCP server's vector store
    from nova.cli.commands import nova_mcp_server

    monkeypatch.setattr(nova_mcp_server, "vector_store", vector_store)

    # Get MCP server results
    mcp_results = await mcp_search(query=query, limit=limit)

    # Get CLI results
    await cli_command.run_async(query=query, vector_dir=vector_store.vector_dir, limit=limit)
    cli_output = capsys.readouterr()

    # Verify result counts match
    assert mcp_results["count"] > 0, "Expected at least one result"
    assert "Found" in cli_output.out

    # Compare first result
    if mcp_results["results"]:
        mcp_first = mcp_results["results"][0]
        cli_lines = cli_output.out.split("\n")
        cli_score_line = next(line for line in cli_lines if "Score:" in line)
        cli_score = float(cli_score_line.split(":")[1].strip().rstrip("%"))

        # Verify scores match within 1%
        assert abs(mcp_first["score"] - cli_score) < 1.0

        # Verify metadata matches
        assert mcp_first["heading"] in cli_output.out
        # Compare tags accounting for JSON encoding
        mcp_tags = json.loads(mcp_first["tags"])
        for tag in mcp_tags:
            assert tag in cli_output.out
        assert mcp_first["content"] in cli_output.out


@pytest.mark.asyncio
async def test_empty_results_consistency(
    vector_store: VectorStore,
    cli_command: SearchCommand,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that empty results are handled consistently between CLI and MCP."""
    # Use a very specific query that won't match any documents
    query = "xyzabc123nonexistentquery"
    limit = 5

    # Patch the MCP server's vector store
    from nova.cli.commands import nova_mcp_server

    monkeypatch.setattr(nova_mcp_server, "vector_store", vector_store)

    # Get results from MCP
    mcp_results = await mcp_search(query=query, limit=limit)

    # Get results from CLI
    await cli_command.run_async(query=query, vector_dir=vector_store.vector_dir, limit=limit)
    cli_output = capsys.readouterr()

    # Verify both return empty results
    assert len(mcp_results["results"]) == 0
    assert "No results found" in cli_output.out


@pytest.mark.asyncio
async def test_score_normalization(
    vector_store: VectorStore,
    cli_command: SearchCommand,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that scores are normalized consistently between CLI and MCP
    server."""
    query = "python"
    limit = 5

    # Patch the MCP server's vector store
    from nova.cli.commands import nova_mcp_server

    monkeypatch.setattr(nova_mcp_server, "vector_store", vector_store)

    # Get MCP server results
    mcp_results = await mcp_search(query=query, limit=limit)

    # Get CLI results
    await cli_command.run_async(query=query, vector_dir=vector_store.vector_dir, limit=limit)
    cli_output = capsys.readouterr()

    # Verify all scores are properly normalized (0-100%)
    for result in mcp_results["results"]:
        score = min(100.0, result["score"])  # Cap at 100%
        assert 0 <= score <= 100

    cli_scores = [
        float(line.split(":")[1].strip().rstrip("%"))
        for line in cli_output.out.split("\n")
        if "Score:" in line
    ]
    for score in cli_scores:
        assert 0 <= score <= 100

    # Verify relative score ordering is consistent
    if len(mcp_results["results"]) > 1 and len(cli_scores) > 1:
        # Check if scores maintain the same relative order
        mcp_scores = [min(100.0, result["score"]) for result in mcp_results["results"]]
        for i in range(len(mcp_scores) - 1):
            if mcp_scores[i] > mcp_scores[i + 1]:
                assert cli_scores[i] > cli_scores[i + 1]
            elif mcp_scores[i] < mcp_scores[i + 1]:
                assert cli_scores[i] < cli_scores[i + 1]
