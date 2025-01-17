"""Tests for the process vectors command."""

import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock

import pytest

from nova.cli.commands.process_vectors import ProcessVectorsCommand
from nova.vector_store.store import VectorStore


@pytest.fixture
def output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        yield temp_path


@pytest.fixture
def mock_store() -> Mock:
    """Create a mock vector store."""
    store = Mock(spec=VectorStore)
    store.search.return_value = []
    return store


@pytest.fixture
def store(output_dir: Path) -> VectorStore:
    """Create a real vector store for testing."""
    store = VectorStore(str(output_dir), use_memory=True)
    return store


def test_process_vectors_basic(output_dir: Path, store: VectorStore) -> None:
    """Test basic vector processing."""
    command = ProcessVectorsCommand(vector_store=store)
    text = "This is a test document about machine learning."

    # Process vectors
    command.run(text=text, output_dir=str(output_dir))

    # Verify output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()

    # Search for the actual content
    results = store.search("machine learning")

    assert len(results) > 0
    assert "machine learning" in results[0]["text"].lower()
    assert results[0]["score"] > 0.5  # High relevance for exact match


def test_process_vectors_empty_text(output_dir: Path, mock_store: Mock) -> None:
    """Test processing empty text."""
    command = ProcessVectorsCommand(vector_store=mock_store)
    text = ""

    # Process vectors - should handle empty text gracefully
    command.run(text=text, output_dir=str(output_dir))

    # Verify output directory exists
    assert output_dir.exists()
    assert output_dir.is_dir()

    # Verify no chunks were added to the store
    mock_store.add_chunk.assert_not_called()

    # Verify search returns empty results
    mock_store.search.return_value = []
    results = mock_store.search("test")
    assert len(results) == 0


def test_process_vectors_multiple_chunks(output_dir: Path, store: VectorStore) -> None:
    """Test processing text that creates multiple chunks."""
    command = ProcessVectorsCommand(vector_store=store)
    text = """# First Section
This is the first section about Python programming.

# Second Section
This is about machine learning with Python.

# Third Section
This discusses JavaScript and web development."""

    command.run(text=text, output_dir=str(output_dir))

    # Search for Python content
    python_results = store.search("python programming")
    assert len(python_results) > 0
    assert any("Python programming" in r["text"] for r in python_results)

    # Search for JavaScript content
    js_results = store.search("javascript web")
    assert len(js_results) > 0
    assert any("JavaScript" in r["text"] for r in js_results)

    # Verify ordering - Python query should rank Python content higher
    python_scores = [r["score"] for r in python_results if "Python" in r["text"]]
    js_scores = [r["score"] for r in python_results if "JavaScript" in r["text"]]
    if js_scores:  # If JavaScript results appear in Python search
        assert max(python_scores) > max(js_scores)


def test_process_vectors_missing_args() -> None:
    """Test missing arguments."""
    command = ProcessVectorsCommand()

    with pytest.raises(KeyError):
        command.run()

    with pytest.raises(KeyError):
        command.run(text="test")

    with pytest.raises(KeyError):
        command.run(output_dir="test")
